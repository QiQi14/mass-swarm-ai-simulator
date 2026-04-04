---
Task_ID: 06_zmq_protocol_cargo
Execution_Phase: Phase A (Parallelizable — after MP2 Task 04)
Model_Tier: basic
Target_Files:
  - micro-core/Cargo.toml
  - micro-core/src/bridges/mod.rs
  - micro-core/src/bridges/zmq_protocol.rs
Dependencies:
  - MP2 Task 04 (integration_ws) must be COMPLETE
Context_Bindings:
  - context/ipc-protocol.md
---

# STRICT INSTRUCTIONS

> **Feature:** P1_MP3 — ZeroMQ Bridge + Stub AI Round-Trip
> **Role:** Add ZMQ dependency to Cargo.toml, extend bridges barrel, and create the ZMQ protocol data types.
> **IMPORTANT:** This task runs AFTER MP2 Task 04 is complete. The `Cargo.toml` and `bridges/mod.rs` already contain MP2's additions (tokio, tokio-tungstenite, futures-util, ws_protocol, ws_server). You are APPENDING to these files, not replacing them.

## Pre-condition Check

Before modifying any file, verify that `micro-core/src/bridges/mod.rs` already contains `pub mod ws_protocol;` and `pub mod ws_server;`. If it does NOT, STOP — MP2 is not yet complete.

## Instructions

1. **Append to `micro-core/Cargo.toml`**
   - Add the following dependency AFTER the existing dependencies:
     ```toml
     zeromq = "0.5"
     ```
   - Do NOT modify or remove any existing dependencies.

2. **Append to `micro-core/src/bridges/mod.rs`**
   - Add these two lines AFTER the existing module declarations:
     ```rust
     pub mod zmq_protocol;
     pub mod zmq_bridge;
     ```
   - Do NOT modify or remove existing `pub mod ws_protocol;` or `pub mod ws_server;` lines.
   - Follow the project's Rust code standards (see `skills/rust-code-standards`). Update the module-level doc comment to mention the ZMQ modules.

3. **Create `micro-core/src/bridges/zmq_protocol.rs`**
   - This file defines the exact JSON schemas from `context/ipc-protocol.md` for the AI bridge.
   - Implement the following structs EXACTLY as specified:

   ```rust
   //! # ZMQ Protocol Data Types
   //!
   //! Serialization models for the AI Bridge (Rust ↔ Python) IPC.
   //! Maps exactly to the schemas in `docs/ipc-protocol.md`.
   //!
   //! ## Ownership
   //! - **Task:** task_06_zmq_protocol_cargo
   //! - **Contract:** implementation_plan.md → Proposed Changes → 2. Rust Data Layer
   //!
   //! ## Depends On
   //! - `serde`
   //! - `serde_json`

   use serde::{Deserialize, Serialize};

   /// Entity snapshot for the AI state payload.
   ///
   /// Maps to the `entities[]` array in the `state_snapshot` IPC message.
   #[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
   pub struct EntitySnapshot {
       pub id: u32,
       pub x: f32,
       pub y: f32,
       /// Team as a lowercase string: "swarm" or "defender".
       pub team: String,
   }

   /// Summary statistics for the neural network observation space.
   ///
   /// Maps to the `summary` object in the `state_snapshot` IPC message.
   #[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
   pub struct SummarySnapshot {
       pub swarm_count: u32,
       pub defender_count: u32,
       pub avg_swarm_health: f32,
       pub avg_defender_health: f32,
   }

   /// World size descriptor.
   ///
   /// Maps to the `world_size` object in IPC messages.
   #[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
   pub struct WorldSize {
       pub w: f32,
       pub h: f32,
   }

   /// Full state snapshot sent from Rust → Python via ZMQ REQ.
   ///
   /// The `msg_type` field serializes as `"type"` in JSON to match
   /// the IPC protocol's mandatory discriminator field.
   #[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
   pub struct StateSnapshot {
       #[serde(rename = "type")]
       pub msg_type: String,
       pub tick: u64,
       pub world_size: WorldSize,
       pub entities: Vec<EntitySnapshot>,
       pub summary: SummarySnapshot,
   }

   /// Macro action received from Python → Rust via ZMQ REP.
   ///
   /// The `action` field contains the action vocabulary string
   /// (e.g., "HOLD", "FLANK_LEFT"). The `params` field is a
   /// flexible JSON object for action-specific parameters.
   #[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
   pub struct MacroAction {
       #[serde(rename = "type")]
       pub msg_type: String,
       pub action: String,
       pub params: serde_json::Value,
   }

   // ── Tests ──────────────────────────────────────────────────────────────

   #[cfg(test)]
   mod tests {
       use super::*;

       #[test]
       fn test_state_snapshot_serialization_roundtrip() {
           // Arrange
           let snapshot = StateSnapshot {
               msg_type: "state_snapshot".to_string(),
               tick: 1234,
               world_size: WorldSize { w: 1000.0, h: 1000.0 },
               entities: vec![
                   EntitySnapshot {
                       id: 1,
                       x: 150.3,
                       y: 200.1,
                       team: "swarm".to_string(),
                   },
               ],
               summary: SummarySnapshot {
                   swarm_count: 5000,
                   defender_count: 200,
                   avg_swarm_health: 0.72,
                   avg_defender_health: 0.91,
               },
           };

           // Act
           let json = serde_json::to_string(&snapshot).unwrap();
           let deserialized: StateSnapshot = serde_json::from_str(&json).unwrap();

           // Assert
           assert_eq!(snapshot, deserialized, "StateSnapshot should survive JSON roundtrip");
       }

       #[test]
       fn test_state_snapshot_json_has_type_field() {
           // Arrange
           let snapshot = StateSnapshot {
               msg_type: "state_snapshot".to_string(),
               tick: 0,
               world_size: WorldSize { w: 100.0, h: 100.0 },
               entities: vec![],
               summary: SummarySnapshot {
                   swarm_count: 0,
                   defender_count: 0,
                   avg_swarm_health: 0.0,
                   avg_defender_health: 0.0,
               },
           };

           // Act
           let json = serde_json::to_string(&snapshot).unwrap();

           // Assert
           assert!(
               json.contains("\"type\":\"state_snapshot\""),
               "JSON must use 'type' key (not 'msg_type'): {}",
               json
           );
       }

       #[test]
       fn test_macro_action_deserialization() {
           // Arrange
           let json = r#"{"type":"macro_action","action":"HOLD","params":{}}"#;

           // Act
           let action: MacroAction = serde_json::from_str(json).unwrap();

           // Assert
           assert_eq!(action.msg_type, "macro_action", "type field should be 'macro_action'");
           assert_eq!(action.action, "HOLD", "action should be 'HOLD'");
       }

       #[test]
       fn test_macro_action_with_params() {
           // Arrange
           let json = r#"{"type":"macro_action","action":"FLANK_LEFT","params":{"intensity":0.8}}"#;

           // Act
           let action: MacroAction = serde_json::from_str(json).unwrap();

           // Assert
           assert_eq!(action.action, "FLANK_LEFT", "action should be 'FLANK_LEFT'");
           assert!(
               action.params.get("intensity").is_some(),
               "params should contain 'intensity' key"
           );
       }
   }
   ```

---

# Verification_Strategy
Test_Type: unit
Test_Stack: cargo
Acceptance_Criteria:
  - "`cargo check` succeeds with no errors."
  - "`cargo clippy` has zero warnings."
  - "`cargo test zmq_protocol` passes all 4 tests."
  - "JSON output matches the schema in `docs/ipc-protocol.md` (type field, not msg_type)."
Suggested_Test_Commands:
  - `cd micro-core && cargo check`
  - `cd micro-core && cargo clippy`
  - `cd micro-core && cargo test zmq_protocol`
