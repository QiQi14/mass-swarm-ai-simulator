# Bug Study: Tokio Broadcast Channel Silently Kills Forwarder Task

**Date:** 2026-04-05  
**Severity:** Critical (complete data pipeline failure)  
**System:** `micro-core/src/bridges/ws_server.rs`  
**Tags:** `tokio`, `broadcast`, `async`, `silent-failure`

---

## 1. Symptom

All spawned entities were invisible in the Debug Visualizer. The WebSocket
connection established successfully (green "Connected" dot), telemetry showed 0
entities, 0 TPS, 0 ticks. The Rust server logs confirmed entities existed:

```
[Tick 60] Entities alive: 99
[WS Command] Spawned 50/50 faction_0 at (205.68, 789.77) spread 30
```

Entities spawned via WS command appeared after spawning but initial entities
never appeared.

## 2. Investigation Process

### Step 1: Verify the data pipeline

```
Bevy ECS → ws_sync_system → BroadcastSender → Forwarder Task → WS Sink → Browser
```

Checked each stage:
- `ws_sync_system` builds `SyncDelta` with `Changed<Position>` → sends to broadcast ✓
- `BroadcastSender` wraps `tokio::sync::broadcast::Sender<String>` ✓
- Browser confirms WS connection established ✓
- But NO messages arrive at the browser ✗

### Step 2: Trace the forwarder task

```rust
// ws_server.rs — THE BUG
tokio::spawn(async move {
    while let Ok(msg) = rx.recv().await {  // ← Breaks on ANY Err
        // ... forward to connected sinks
    }
});
```

### Step 3: Identify the failure mode

`tokio::sync::broadcast::Receiver::recv()` returns:
- `Ok(msg)` — normal message
- `Err(RecvError::Lagged(n))` — buffer overflow, n messages lost
- `Err(RecvError::Closed)` — sender dropped

The broadcast channel has a buffer of 100. At 60 TPS, `ws_sync_system` fills the
buffer in ~1.67 seconds. The browser typically connects 2+ seconds after server
start. By then:

1. Buffer overflows
2. `recv()` returns `Err(Lagged(n))`
3. `while let Ok(msg)` evaluates to `false`
4. **Loop breaks — forwarder task exits permanently**
5. All subsequent messages are broadcast but never forwarded

## 3. Root Cause

The `while let Ok(msg)` pattern treats ALL errors as fatal, including the
**recoverable** `Lagged` error. This is a common footgun with `tokio::broadcast`
because the API returns `Err` for what is logically a "skip" operation, not a
failure.

## 4. Fix

```diff
-    while let Ok(msg) = rx.recv().await {
-        // ... forward to sinks
-    }

+    loop {
+        match rx.recv().await {
+            Ok(msg) => {
+                // ... forward to sinks
+            }
+            Err(tokio::sync::broadcast::error::RecvError::Lagged(n)) => {
+                eprintln!("[WS Server] Skipped {} lagged messages", n);
+                continue; // Recoverable — skip lost messages, keep running
+            }
+            Err(tokio::sync::broadcast::error::RecvError::Closed) => {
+                break; // Sender dropped — simulation shut down
+            }
+        }
+    }
```

## 5. Lessons Learned

1. **`tokio::broadcast` is not a queue** — it's a ring buffer. Slow consumers lose
   messages, and the API signals this via `Err(Lagged)`. This is by design, not a bug.

2. **`while let Ok(x) = fallible_op()` is dangerous** for operations that have
   recoverable error variants. Always use explicit `match` to handle each case.

3. **Silent task death is the worst failure mode.** The forwarder died silently — no
   panic, no log, no error. Adding `eprintln!` for the Lagged case provides
   operational visibility.

4. **Buffer size matters.** A capacity of 100 at 60 TPS gives only 1.67 seconds
   before overflow. For systems where clients connect late, consider either:
   - Larger buffer (1000+ = ~17 seconds)
   - Initial full-state sync on client connect (we implemented this)
   - Both

## 6. Detection Strategy

- **Unit test:** Start server, fill broadcast buffer beyond capacity, verify
  forwarder task still alive after `Lagged`
- **Integration test:** Start server, wait 5 seconds (simulate late connect),
  connect client, verify messages arrive
- **Runtime:** Log `Lagged` count as a metric
