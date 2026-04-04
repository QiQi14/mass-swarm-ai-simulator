//! # ZMQ Bridge — Bevy Systems
//!
//! ECS systems for AI trigger/poll and the state snapshot builder.
//! These run inside Bevy's `Update` schedule, gated by `SimState`.
//!
//! ## Ownership
//! - **Task:** task_07_zmq_bridge_plugin
//! - **Contract:** implementation_plan.md → Proposed Changes → 3. Rust System Layer

use bevy::prelude::*;
use bevy_state::prelude::*;
use std::sync::mpsc;

use super::config::{AiBridgeChannels, AiBridgeConfig, SimState};
use crate::bridges::zmq_protocol::{
    EntitySnapshot, MacroAction, StateSnapshot, SummarySnapshot, WorldSize,
};
use crate::components::{EntityId, FactionId, Position, StatBlock};
use crate::config::{SimulationConfig, TickCounter};

/// Builds a StateSnapshot from the current ECS state.
///
/// Queries all entities with EntityId, Position, and Team components
/// and packages them into the IPC-compatible StateSnapshot format.
///
/// # Arguments
/// * `tick` - Current simulation tick
/// * `sim_config` - World dimensions for the world_size field
/// * `query` - All entities with EntityId, Position, and Team
fn build_state_snapshot(
    tick: &TickCounter,
    sim_config: &SimulationConfig,
    query: &Query<(&EntityId, &Position, &FactionId, &StatBlock)>,
) -> StateSnapshot {
    let mut faction_counts = std::collections::HashMap::new();
    let mut faction_sum_stats: std::collections::HashMap<u32, Vec<f32>> = std::collections::HashMap::new();
    let mut entities = Vec::new();

    for (eid, pos, faction, stat_block) in query.iter() {
        let count = faction_counts.entry(faction.0).or_insert(0);
        *count += 1;

        let sums = faction_sum_stats.entry(faction.0).or_insert_with(|| vec![0.0; crate::components::MAX_STATS]);
        for (i, &val) in stat_block.0.iter().enumerate() {
            sums[i] += val;
        }

        entities.push(EntitySnapshot {
            id: eid.id,
            x: pos.x,
            y: pos.y,
            faction_id: faction.0,
            stats: stat_block.0.to_vec(),
        });
    }

    let mut faction_avg_stats: std::collections::HashMap<u32, Vec<f32>> = std::collections::HashMap::new();
    for (&fid, count) in &faction_counts {
        if let Some(sums) = faction_sum_stats.get(&fid) {
            let avgs: Vec<f32> = sums.iter().map(|s| s / (*count as f32)).collect();
            faction_avg_stats.insert(fid, avgs);
        }
    }

    StateSnapshot {
        msg_type: "state_snapshot".to_string(),
        tick: tick.tick,
        world_size: WorldSize {
            w: sim_config.world_width,
            h: sim_config.world_height,
        },
        entities,
        summary: SummarySnapshot {
            faction_counts,
            faction_avg_stats,
        },
    }
}

/// Triggers AI communication every N ticks.
///
/// Runs only when `SimState::Running`. Builds a state snapshot from
/// the current ECS state, serializes it to JSON, and sends it to the
/// background ZMQ thread. Transitions to `WaitingForAI` on success.
///
/// # Arguments
/// * `tick` - Current tick counter
/// * `config` - AI bridge configuration (send interval)
/// * `sim_config` - World dimensions
/// * `channels` - Channel to background ZMQ thread
/// * `query` - All entities with EntityId, Position, and Team
/// * `next_state` - State transition handle
pub(super) fn ai_trigger_system(
    tick: Res<TickCounter>,
    config: Res<AiBridgeConfig>,
    sim_config: Res<SimulationConfig>,
    channels: Res<AiBridgeChannels>,
    query: Query<(&EntityId, &Position, &FactionId, &StatBlock)>,
    mut next_state: ResMut<NextState<SimState>>,
) {
    if tick.tick == 0 || !tick.tick.is_multiple_of(config.send_interval_ticks) {
        return;
    }

    let snapshot = build_state_snapshot(&tick, &sim_config, &query);
    let json = serde_json::to_string(&snapshot).unwrap();

    // try_send is non-blocking. If the channel is full (previous request
    // still in flight), skip this tick.
    if channels.state_tx.try_send(json).is_ok() {
        next_state.set(SimState::WaitingForAI);
    }
}

/// Polls for AI response from the background ZMQ thread.
///
/// Runs only when `SimState::WaitingForAI`. Uses non-blocking
/// `try_recv()` so other systems (tick counter, WS sync) keep running.
/// On response (real or fallback HOLD), transitions back to `Running`.
///
/// # Arguments
/// * `channels` - Channel from background ZMQ thread
/// * `next_state` - State transition handle
pub(super) fn ai_poll_system(
    channels: Res<AiBridgeChannels>,
    mut next_state: ResMut<NextState<SimState>>,
) {
    match channels.action_rx.lock().unwrap().try_recv() {
        Ok(reply_json) => {
            match serde_json::from_str::<MacroAction>(&reply_json) {
                Ok(action) => {
                    println!("[AI Bridge] Received action: {} (tick resume)", action.action);
                    // Phase 3 Macro-Brain: apply the action to ECS will happen later
                }
                Err(e) => {
                    eprintln!("[AI Bridge] Failed to parse macro action: {}", e);
                }
            }
            next_state.set(SimState::Running);
        }
        Err(mpsc::TryRecvError::Empty) => {
            // Still waiting — do nothing, system will run again next tick
        }
        Err(mpsc::TryRecvError::Disconnected) => {
            eprintln!("[AI Bridge] Background thread disconnected!");
            next_state.set(SimState::Running);
        }
    }
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    #[test]
    fn test_ai_trigger_system_skips_non_interval_ticks() {
        // Arrange
        let mut app = App::new();
        app.add_plugins(bevy_state::app::StatesPlugin);
        app.init_state::<SimState>();
        app.insert_resource(AiBridgeConfig {
            send_interval_ticks: 30,
            zmq_timeout_secs: 5,
        });

        // Mock channels
        let (state_tx, _state_rx) = mpsc::sync_channel::<String>(1);
        let (_action_tx, action_rx) = mpsc::sync_channel::<String>(1);
        app.insert_resource(AiBridgeChannels {
            state_tx,
            action_rx: Mutex::new(action_rx),
        });
        app.insert_resource(SimulationConfig::default());
        app.insert_resource(TickCounter { tick: 15 }); // Not divisible by 30

        app.add_systems(Update, ai_trigger_system.run_if(in_state(SimState::Running)));

        app.world_mut().spawn((
            EntityId { id: 1 },
            Position { x: 10.0, y: 20.0 },
            FactionId(0),
            StatBlock::default(),
        ));

        // Act
        app.update();

        // Assert
        let state = app.world().get_resource::<State<SimState>>().unwrap();
        assert_eq!(state.get(), &SimState::Running, "Should still be Running since tick % 30 != 0");
    }

    #[test]
    fn test_ai_trigger_system_fires_on_interval() {
        // Arrange
        let mut app = App::new();
        app.add_plugins(bevy_state::app::StatesPlugin);
        app.init_state::<SimState>();
        app.insert_resource(AiBridgeConfig {
            send_interval_ticks: 30,
            zmq_timeout_secs: 5,
        });

        // Mock channels
        let (state_tx, _state_rx) = mpsc::sync_channel::<String>(1);
        let (_action_tx, action_rx) = mpsc::sync_channel::<String>(1);
        app.insert_resource(AiBridgeChannels {
            state_tx,
            action_rx: Mutex::new(action_rx),
        });
        app.insert_resource(SimulationConfig::default());
        app.insert_resource(TickCounter { tick: 30 }); // Divisible by 30

        app.add_systems(Update, ai_trigger_system.run_if(in_state(SimState::Running)));

        app.world_mut().spawn((
            EntityId { id: 1 },
            Position { x: 10.0, y: 20.0 },
            FactionId(0),
            StatBlock::default(),
        ));

        // Act
        app.update(); // triggers system, sets NextState
        app.update(); // applies NextState -> State

        // Assert
        let state = app.world().get_resource::<State<SimState>>().unwrap();
        assert_eq!(state.get(), &SimState::WaitingForAI, "Should transition to WaitingForAI");
    }
}
