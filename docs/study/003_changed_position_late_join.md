# Bug Study: Changed<Position> Delta Sync Misses Initial Entities

**Date:** 2026-04-05  
**Severity:** High (initial entities invisible, spawned ones visible)  
**System:** `micro-core/src/systems/ws_sync.rs`  
**Tags:** `bevy`, `change-detection`, `ecs`, `delta-sync`

---

## 1. Symptom

After fixing the broadcast forwarder (Study 001), a new issue appeared:
- Entities spawned via WS command → **visible** in visualizer ✓
- Initial 100 entities from `Startup` → **invisible** ✗
- Telemetry showed 0 entities even though Rust logs confirmed 99 alive

## 2. Investigation Process

### Step 1: Understand the sync pipeline

```rust
pub fn ws_sync_system(
    query: Query<..., Changed<Position>>,  // ← ONLY entities with changed Position
    ...
) {
    for (id, pos, vel, ...) in query.iter() {
        moved.push(EntityState { ... });
    }
    if !moved.is_empty() || !removed.is_empty() {  // ← Skip if empty
        sender.0.send(json_str);
    }
}
```

Two problems:
1. Query uses `Changed<Position>` — only captures entities whose Position was
   modified since the system's last run
2. Message only sent when `moved` is non-empty

### Step 2: Trace the change detection lifecycle

```
Startup:     initial_spawn_system spawns 100 entities
             → Position components created → Changed flag SET

Tick 1:      ws_sync_system runs → Changed<Position> fires for all 100
             → SyncDelta broadcast with 100 entities
             → BUT: WS clients not connected yet → forwarder sends to 0 sinks
             → Message effectively LOST

Tick 2-N:    ws_sync_system runs → Changed<Position> already consumed on Tick 1
             → query returns 0 entities (no position changes since last check)
             → moved is empty → no message sent

Later:       Browser connects → receives... nothing
```

### Step 3: Why spawned entities work

Entities spawned via `spawn_wave` WS command:
1. Browser is already connected
2. Entity spawned via `Commands` → appears next tick
3. `Changed<Position>` fires (newly added component)
4. ws_sync picks them up → broadcasts → forwarder sends to connected browser ✓

The timing difference: spawned entities arrive AFTER the browser connects.

## 3. Root Cause

`Changed<Position>` is a **one-shot detection** — it fires when the component is
modified, and the flag is consumed when the system reads it. For initial entities,
this detection happens on Tick 1 when no WS clients exist. After that, the flag is
consumed and the entities become invisible to the sync system.

The movement system DOES write to Position every tick (`pos.x = next_x.clamp(...)`)
which re-triggers `Changed`, but this depends on the movement system actually
processing entities (which was blocked by the SimState bug — see Study 002).

Even with movement running, relying solely on `Changed` for sync creates a **late
join problem** — any client connecting after the initial Changed detection misses
the full state.

## 4. Fix

Added a periodic full-state broadcast alongside the delta sync:

```rust
pub fn ws_sync_system(
    changed_query: Query<..., Changed<Position>>,  // Delta sync
    full_query: Query<...>,                         // Full state
    tick: Res<TickCounter>,
    ...
) {
    let is_full_sync = tick.tick % 60 == 0;  // Every ~1 second

    let mut moved = Vec::new();
    if is_full_sync {
        // Full snapshot: ALL entities regardless of change detection
        for (id, pos, vel, ...) in full_query.iter() { ... }
    } else {
        // Delta: only changed entities (efficient for 59/60 ticks)
        for (id, pos, vel, ...) in changed_query.iter() { ... }
    }
    // Always send (even empty) so tick/telemetry updates reach client
    sender.0.send(json_str);
}
```

## 5. Lessons Learned

1. **Change detection is not a sync primitive.** `Changed<T>` is designed for
   reactive systems within a single app, not for external client synchronization.
   External clients can connect at any time and need full state.

2. **The "late join" problem is universal.** Any pub/sub system needs either:
   - Periodic full-state snapshots (what we implemented)
   - State-on-connect (send full state when a client first connects)
   - Event sourcing (replay all events from the beginning)

3. **Remove `if !moved.is_empty()` guards for sync systems.** Even empty SyncDelta
   messages carry useful metadata (tick count, telemetry, visibility). Clients need
   these to update their state displays.

4. **Two queries are cheap in Bevy.** Having both `changed_query` (filtered) and
   `full_query` (unfiltered) costs near-zero memory — Bevy queries are views into
   the same archetype storage. The full query only iterates all entities once per
   second (60 ticks), which is negligible at any entity count.

## 6. Detection Strategy

- **Integration test:** Start server, wait 3 seconds, connect client, verify all
  entities appear within 1 second
- **Metric:** Track `moved.len()` per tick — if it's always 0 when entities exist,
  the sync is broken
- **Architecture review:** Any system using `Changed<T>` for external sync should
  have a periodic full-state fallback
