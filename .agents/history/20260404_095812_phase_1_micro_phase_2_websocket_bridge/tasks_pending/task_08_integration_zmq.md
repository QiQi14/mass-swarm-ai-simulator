---
Task_ID: 08_integration_zmq
Execution_Phase: Phase C (Sequential Integration)
Model_Tier: standard
Target_Files:
  - micro-core/src/main.rs
Dependencies:
  - Task 05 (python_stub_ai)
  - Task 07 (zmq_bridge_plugin)
Context_Bindings:
  - context/tech-stack.md
  - skills/rust-code-standards
---

# STRICT INSTRUCTIONS

> **Feature:** P1_MP3 — ZeroMQ Bridge + Stub AI Round-Trip
> **Role:** Wire `ZmqBridgePlugin` into `main.rs`, gate `movement_system` behind `SimState::Running`, and verify end-to-end round-trip with the Python stub.

## Pre-condition Check

Before modifying `main.rs`, verify:
1. `micro-core/src/bridges/zmq_bridge.rs` exists and contains `pub struct ZmqBridgePlugin`
2. `micro-core/src/bridges/zmq_protocol.rs` exists
3. `macro-brain/src/stub_ai.py` exists
4. `cargo check` succeeds (Tasks 06 and 07 are complete)

## Instructions

1. **Update `micro-core/src/main.rs`**

   Add the `ZmqBridgePlugin` import and register it with the Bevy app:

   ```rust
   use micro_core::bridges::zmq_bridge::{ZmqBridgePlugin, SimState};
   ```

2. **Register the plugin:**
   - Add `.add_plugins(ZmqBridgePlugin)` to the app builder.

3. **Gate `movement_system` behind `SimState::Running`:**
   - Change the `movement_system` registration from:
     ```rust
     movement_system,
     ```
     to:
     ```rust
     movement_system.run_if(in_state(SimState::Running)),
     ```

4. **Do NOT gate these systems** — they must run regardless of `SimState`:
   - `tick_counter_system` — tick must always advance for timeout/exit logic
   - `log_system` — status logging should show even during AI pause
   - `smoke_test_exit_system` — must be able to exit during AI wait
   - `ws_sync_system` (if present from MP2) — debug visualizer stays updated

5. **The final `main.rs` should look approximately like this:**

   ```rust
   use bevy::prelude::*;

   use micro_core::bridges::zmq_bridge::{ZmqBridgePlugin, SimState};
   use micro_core::components::NextEntityId;
   use micro_core::config::{SimulationConfig, TickCounter};
   use micro_core::systems::{initial_spawn_system, movement_system, tick_counter_system};
   // ... MP2 imports (ws_sync, BroadcastSender, etc.) ...

   const SMOKE_TEST_MAX_TICKS: u64 = 300;

   fn main() {
       // ... MP2 channel setup (tokio broadcast) ...

       let mut app = App::new();
       app.add_plugins(MinimalPlugins)
          .set_runner(custom_runner)
          // Plugins
          .add_plugins(ZmqBridgePlugin)
          // Resources
          .init_resource::<SimulationConfig>()
          .init_resource::<TickCounter>()
          .init_resource::<NextEntityId>()
          // ... MP2 resources (BroadcastSender) ...
          // Startup
          .add_systems(Startup, initial_spawn_system)
          // Update — movement_system gated by SimState
          .add_systems(Update, (
              tick_counter_system,
              movement_system.run_if(in_state(SimState::Running)),
              log_system,
              // ... ws_sync_system (MP2) ...
          ));

       // Conditional smoke test exit
       if std::env::args().any(|a| a == "--smoke-test") {
           app.add_systems(Update, smoke_test_exit_system);
       }

       app.run();
   }

   // ... log_system, smoke_test_exit_system, custom_runner unchanged ...
   ```

> **CRITICAL:** Do NOT remove or modify any MP2 additions (tokio channel setup, BroadcastSender resource, ws_sync_system, WS server thread spawn). You are ONLY adding the ZMQ plugin and gating movement_system.

---

# Verification_Strategy
Test_Type: manual_steps + integration
Test_Stack: cargo + python
Acceptance_Criteria:
  - "`cargo build` succeeds with no errors."
  - "`cargo clippy` has zero warnings."
  - "`cargo test` passes all existing and new unit tests."
  - "Without Python running: `cargo run -- --smoke-test` starts, logs ZMQ timeout warnings (fallback to HOLD), and exits after 300 ticks."
  - "With Python running: `stub_ai.py` logs tick snapshots, Rust logs 'Received action: HOLD' every ~0.5s, simulation exits cleanly on --smoke-test."
Manual_Steps:
  - "1. Run `cd micro-core && cargo build` — must succeed."
  - "2. Run `cd micro-core && cargo test` — must pass."
  - "3. Run `cd micro-core && cargo run -- --smoke-test` WITHOUT Python — verify it exits after ~5s with ZMQ timeout warnings and HOLD fallbacks in stdout."
  - "4. In a separate terminal: `cd macro-brain && pip install pyzmq && python3 src/stub_ai.py`"
  - "5. Run `cd micro-core && cargo run -- --smoke-test` WITH Python running — verify Python logs tick snapshots, Rust logs 'Received action: HOLD', exits cleanly."
  - "6. Kill both processes."
