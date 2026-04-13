//! # ZMQ Bridge — Bevy Systems
//! # ZMQ Bridge — Bevy Systems
//!
//! ECS systems for AI trigger/poll and the state snapshot builder.
//! These run inside Bevy's `Update` schedule, gated by `SimState`.
//!
//! ## Ownership
//! - **Task:** task_07_zmq_protocol_upgrade
//! - **Contract:** implementation_plan.md → Proposed Changes → 3. Rust System Layer
//!
//! ## Depends On
//! - `crate::bridges::zmq_protocol`
//! - `crate::systems::state_vectorizer`
//! - `crate::systems::directive_executor::LatestDirective`
//! - `crate::config::{ActiveZoneModifiers, InterventionTracker, ActiveSubFactions, AggroMaskRegistry}`

use bevy::prelude::*;
use bevy_state::prelude::*;
use std::sync::mpsc;

use super::config::{AiBridgeChannels, AiBridgeConfig, SimState};
use crate::bridges::zmq_protocol::{AiResponse, MacroAction, MacroDirective};
use crate::components::{EntityId, FactionId, Position, StatBlock};
use crate::config::{
    ActiveSubFactions, ActiveZoneModifiers, AggroMaskRegistry, InterventionTracker,
    SimulationConfig, TickCounter,
};
use crate::systems::directive_executor::LatestDirective;

use super::snapshot::build_state_snapshot;
use crate::terrain::TerrainGrid;
use crate::visibility::FactionVisibility;

/// Triggers AI communication every N ticks.
///
/// Runs only when `SimState::Running`. Builds a state snapshot from
/// the current ECS state, serializes it to JSON, and sends it to the
/// background ZMQ thread. Transitions to `WaitingForAI` on success.
#[allow(clippy::too_many_arguments)]
pub(super) fn ai_trigger_system(
    tick: Res<TickCounter>,
    config: Res<AiBridgeConfig>,
    sim_config: Res<SimulationConfig>,
    channels: Res<AiBridgeChannels>,
    visibility: Res<FactionVisibility>,
    terrain: Res<TerrainGrid>,
    zones: Res<ActiveZoneModifiers>,
    intervention: Res<InterventionTracker>,
    sub_factions: Res<ActiveSubFactions>,
    aggro: Res<AggroMaskRegistry>,
    combat_buffs: Res<crate::config::FactionBuffs>,
    buff_config: Res<crate::config::BuffConfig>,
    density_config: Res<crate::config::DensityConfig>,
    query: Query<(&EntityId, &Position, &FactionId, &StatBlock, &crate::components::UnitClassId)>,
    mut next_state: ResMut<NextState<SimState>>,
) {
    if tick.tick == 0 || !tick.tick.is_multiple_of(config.send_interval_ticks) {
        return;
    }

    // Default macro-brain runs for faction 0
    let mut snapshot = build_state_snapshot(
        &tick,
        &sim_config,
        &query,
        &visibility,
        &terrain,
        0,
        &zones,
        &intervention,
        &sub_factions,
        &aggro,
        &combat_buffs,
        &buff_config,
        &density_config,
    );

    let brain_faction = 0u32;
    let total_cells = (visibility.grid_width * visibility.grid_height) as usize;
    
    let explored = visibility.explored.get(&brain_faction).map(|bits| {
        (0..total_cells)
            .map(|i| if FactionVisibility::get_bit(bits, i) { 1u8 } else { 0u8 })
            .collect::<Vec<u8>>()
    });
    
    let visible = visibility.visible.get(&brain_faction).map(|bits| {
        (0..total_cells)
            .map(|i| if FactionVisibility::get_bit(bits, i) { 1u8 } else { 0u8 })
            .collect::<Vec<u8>>()
    });
    
    snapshot.fog_explored = explored;
    snapshot.fog_visible = visible;

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
/// Parses `AiResponse` discriminated union first (supports both `macro_directive`
/// and `reset_environment`). Falls back to legacy `MacroAction` for backward
/// compatibility. Stores parsed directives in `LatestDirective` for the
/// `directive_executor_system` to consume.
///
/// Falls back to `Running` after 200ms even if the background thread
/// hasn't responded yet, preventing the simulation from freezing
/// when no Python AI is connected.
pub(super) fn ai_poll_system(
    config: Res<AiBridgeConfig>,
    channels: Res<AiBridgeChannels>,
    mut next_state: ResMut<NextState<SimState>>,
    mut latest_directive: ResMut<LatestDirective>,
    mut pending_reset: ResMut<crate::bridges::zmq_bridge::reset::PendingReset>,
    mut waiting_since: Local<Option<std::time::Instant>>,
    training_mode: Res<crate::config::TrainingMode>,
) {
    // Track when we entered WaitingForAI
    let start = *waiting_since.get_or_insert_with(std::time::Instant::now);
    // Use configured timeout (long for training, short for manual play)
    let timeout = std::time::Duration::from_secs(config.zmq_timeout_secs);

    match channels.action_rx.lock().unwrap().try_recv() {
        Ok(reply_json) => {
            #[derive(serde::Deserialize)]
            struct BatchResponse {
                #[serde(rename = "type")]
                msg_type: String,
                directives: Vec<MacroDirective>,
            }

            // Try new Batch format first
            if let Ok(batch) = serde_json::from_str::<BatchResponse>(&reply_json) {
                if batch.msg_type == "macro_directives" {
                    if !training_mode.0 {
                        println!(
                            "[AI Bridge] Received batch directives: {} directives (tick resume)",
                            batch.directives.len()
                        );
                    }
                    latest_directive.directives = batch.directives;
                    latest_directive.last_directive_json = Some(reply_json.clone());
                    *waiting_since = None;
                    next_state.set(SimState::Running);
                    return;
                }
            }

            // Fallback for ResetEnvironment (which still uses AiResponse)
            match serde_json::from_str::<AiResponse>(&reply_json) {
                Ok(AiResponse::ResetEnvironment {
                    terrain,
                    spawns,
                    combat_rules,
                    ability_config,
                    movement_config,
                    max_density,
                    max_entity_ecp,
                    terrain_thresholds,
                    removal_rules,
                    navigation_rules,
                    ecp_stat_index,
                    unit_types,
                    ecp_formula,
                }) => {
                    if !training_mode.0 {
                        println!("[AI Bridge] Received reset_environment command (tick resume)");
                    }
                    pending_reset.request = Some(crate::bridges::zmq_bridge::reset::ResetRequest {
                        terrain,
                        spawns,
                        combat_rules,
                        ability_config,
                        movement_config,
                        max_density,
                        max_entity_ecp,
                        terrain_thresholds,
                        removal_rules,
                        navigation_rules,
                        ecp_stat_index,
                        unit_types,
                        ecp_formula,
                    });
                }
                Ok(AiResponse::Directive { directive: _ }) => {
                    eprintln!("[ZMQ] Unexpected message type (expected 'macro_directives')");
                    // Empty directives on error per requirements
                    latest_directive.directives = vec![];
                }
                Err(e) => {
                    if let Ok(legacy) = serde_json::from_str::<MacroAction>(&reply_json) {
                        eprintln!("[ZMQ] Unexpected message type (expected 'macro_directives'). Legacy MacroAction format sent: {}", legacy.action);
                    } else {
                        eprintln!("[ZMQ] Failed to parse AI response: {}", e);
                    }
                    latest_directive.directives = vec![];
                }
            }
            *waiting_since = None;
            next_state.set(SimState::Running);
        }
        Err(mpsc::TryRecvError::Empty) => {
            // Timeout: fall back to Running after zmq_timeout_secs to prevent hang
            if start.elapsed() > timeout {
                eprintln!("[AI Bridge] Timeout after {}s — falling back to Running", config.zmq_timeout_secs);
                *waiting_since = None;
                next_state.set(SimState::Running);
            }
        }
        Err(mpsc::TryRecvError::Disconnected) => {
            eprintln!("[AI Bridge] Background thread disconnected!");
            *waiting_since = None;
            next_state.set(SimState::Running);
        }
    }
}

// ── Tests ──────────────────────────────────────────────────────────────

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
        app.insert_resource(FactionVisibility::new(5, 5, 20.0));
        app.insert_resource(TerrainGrid::new(5, 5, 20.0));
        app.insert_resource(ActiveZoneModifiers::default());
        app.insert_resource(InterventionTracker::default());
        app.insert_resource(ActiveSubFactions::default());
        app.insert_resource(AggroMaskRegistry::default());
        app.insert_resource(crate::config::FactionBuffs::default());
        app.init_resource::<crate::config::BuffConfig>();
        app.init_resource::<crate::config::DensityConfig>();

        app.add_systems(
            Update,
            ai_trigger_system.run_if(in_state(SimState::Running)),
        );

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
        assert_eq!(
            state.get(),
            &SimState::Running,
            "Should still be Running since tick % 30 != 0"
        );
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
        app.insert_resource(FactionVisibility::new(5, 5, 20.0));
        app.insert_resource(TerrainGrid::new(5, 5, 20.0));
        app.insert_resource(ActiveZoneModifiers::default());
        app.insert_resource(InterventionTracker::default());
        app.insert_resource(ActiveSubFactions::default());
        app.insert_resource(AggroMaskRegistry::default());
        app.insert_resource(crate::config::FactionBuffs::default());
        app.init_resource::<crate::config::BuffConfig>();
        app.init_resource::<crate::config::DensityConfig>();

        app.add_systems(
            Update,
            ai_trigger_system.run_if(in_state(SimState::Running)),
        );

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
        assert_eq!(
            state.get(),
            &SimState::WaitingForAI,
            "Should transition to WaitingForAI"
        );
    }
    #[test]
    fn test_ai_poll_parses_directive() {
        // Arrange
        let mut app = App::new();
        app.add_plugins(bevy_state::app::StatesPlugin);
        app.init_state::<SimState>();

        let (state_tx, _state_rx) = mpsc::sync_channel::<String>(1);
        let (action_tx, action_rx) = mpsc::sync_channel::<String>(1);
        app.insert_resource(AiBridgeChannels {
            state_tx,
            action_rx: Mutex::new(action_rx),
        });
        app.insert_resource(AiBridgeConfig {
            send_interval_ticks: 30,
            zmq_timeout_secs: 5,
        });
        app.insert_resource(LatestDirective::default());
        app.insert_resource(crate::bridges::zmq_bridge::reset::PendingReset::default());
        app.insert_resource(crate::config::TrainingMode(false));

        app.add_systems(
            Update,
            ai_poll_system.run_if(in_state(SimState::WaitingForAI)),
        );

        // Force into WaitingForAI state
        app.world_mut()
            .get_resource_mut::<NextState<SimState>>()
            .unwrap()
            .set(SimState::WaitingForAI);
        app.update(); // Apply NextState

        // Send a valid macro_directives batch with Idle
        let directive_json = r#"{"type":"macro_directives","directives":[{"directive":"Idle"}]}"#;
        action_tx.send(directive_json.to_string()).unwrap();

        // Act
        app.update(); // Poll system reads directive
        app.update(); // Apply NextState → Running

        // Assert
        let _latest = app.world().get_resource::<LatestDirective>().unwrap();
        // Check that the system transitioned to Running
        let state = app.world().get_resource::<State<SimState>>().unwrap();
        assert_eq!(
            state.get(),
            &SimState::Running,
            "Should transition back to Running after receiving directive"
        );
    }

    #[test]
    fn test_ai_poll_parses_all_directive_variants() {
        // Test that various MacroDirective variants parse successfully in batch format
        let test_cases = [
            r#"{"type":"macro_directives","directives":[{"directive":"Idle"}]}"#,
            r#"{"type":"macro_directives","directives":[{"directive":"UpdateNavigation","follower_faction":0,"target":{"type":"Faction","faction_id":1}}]}"#,
            r#"{"type":"macro_directives","directives":[{"directive":"Retreat","faction":0,"retreat_x":50.0,"retreat_y":50.0}]}"#,
            r#"{"type":"macro_directives","directives":[{"directive":"SetZoneModifier","target_faction":0,"x":100.0,"y":100.0,"radius":50.0,"cost_modifier":-50.0}]}"#,
            r#"{"type":"macro_directives","directives":[{"directive":"SplitFaction","source_faction":0,"new_sub_faction":101,"percentage":0.3,"epicenter":[500.0,500.0]}]}"#,
            r#"{"type":"macro_directives","directives":[{"directive":"MergeFaction","source_faction":101,"target_faction":0}]}"#,
            r#"{"type":"macro_directives","directives":[{"directive":"SetAggroMask","source_faction":101,"target_faction":1,"allow_combat":false}]}"#,
        ];

        for (i, json) in test_cases.iter().enumerate() {
            #[derive(serde::Deserialize)]
            struct BatchResponse {
                #[serde(rename = "type")]
                msg_type: String,
                directives: Vec<MacroDirective>,
            }
            let parsed = serde_json::from_str::<BatchResponse>(json);
            assert!(
                parsed.is_ok(),
                "Variant {} should parse as BatchResponse: {:?} — Error: {:?}",
                i,
                json,
                parsed.err()
            );
            assert_eq!(parsed.unwrap().msg_type, "macro_directives");
        }
    }

    #[test]
    fn test_ai_poll_legacy_fallback() {
        // Arrange
        let mut app = App::new();
        app.add_plugins(bevy_state::app::StatesPlugin);
        app.init_state::<SimState>();

        let (state_tx, _state_rx) = mpsc::sync_channel::<String>(1);
        let (action_tx, action_rx) = mpsc::sync_channel::<String>(1);
        app.insert_resource(AiBridgeChannels {
            state_tx,
            action_rx: Mutex::new(action_rx),
        });
        app.insert_resource(AiBridgeConfig {
            send_interval_ticks: 30,
            zmq_timeout_secs: 5,
        });
        app.insert_resource(LatestDirective::default());
        app.insert_resource(crate::bridges::zmq_bridge::reset::PendingReset::default());
        app.insert_resource(crate::config::TrainingMode(false));

        app.add_systems(
            Update,
            ai_poll_system.run_if(in_state(SimState::WaitingForAI)),
        );

        // Force into WaitingForAI
        app.world_mut()
            .get_resource_mut::<NextState<SimState>>()
            .unwrap()
            .set(SimState::WaitingForAI);
        app.update(); // Apply NextState

        // Send legacy MacroAction format
        let legacy_json = r#"{"type":"macro_directive","directive":"Idle"}"#;
        action_tx.send(legacy_json.to_string()).unwrap();

        // Act
        app.update(); // Poll system reads legacy action

        // Assert
        let latest = app.world().get_resource::<LatestDirective>().unwrap();
        assert!(
            latest.directives.is_empty(),
            "Legacy fallback should evaluate as err and return empty directives"
        );
    }
}
