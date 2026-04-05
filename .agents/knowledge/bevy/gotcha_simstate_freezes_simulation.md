# Rule: SimState::WaitingForAI Freezes Simulation When No AI Connected

**Category:** Architecture, ZMQ Bridge, System Scheduling

## Context
The ZMQ bridge's `ai_trigger_system` fired every 30 ticks (0.5s) and transitioned
`SimState` to `WaitingForAI`. The background ZMQ I/O thread then waited 5 seconds
for a Python AI response (which never came since no AI was connected). During those
5 seconds, ALL simulation systems gated by `run_if(in_state(SimState::Running))` were
frozen — including the movement system.

**Result:** Entities appeared static despite having non-zero velocity. The movement
system only ran for 0.5s every 5.5s (9% of the time).

## Strict Directive
1. **Never gate physics/movement/interaction systems** behind `SimState::Running` in
   the main update schedule. Use only user-driven pause controls (`SimPaused`/`SimStep`).
2. `SimState` should only gate the ZMQ bridge's own trigger/poll systems.
3. If `SimState::WaitingForAI` is needed, add a **fast timeout** (200ms) in
   `ai_poll_system` to prevent sim freezes when no AI is connected.
4. The `ai_poll_system` should use `Local<Option<Instant>>` to track wait duration.

## Example
- **❌ Anti-pattern:**
```rust
.add_systems(Update, (movement_system,).chain()
    .run_if(in_state(SimState::Running))
    .run_if(|p: Res<SimPaused>| !p.0))
```
- **✅ Best Practice:**
```rust
.add_systems(Update, (movement_system,).chain()
    .run_if(|p: Res<SimPaused>, s: Res<SimStepRemaining>| !p.0 || s.0 > 0))
```
