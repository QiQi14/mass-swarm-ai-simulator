# Lesson: Bevy Unit Testing with States

**Category:** gotcha
**Discovered:** task_07_zmq_bridge_plugin (2026-04-03)
**Severity:** high

## Context
When writing unit tests for Bevy systems that interact with `State` or `NextState`, an isolated `App::new()` is typically used to minimize overhead.

## Problem
In recent Bevy versions, initializing states natively via `app.init_state::<MyState>()` will cause a runtime panic (e.g. `The StateTransition schedule is missing. Did you forget to add StatesPlugin or DefaultPlugins before calling init_state?`) if the necessary state scheduling plugins are not injected. 
Furthermore, pushing a state transition via `next_state.set()` will not reflect immediately. Bevy needs to process the state transitions through its schedule lifecycle.

## Correct Approach
1. Always inject `bevy::state::app::StatesPlugin` (or `bevy_state::app::StatesPlugin` depending on namespace) before asserting state transitions in a minimal app setup.
2. If your function sets a state transition inside an `Update` schedule tick, you must run `app.update()` twice to see the transition reflected in `state.get()` if you rely on the transition taking effect. The first update triggers the system that fires `.set(...)`, logging it into the queue. The second update propagates the `NextState` transition queue onto the active `State`.

## Example
- ❌ What the executor did:
```rust
let mut app = App::new();
app.init_state::<SimState>();
// ... setup system
app.update();
let state = app.world().get_resource::<State<SimState>>().unwrap();
assert_eq!(state.get(), &SimState::WaitingForAI); // Panics on missing plugin, or fails assert.
```

- ✅ What it should be:
```rust
let mut app = App::new();
app.add_plugins(bevy_state::app::StatesPlugin); // Prevent crash
app.init_state::<SimState>();
// ... setup system
app.update(); // triggers system, pushes NextState transition
app.update(); // executes StateTransition schedule, applies state

let state = app.world().get_resource::<State<SimState>>().unwrap();
assert_eq!(state.get(), &SimState::WaitingForAI); // Succeeds
```
