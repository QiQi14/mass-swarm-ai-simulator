---
Task_ID: 03_ws_sync_system
Execution_Phase: Phase B (Parallelizable)
Model_Tier: standard
Target_Files:
  - micro-core/src/systems/ws_sync.rs
  - micro-core/src/systems/mod.rs
Dependencies:
  - Task 01 (ws_protocol definitions)
Context_Bindings:
  - context/architecture.md
---

# STRICT INSTRUCTIONS

1. **Create `micro-core/src/systems/ws_sync.rs`**
   - This file bridges the synchronous Bevy world to the async Tokio world.
   - Define a `Resource`:
     ```rust
     use bevy::prelude::Resource;
     use tokio::sync::broadcast::Sender;
     
     #[derive(Resource, Clone)]
     pub struct BroadcastSender(pub Sender<String>);
     ```
   - Implement the `ws_sync_system`:
     ```rust
     use bevy::prelude::*;
     use crate::components::{EntityId, position::Position, team::Team};
     use crate::config::TickCounter;
     use crate::bridges::ws_protocol::{WsMessage, EntityState};
     
     pub fn ws_sync_system(
         query: Query<(&EntityId, &Position, &Team), Changed<Position>>,
         tick: Res<TickCounter>,
         sender: Res<BroadcastSender>,
     ) {
         let mut moved = Vec::new();
         for (id, pos, team) in query.iter() {
             moved.push(EntityState {
                 id: id.id,
                 x: pos.x,
                 y: pos.y,
                 team: team.clone(),
             });
         }
         
         if !moved.is_empty() {
             let msg = WsMessage::SyncDelta {
                 tick: tick.tick,
                 moved,
             };
             if let Ok(json_str) = serde_json::to_string(&msg) {
                 // Try to send to connected clients. If no clients exist, 
                 // the channel returns an error, which we simply ignore.
                 let _ = sender.0.send(json_str);
             }
         }
     }
     ```

2. **Update `micro-core/src/systems/mod.rs`**
   - Add `pub mod ws_sync;`.
   - Export `BroadcastSender` and `ws_sync_system`.

---

# Verification_Strategy
Test_Type: unit
Test_Stack: cargo test
Acceptance_Criteria:
  - "The `ws_sync_system` can be integrated and built."
  - "Unit test proves that when a `Position` is updated in the mock world, a JSON string is successfully transmitted onto the mocked sender."
Suggested_Test_Commands:
  - `cd micro-core && cargo build`
  - `cd micro-core && cargo test`
