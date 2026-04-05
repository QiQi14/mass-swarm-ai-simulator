# Bug Study: SimState Gate Freezes Physics 90% of the Time

**Date:** 2026-04-05  
**Severity:** Critical (entities appear completely static)  
**System:** `micro-core/src/main.rs`, `micro-core/src/bridges/zmq_bridge/systems.rs`  
**Tags:** `bevy`, `state-machine`, `zmq`, `system-scheduling`

---

## 1. Symptom

Entities appeared in the visualizer but never moved. Velocity arrows were visible
(non-zero velocity), but positions remained identical across thousands of ticks.
The telemetry showed the movement system running (~134µs), but entity positions
never changed.

Browser diagnostic confirmed:
```json
// Snapshot 1 (Tick 5836)
{ "id": 1, "x": 239.577, "y": 438.731, "dx": 1.838, "dy": 4.636 }

// Snapshot 2 (Tick 6333) — 497 ticks later
{ "id": 1, "x": 239.577, "y": 438.731, "dx": 1.838, "dy": 4.636 }
```

Position AND velocity were frozen. The velocity values (1.838, 4.636) were outside
the initial spawn range of (-1..1), proving the movement system ran briefly and
then stopped.

## 2. Investigation Process

### Step 1: Verify movement system processes entities

Added diagnostic `println!` inside the movement system:
```rust
static DIAG_COUNTER: AtomicU64 = AtomicU64::new(0);
let c = DIAG_COUNTER.fetch_add(1, Ordering::Relaxed);
if c % 60 == 0 {
    let count = query.iter().count();
    println!("[Movement DIAG] tick={}, entities_in_query={}", c, count);
}
```

Result in `--smoke-test` mode (no WS server):
```
[Movement DIAG] tick=0, entities_in_query=100
[Movement DIAG] tick=60, entities_in_query=97
[Movement DIAG] tick=120, entities_in_query=74
```

**Movement system works correctly in isolation.** The issue is specific to the
normal `./dev.sh` runtime.

### Step 2: Identify the scheduling difference

The simulation chain was gated by:
```rust
.run_if(in_state(SimState::Running))
.run_if(|paused: Res<SimPaused>| !paused.0 || step.0 > 0)
```

`SimState::Running` was the key difference. In smoke test mode, `SimState`
transitions happen but recover quickly. In normal mode, the ZMQ bridge creates
a different pattern.

### Step 3: Trace the SimState lifecycle

```
Tick 0-29:   SimState::Running      → movement runs ✓
Tick 30:     ai_trigger_system      → try_send(state_json).is_ok()
             → SimState::WaitingForAI

Tick 30-330: SimState::WaitingForAI → movement chain gated → FROZEN
             ZMQ background thread:
               socket.send(state) → timeout 5s (no Python AI)
               socket.recv()      → timeout 5s
             ai_poll_system: try_recv() → Empty → do nothing

~5 seconds later:
Tick ~330:   Background thread sends HOLD fallback
             ai_poll_system: try_recv() → Ok(HOLD) → SimState::Running

Tick 330-359: movement runs ✓ (0.5 seconds)
Tick 360:    ai_trigger_system fires again → WaitingForAI
```

**Result:** Simulation runs 0.5s, frozen 5s, runs 0.5s, frozen 5s...
That's **9% running time**. Entities have their velocities partially modified
during the brief Running windows but appear static because movement is nearly
invisible at that ratio.

## 3. Root Cause

The `SimState::Running` gate was applied to the **physics chain** (movement,
interaction, removal), but `SimState` was designed for the ZMQ AI bridge
(pause while waiting for Python macro-brain response). When no Python AI is
connected, the ZMQ socket times out after 5 seconds, creating a 5-second
freeze cycle that cripples the simulation.

The velocity values (1.838, 4.636) confirm the movement system ran briefly
during the first Running window, computed new velocities from separation
forces, then froze when SimState flipped to WaitingForAI.

## 4. Fix

Two changes:

### 4a. Remove SimState gating from physics (main.rs)
```diff
-.run_if(in_state(SimState::Running))
 .run_if(|paused: Res<SimPaused>, step: Res<SimStepRemaining>| !paused.0 || step.0 > 0)
```

Physics is now only gated by user-driven pause controls.

### 4b. Add 200ms timeout to ai_poll_system
```rust
pub(super) fn ai_poll_system(
    channels: Res<AiBridgeChannels>,
    mut next_state: ResMut<NextState<SimState>>,
    mut waiting_since: Local<Option<std::time::Instant>>,
) {
    let start = *waiting_since.get_or_insert_with(std::time::Instant::now);
    match channels.action_rx.lock().unwrap().try_recv() {
        Ok(_) => { *waiting_since = None; next_state.set(SimState::Running); }
        Err(TryRecvError::Empty) => {
            if start.elapsed() > Duration::from_millis(200) {
                *waiting_since = None;
                next_state.set(SimState::Running); // Don't freeze
            }
        }
        Err(TryRecvError::Disconnected) => {
            *waiting_since = None;
            next_state.set(SimState::Running);
        }
    }
}
```

## 5. Lessons Learned

1. **Don't gate physics behind external I/O state.** The ZMQ bridge's "waiting for
   AI" state should never block the physics pipeline. Physics should have its own
   independent pause mechanism (user-driven) separate from AI communication state.

2. **Default resources matter.** `AiBridgeConfig::default()` has
   `zmq_timeout_secs = 5`. In a headless dev environment with no Python AI, this
   creates a 5-second freeze every 0.5 seconds. The default should either be 0
   (disabled) or the system should detect "no AI connected" and skip entirely.

3. **Telemetry can mislead.** The telemetry showed Movement: 134µs, which made it
   look like the system was running. But the function body executes overhead code
   (HashMap construction, timing) even when the query returns 0 entities. The 134µs
   was setup cost, not entity processing.

4. **Frozen velocity is a diagnostic signal.** If velocity is non-zero but positions
   never change, it means the movement system isn't running OR it's running but its
   writes are being overwritten. Checking if velocity has decayed (it should, via
   `lerp`) reveals whether the system ran at all.

## 6. Detection Strategy

- **Diagnostic:** Log `SimState` transitions with timestamps:
  `[SimState] Running → WaitingForAI (tick 30, will timeout in 5s)`
- **Telemetry:** Track "active sim ticks per second" vs "wall clock TPS" — a ratio
  below 1.0 indicates gating
- **Unit test:** Verify movement occurs without ZMQ bridge present
