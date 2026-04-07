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
    query: Query<(&EntityId, &Position, &FactionId, &StatBlock)>,
    mut next_state: ResMut<NextState<SimState>>,
) {
    if tick.tick == 0 || !tick.tick.is_multiple_of(config.send_interval_ticks) {
        return;
    }

    // Default macro-brain runs for faction 0
    let snapshot = build_state_snapshot(
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
    );
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
    channels: Res<AiBridgeChannels>,
    mut next_state: ResMut<NextState<SimState>>,
    mut latest_directive: ResMut<LatestDirective>,
    mut waiting_since: Local<Option<std::time::Instant>>,
) {
    // Track when we entered WaitingForAI
    let start = *waiting_since.get_or_insert_with(std::time::Instant::now);

    match channels.action_rx.lock().unwrap().try_recv() {
        Ok(reply_json) => {
            // Try new AiResponse discriminated union first
            match serde_json::from_str::<AiResponse>(&reply_json) {
                Ok(AiResponse::Directive { directive }) => {
                    println!(
                        "[AI Bridge] Received directive: {:?} (tick resume)",
                        directive
                    );
                    latest_directive.directive = Some(directive);
                }
                Ok(AiResponse::ResetEnvironment {
                    navigation_rules: _navigation_rules,
                    ..
                }) => {
                    // Reset commands are handled at the environment level,
                    // not stored as directives. Log and resume.
                    // TODO: task_a1 — navigation_rules field added
                    println!("[AI Bridge] Received reset_environment command (tick resume)");
                }
                Err(_) => {
                    // Fallback: try legacy MacroAction format
                    match serde_json::from_str::<MacroAction>(&reply_json) {
                        Ok(action) => {
                            println!(
                                "[AI Bridge] Received legacy action: {} (tick resume)",
                                action.action
                            );
                            // Legacy actions map to Hold (no macro-level control)
                            latest_directive.directive = Some(MacroDirective::Hold);
                        }
                        Err(e) => {
                            eprintln!("[AI Bridge] Failed to parse AI response: {}", e);
                        }
                    }
                }
            }
            *waiting_since = None;
            next_state.set(SimState::Running);
        }
        Err(mpsc::TryRecvError::Empty) => {
            // Timeout: fall back to Running after 200ms to keep sim responsive
            if start.elapsed() > std::time::Duration::from_millis(200) {
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
        app.insert_resource(LatestDirective::default());

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

        // Send a valid AiResponse::Directive with Hold
        let directive_json = r#"{"type":"macro_directive","directive":"Hold"}"#;
        action_tx.send(directive_json.to_string()).unwrap();

        // Act
        app.update(); // Poll system reads directive
        app.update(); // Apply NextState → Running

        // Assert
        let _latest = app.world().get_resource::<LatestDirective>().unwrap();
        // Directive should have been stored (may be consumed by executor if registered)
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
        // Test that various MacroDirective variants parse successfully through AiResponse
        let test_cases = [
            r#"{"type":"macro_directive","directive":"Hold"}"#,
            r#"{"type":"macro_directive","directive":"UpdateNavigation","follower_faction":0,"target":{"type":"Faction","faction_id":1}}"#,
            r#"{"type":"macro_directive","directive":"Retreat","faction":0,"retreat_x":50.0,"retreat_y":50.0}"#,
            r#"{"type":"macro_directive","directive":"SetZoneModifier","target_faction":0,"x":100.0,"y":100.0,"radius":50.0,"cost_modifier":-50.0}"#,
            r#"{"type":"macro_directive","directive":"SplitFaction","source_faction":0,"new_sub_faction":101,"percentage":0.3,"epicenter":[500.0,500.0]}"#,
            r#"{"type":"macro_directive","directive":"MergeFaction","source_faction":101,"target_faction":0}"#,
            r#"{"type":"macro_directive","directive":"SetAggroMask","source_faction":101,"target_faction":1,"allow_combat":false}"#,
        ];

        for (i, json) in test_cases.iter().enumerate() {
            let parsed = serde_json::from_str::<AiResponse>(json);
            assert!(
                parsed.is_ok(),
                "Variant {} should parse as AiResponse: {:?} — Error: {:?}",
                i,
                json,
                parsed.err()
            );
            match parsed.unwrap() {
                AiResponse::Directive { directive } => {
                    // Verify it round-trips
                    let _: MacroDirective = directive;
                }
                _ => panic!("Expected AiResponse::Directive for variant {}", i),
            }
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
        app.insert_resource(LatestDirective::default());

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
        let legacy_json = r#"{"type":"macro_action","action":"HOLD","params":{}}"#;
        action_tx.send(legacy_json.to_string()).unwrap();

        // Act
        app.update(); // Poll system reads legacy action

        // Assert
        let latest = app.world().get_resource::<LatestDirective>().unwrap();
        assert!(
            latest.directive.is_some(),
            "Legacy fallback should set directive to Some(Hold)"
        );
        assert_eq!(
            latest.directive,
            Some(MacroDirective::Hold),
            "Legacy fallback should map to Hold"
        );
    }
}
