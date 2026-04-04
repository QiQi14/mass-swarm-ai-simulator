---
Task_ID: 04_integration_ws
Execution_Phase: Phase C (Sequential Integration)
Model_Tier: standard
Target_Files:
  - micro-core/src/main.rs
Dependencies:
  - Task 02 (ws_server)
  - Task 03 (ws_sync_system)
Context_Bindings:
  - context/tech-stack.md
---

# STRICT INSTRUCTIONS

1. **Update `micro-core/src/main.rs`** to wire the Tokio WS server and Bevy WS sync system.
2. Initialize the broadcast channel before Bevy app creation:
   ```rust
   let (tx, rx) = tokio::sync::broadcast::channel::<String>(100);
   ```
3. Boot the Tokio Server asynchronously in a separate operating system thread:
   ```rust
   std::thread::spawn(move || {
       let rt = tokio::runtime::Runtime::new().unwrap();
       rt.block_on(async {
           micro_core::bridges::ws_server::start_server(rx).await;
       });
   });
   ```
4. Expose `tx` to Bevy using `.insert_resource(micro_core::systems::ws_sync::BroadcastSender(tx))`.
5. Add `micro_core::systems::ws_sync::ws_sync_system` to `Update` systems.
6. Modify `smoke_test_exit_system` so it only runs if `--smoke-test` is requested:
   ```rust
   if std::env::args().any(|a| a == "--smoke-test") {
       app.add_systems(Update, smoke_test_exit_system);
   }
   ```
   (Alternatively, you can always register the system but evaluate the argument inside it. Or you can remove `app.add_systems(Update, smoke_test_exit_system)` from the default tuple and conditionally add it.)

---

# Verification_Strategy
Test_Type: manual_steps
Test_Stack: bash
Acceptance_Criteria:
  - "Running the project continuously emits WS delta messages via `ws://127.0.0.1:8080`, without crashing the 60 TPS headless ECS."
  - "The smoke-test argument properly auto-exits the simulation."
Manual_Steps:
  - "Run `cargo run`."
  - "Wait a few seconds ensuring it doesn't crash."
  - "Run `cargo run -- --smoke-test`."
  - "Verify it exits cleanly after 300 ticks."
