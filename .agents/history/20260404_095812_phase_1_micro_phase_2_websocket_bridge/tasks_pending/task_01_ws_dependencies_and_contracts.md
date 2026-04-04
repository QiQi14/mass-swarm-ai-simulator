---
Task_ID: 01_ws_dependencies_and_contracts
Execution_Phase: Phase A (Parallelizable)
Model_Tier: basic
Target_Files:
  - micro-core/Cargo.toml
  - micro-core/src/lib.rs
  - micro-core/src/bridges/mod.rs
  - micro-core/src/bridges/ws_protocol.rs
Dependencies: None
Context_Bindings: []
---

# STRICT INSTRUCTIONS

1. **Update `Cargo.toml`**
   - Add the following dependencies to `micro-core/Cargo.toml`:
     ```toml
     tokio = { version = "1.51.0", features = ["rt-multi-thread", "macros", "sync"] }
     tokio-tungstenite = "0.29.0"
     futures-util = "0.3.32"
     ```

2. **Create `micro-core/src/bridges/ws_protocol.rs`**
   - Import `serde::{Serialize, Deserialize}` and `crate::components::team::Team`.
   - Implement `EntityState`:
     ```rust
     use serde::{Deserialize, Serialize};
     use crate::components::team::Team;

     #[derive(Serialize, Deserialize, Debug, Clone)]
     pub struct EntityState {
         pub id: u32,
         pub x: f32,
         pub y: f32,
         pub team: Team,
     }
     ```
   - Implement `WsMessage`:
     ```rust
     #[derive(Serialize, Deserialize, Debug, Clone)]
     #[serde(tag = "type")]
     pub enum WsMessage {
         SyncDelta {
             tick: u64,
             moved: Vec<EntityState>,
         }
     }
     ```

3. **Create `micro-core/src/bridges/mod.rs`**
   - Add `pub mod ws_protocol;`.

4. **Update `micro-core/src/lib.rs`**
   - Add `pub mod bridges;` after the existing module declarations (`pub mod components;`, `pub mod config;`, `pub mod systems;`).
   - Do NOT remove or modify any existing lines.

---

# Verification_Strategy
Test_Type: unit
Test_Stack: cargo
Acceptance_Criteria:
  - "Cargo check compiles the newly added modules without errors."
  - "The JSON serialization derives compile successfully."
Suggested_Test_Commands:
  - `cd micro-core && cargo check`
