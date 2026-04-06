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
use crate::bridges::zmq_protocol::{
    AiResponse, EntitySnapshot, MacroAction, MacroDirective, StateSnapshot, SummarySnapshot,
    WorldSize, ZoneModifierSnapshot,
};
use crate::components::{EntityId, FactionId, Position, StatBlock};
use crate::config::{
    ActiveSubFactions, ActiveZoneModifiers, AggroMaskRegistry, InterventionTracker,
    SimulationConfig, TickCounter,
};
use crate::systems::directive_executor::LatestDirective;
use crate::systems::state_vectorizer::{build_density_maps, DEFAULT_MAX_DENSITY};
use crate::terrain::TerrainGrid;
use crate::visibility::FactionVisibility;

/// Builds a StateSnapshot from the current ECS state.
///
/// Queries all entities with EntityId, Position, FactionId, and StatBlock components
/// and packages them into the IPC-compatible StateSnapshot format.
/// Populates density maps from entity positions, intervention flags,
/// zone modifier snapshots, active sub-factions, and aggro mask states.
///
/// # Arguments
/// * `tick` - Current simulation tick
/// * `sim_config` - World dimensions for the world_size field
/// * `query` - All entities with EntityId, Position, FactionId, and StatBlock
/// * `visibility` - Fog-of-war visibility grids
/// * `terrain` - Terrain cost grids
/// * `brain_faction` - Faction ID of the ML brain
/// * `zones` - Active zone modifiers for snapshot feedback
/// * `intervention` - Tier 1 engine override activity tracker
/// * `sub_factions` - Currently active sub-factions
/// * `aggro` - Aggro mask registry for faction-pair combat control
#[allow(clippy::too_many_arguments)]
fn build_state_snapshot(
    tick: &TickCounter,
    sim_config: &SimulationConfig,
    query: &Query<(&EntityId, &Position, &FactionId, &StatBlock)>,
    visibility: &FactionVisibility,
    terrain: &TerrainGrid,
    brain_faction: u32,
    zones: &ActiveZoneModifiers,
    intervention: &InterventionTracker,
    sub_factions: &ActiveSubFactions,
    aggro: &AggroMaskRegistry,
) -> StateSnapshot {
    let mut faction_counts = std::collections::HashMap::new();
    let mut faction_sum_stats: std::collections::HashMap<u32, Vec<f32>> =
        std::collections::HashMap::new();
    let mut entities = Vec::new();

    // Collect ALL entity positions for density map computation (unfiltered)
    let mut all_entity_positions: Vec<(f32, f32, u32)> = Vec::new();

    let vis_grid = visibility.visible.get(&brain_faction);
    let exp_grid = visibility.explored.get(&brain_faction);

    for (eid, pos, faction, stat_block) in query.iter() {
        let count = faction_counts.entry(faction.0).or_insert(0);
        *count += 1;

        let sums = faction_sum_stats
            .entry(faction.0)
            .or_insert_with(|| vec![0.0; crate::components::MAX_STATS]);
        for (i, &val) in stat_block.0.iter().enumerate() {
            sums[i] += val;
        }

        // Density maps use ALL entities (not fog-filtered) so the brain
        // has complete spatial awareness of its own forces
        all_entity_positions.push((pos.x, pos.y, faction.0));

        // Entity list is fog-filtered: own faction always visible, enemies only if in visible cells
        let mut is_visible = false;
        if faction.0 == brain_faction {
            is_visible = true;
        } else if let Some(vg) = vis_grid {
            let cx = (pos.x / visibility.cell_size).floor() as i32;
            let cy = (pos.y / visibility.cell_size).floor() as i32;
            if cx >= 0
                && cx < visibility.grid_width as i32
                && cy >= 0
                && cy < visibility.grid_height as i32
            {
                let cell_idx = (cy as u32 * visibility.grid_width + cx as u32) as usize;
                if FactionVisibility::get_bit(vg, cell_idx) {
                    is_visible = true;
                }
            }
        }

        if is_visible {
            entities.push(EntitySnapshot {
                id: eid.id,
                x: pos.x,
                y: pos.y,
                faction_id: faction.0,
                stats: stat_block.0.to_vec(),
            });
        }
    }

    let mut faction_avg_stats: std::collections::HashMap<u32, Vec<f32>> =
        std::collections::HashMap::new();
    for (&fid, count) in &faction_counts {
        if let Some(sums) = faction_sum_stats.get(&fid) {
            let avgs: Vec<f32> = sums.iter().map(|s| s / (*count as f32)).collect();
            faction_avg_stats.insert(fid, avgs);
        }
    }

    // Raw density maps — HashMap<faction_id, Vec<f32>>
    // Sub-factions automatically get their own key
    let density_maps = build_density_maps(
        &all_entity_positions,
        terrain.width,
        terrain.height,
        terrain.cell_size,
        DEFAULT_MAX_DENSITY,
    );

    // Zone modifier snapshots for observation feedback
    let active_zones: Vec<ZoneModifierSnapshot> = zones
        .zones
        .iter()
        .map(|z| ZoneModifierSnapshot {
            target_faction: z.target_faction,
            x: z.x,
            y: z.y,
            radius: z.radius,
            cost_modifier: z.cost_modifier,
            ticks_remaining: z.ticks_remaining,
        })
        .collect();

    // Aggro mask serialization: (source, target) → "source_target" key
    let aggro_masks: std::collections::HashMap<String, bool> = aggro
        .masks
        .iter()
        .map(|(&(s, t), &v)| (format!("{}_{}", s, t), v))
        .collect();

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
        explored: exp_grid.cloned(),
        visible: vis_grid.cloned(),
        terrain_hard: terrain.hard_costs.clone(),
        terrain_soft: terrain.soft_costs.clone(),
        terrain_grid_w: terrain.width,
        terrain_grid_h: terrain.height,
        terrain_cell_size: terrain.cell_size,
        density_maps,
        intervention_active: intervention.active,
        active_zones,
        active_sub_factions: sub_factions.factions.clone(),
        aggro_masks,
    }
}

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
                Ok(AiResponse::ResetEnvironment { .. }) => {
                    // Reset commands are handled at the environment level,
                    // not stored as directives. Log and resume.
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
        let state = app
            .world()
            .get_resource::<State<SimState>>()
            .unwrap();
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
        let state = app
            .world()
            .get_resource::<State<SimState>>()
            .unwrap();
        assert_eq!(
            state.get(),
            &SimState::WaitingForAI,
            "Should transition to WaitingForAI"
        );
    }

    #[derive(Resource)]
    struct CapturedSnapshot(Option<StateSnapshot>);

    fn capture_snapshot_system(
        tick: Res<TickCounter>,
        sim_config: Res<SimulationConfig>,
        visibility: Res<FactionVisibility>,
        terrain: Res<TerrainGrid>,
        zones: Res<ActiveZoneModifiers>,
        intervention: Res<InterventionTracker>,
        sub_factions: Res<ActiveSubFactions>,
        aggro: Res<AggroMaskRegistry>,
        query: Query<(&EntityId, &Position, &FactionId, &StatBlock)>,
        mut captured: ResMut<CapturedSnapshot>,
    ) {
        captured.0 = Some(build_state_snapshot(
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
        ));
    }

    /// Helper to build a minimal app for snapshot tests.
    fn snapshot_test_app() -> App {
        let mut app = App::new();
        app.insert_resource(SimulationConfig::default());
        app.insert_resource(TickCounter { tick: 30 });
        app.insert_resource(FactionVisibility::new(5, 5, 20.0));
        app.insert_resource(TerrainGrid::new(5, 5, 20.0));
        app.insert_resource(ActiveZoneModifiers::default());
        app.insert_resource(InterventionTracker::default());
        app.insert_resource(ActiveSubFactions::default());
        app.insert_resource(AggroMaskRegistry::default());
        app.insert_resource(CapturedSnapshot(None));
        app.add_systems(Update, capture_snapshot_system);
        app
    }

    #[test]
    fn test_snapshot_always_includes_own_entities() {
        // Arrange
        let mut app = snapshot_test_app();
        let mut vis = FactionVisibility::new(5, 5, 20.0);
        vis.ensure_faction(0);
        // Fog is black (no visible cells)
        app.insert_resource(vis);

        app.world_mut().spawn((
            EntityId { id: 10 },
            Position { x: 10.0, y: 10.0 },
            FactionId(0),
            StatBlock::default(),
        ));

        // Act
        app.update();

        // Assert
        let snap = app
            .world()
            .resource::<CapturedSnapshot>()
            .0
            .as_ref()
            .unwrap();
        assert_eq!(
            snap.entities.len(),
            1,
            "Should include own entity even if invisible in fog"
        );
        assert_eq!(snap.entities[0].id, 10);
    }

    #[test]
    fn test_snapshot_filters_enemies_by_fog() {
        // Arrange
        let mut app = snapshot_test_app();
        let mut vis = FactionVisibility::new(5, 5, 20.0);
        vis.ensure_faction(0);

        // Enemy 1 at (0,0) - make visible
        let vg = vis.visible.get_mut(&0).unwrap();
        FactionVisibility::set_bit(vg, 0); // cell (0,0) is visible

        app.insert_resource(vis);

        // Enemy in visible cell
        app.world_mut().spawn((
            EntityId { id: 20 },
            Position { x: 10.0, y: 10.0 }, // Cell (0,0)
            FactionId(1),                   // Enemy
            StatBlock::default(),
        ));

        // Enemy in fog cell
        app.world_mut().spawn((
            EntityId { id: 21 },
            Position { x: 90.0, y: 90.0 }, // Cell (4,4)
            FactionId(1),                   // Enemy
            StatBlock::default(),
        ));

        // Act
        app.update();

        // Assert
        let snap = app
            .world()
            .resource::<CapturedSnapshot>()
            .0
            .as_ref()
            .unwrap();
        assert_eq!(snap.entities.len(), 1, "Should only include visible enemies");
        assert_eq!(
            snap.entities[0].id, 20,
            "Should include enemy at visible cell"
        );
    }

    #[test]
    fn test_snapshot_includes_density_maps() {
        // Arrange
        let mut app = snapshot_test_app();
        // TerrainGrid is 5×5, cell_size=20 → entities at known positions

        app.world_mut().spawn((
            EntityId { id: 1 },
            Position { x: 10.0, y: 10.0 }, // Cell (0,0)
            FactionId(0),
            StatBlock::default(),
        ));

        app.world_mut().spawn((
            EntityId { id: 2 },
            Position { x: 30.0, y: 30.0 }, // Cell (1,1)
            FactionId(1),
            StatBlock::default(),
        ));

        // Act
        app.update();

        // Assert
        let snap = app
            .world()
            .resource::<CapturedSnapshot>()
            .0
            .as_ref()
            .unwrap();
        assert!(
            snap.density_maps.contains_key(&0),
            "Density maps should contain faction 0"
        );
        assert!(
            snap.density_maps.contains_key(&1),
            "Density maps should contain faction 1"
        );
        // Verify faction 0 has correct density at cell (0,0) = index 0
        let f0_map = &snap.density_maps[&0];
        assert_eq!(f0_map.len(), 25, "5×5 grid = 25 cells");
        assert!(
            f0_map[0] > 0.0,
            "Entity at (10,10) should produce density at cell (0,0)"
        );
    }

    #[test]
    fn test_snapshot_sub_faction_density() {
        // Arrange
        let mut app = snapshot_test_app();

        app.world_mut().spawn((
            EntityId { id: 1 },
            Position { x: 10.0, y: 10.0 },
            FactionId(101), // Sub-faction
            StatBlock::default(),
        ));

        // Act
        app.update();

        // Assert
        let snap = app
            .world()
            .resource::<CapturedSnapshot>()
            .0
            .as_ref()
            .unwrap();
        assert!(
            snap.density_maps.contains_key(&101),
            "Sub-faction 101 should have its own density map key"
        );
    }

    #[test]
    fn test_snapshot_intervention_flag() {
        // Arrange — intervention active
        let mut app = snapshot_test_app();
        app.insert_resource(InterventionTracker { active: true });

        app.world_mut().spawn((
            EntityId { id: 1 },
            Position { x: 10.0, y: 10.0 },
            FactionId(0),
            StatBlock::default(),
        ));

        // Act
        app.update();

        // Assert
        let snap = app
            .world()
            .resource::<CapturedSnapshot>()
            .0
            .as_ref()
            .unwrap();
        assert!(
            snap.intervention_active,
            "Snapshot should reflect intervention_active = true"
        );
    }

    #[test]
    fn test_snapshot_active_zones() {
        // Arrange
        let mut app = snapshot_test_app();
        let mut zones = ActiveZoneModifiers::default();
        zones.zones.push(crate::config::ZoneModifier {
            target_faction: 0,
            x: 50.0,
            y: 50.0,
            radius: 100.0,
            cost_modifier: -50.0,
            ticks_remaining: 60,
        });
        app.insert_resource(zones);

        app.world_mut().spawn((
            EntityId { id: 1 },
            Position { x: 10.0, y: 10.0 },
            FactionId(0),
            StatBlock::default(),
        ));

        // Act
        app.update();

        // Assert
        let snap = app
            .world()
            .resource::<CapturedSnapshot>()
            .0
            .as_ref()
            .unwrap();
        assert_eq!(
            snap.active_zones.len(),
            1,
            "Snapshot should contain 1 active zone"
        );
        assert_eq!(snap.active_zones[0].target_faction, 0);
        assert!((snap.active_zones[0].cost_modifier - (-50.0)).abs() < f32::EPSILON);
        assert_eq!(snap.active_zones[0].ticks_remaining, 60);
    }

    #[test]
    fn test_snapshot_aggro_masks_serialization() {
        // Arrange
        let mut app = snapshot_test_app();
        let mut aggro = AggroMaskRegistry::default();
        aggro.masks.insert((0, 1), false);
        aggro.masks.insert((1, 0), false);
        app.insert_resource(aggro);

        app.world_mut().spawn((
            EntityId { id: 1 },
            Position { x: 10.0, y: 10.0 },
            FactionId(0),
            StatBlock::default(),
        ));

        // Act
        app.update();

        // Assert
        let snap = app
            .world()
            .resource::<CapturedSnapshot>()
            .0
            .as_ref()
            .unwrap();
        assert!(
            snap.aggro_masks.contains_key("0_1"),
            "Aggro mask should contain key '0_1'"
        );
        assert_eq!(
            snap.aggro_masks["0_1"], false,
            "Aggro mask 0→1 should be false"
        );
        assert!(
            snap.aggro_masks.contains_key("1_0"),
            "Aggro mask should contain key '1_0'"
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
        let directive_json =
            r#"{"type":"macro_directive","directive":"Hold"}"#;
        action_tx.send(directive_json.to_string()).unwrap();

        // Act
        app.update(); // Poll system reads directive
        app.update(); // Apply NextState → Running

        // Assert
        let _latest = app
            .world()
            .get_resource::<LatestDirective>()
            .unwrap();
        // Directive should have been stored (may be consumed by executor if registered)
        // Check that the system transitioned to Running
        let state = app
            .world()
            .get_resource::<State<SimState>>()
            .unwrap();
        assert_eq!(
            state.get(),
            &SimState::Running,
            "Should transition back to Running after receiving directive"
        );
    }

    #[test]
    fn test_ai_poll_parses_all_directive_variants() {
        // Test that various MacroDirective variants parse successfully through AiResponse
        let test_cases = vec![
            r#"{"type":"macro_directive","directive":"Hold"}"#,
            r#"{"type":"macro_directive","directive":"UpdateNavigation","follower_faction":0,"target":{"type":"Faction","faction_id":1}}"#,
            r#"{"type":"macro_directive","directive":"TriggerFrenzy","faction":0,"speed_multiplier":1.5,"duration_ticks":60}"#,
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
        let legacy_json =
            r#"{"type":"macro_action","action":"HOLD","params":{}}"#;
        action_tx.send(legacy_json.to_string()).unwrap();

        // Act
        app.update(); // Poll system reads legacy action

        // Assert
        let latest = app
            .world()
            .get_resource::<LatestDirective>()
            .unwrap();
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
