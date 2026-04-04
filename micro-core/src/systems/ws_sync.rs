//! # WebSocket Sync System
//!
//! Bridges the synchronous Bevy world to the async Tokio world.
//! Extracts changed entities and broadcasts state updates to connected WebSocket clients.
//!
//! ## Ownership
//! - **Task:** task_03_ws_sync_system
//! - **Contract:** Phase 1, Micro-Phase 2 WebSocket Message Schema

use bevy::prelude::*;
use crate::components::{EntityId, FactionId, Position, StatBlock, Velocity};
use crate::config::TickCounter;
use crate::bridges::ws_protocol::{WsMessage, EntityState};
use tokio::sync::broadcast::Sender;

/// Resource wrapping the async broadcast sender.
#[derive(Resource, Clone)]
pub struct BroadcastSender(pub Sender<String>);

/// Extracts entities that have moved and sends a state synchronization message
/// to the async broadcast channel.
pub fn ws_sync_system(
    query: Query<(&EntityId, &Position, &Velocity, &FactionId, &StatBlock), Changed<Position>>,
    tick: Res<TickCounter>,
    sender: Res<BroadcastSender>,
) {
    let mut moved = Vec::new();
    for (id, pos, vel, faction, stat_block) in query.iter() {
        moved.push(EntityState {
            id: id.id,
            x: pos.x,
            y: pos.y,
            dx: vel.dx,
            dy: vel.dy,
            faction_id: faction.0,
            stats: stat_block.0.to_vec(),
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

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use bevy::app::App;
    use tokio::sync::broadcast;

    #[test]
    fn test_ws_sync_system_broadcasts_changes() {
        // Arrange
        let mut app = App::new();
        let (tx, mut rx) = broadcast::channel::<String>(10);
        app.insert_resource(BroadcastSender(tx));
        app.insert_resource(TickCounter { tick: 42 });

        app.add_systems(Update, ws_sync_system);

        app.world_mut().spawn((
            EntityId { id: 100 },
            Position { x: 5.0, y: 10.0 },
            Velocity { dx: 1.5, dy: -2.5 },
            FactionId(0),
            StatBlock::with_defaults(&[(0, 0.8)]),
        ));

        // Act
        app.update();

        // Assert
        let msg = rx.try_recv().expect("Should have received a message");
        assert!(msg.contains(r#""type":"SyncDelta""#));
        assert!(msg.contains(r#""tick":42"#));
        assert!(msg.contains(r#""id":100"#));
        assert!(msg.contains(r#""x":5.0"#));
        assert!(msg.contains(r#""y":10.0"#));
        assert!(msg.contains(r#""dx":1.5"#));
        assert!(msg.contains(r#""dy":-2.5"#));
        assert!(msg.contains(r#""faction_id":0"#));
        assert!(msg.contains(r#""stats":[0.8,0.0,0.0,0.0,0.0,0.0,0.0,0.0]"#));
    }
}
