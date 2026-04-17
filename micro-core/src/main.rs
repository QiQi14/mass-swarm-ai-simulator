//! # Entry Point
//!
//! Minimal headless Bevy application proving 60 TPS without visualizer.
//!
//! ## Ownership
//! - **Task:** task_04_integration_smoke
//! - **Contract:** implementation_plan.md
//!
//! ## Depends On
//! - `bevy::app::ScheduleRunnerPlugin`
//! - `bevy::prelude::*`
//! - `std::time::Duration`

use bevy::prelude::*;
use bevy_state::app::AppExtStates;
use bevy_state::prelude::in_state;

use micro_core::bridges::zmq_bridge::ZmqBridgePlugin;
use micro_core::components::NextEntityId;
use micro_core::config::{
    ActiveSubFactions, ActiveZoneModifiers, AggroMaskRegistry, BuffConfig, CooldownTracker,
    DensityConfig, FactionBuffs, InterventionTracker, SimPaused, SimSpeed, SimStepRemaining,
    SimulationConfig, TerrainChanged, TickCounter, TrainingMode,
};
use micro_core::pathfinding::FlowFieldRegistry;
use micro_core::rules::{
    FactionBehaviorMode, InteractionRuleSet, NavigationRuleSet, RemovalEvents, RemovalRuleSet,
};
use micro_core::spatial::SpatialHashGrid;
use micro_core::systems::directive_executor::{
    LatestDirective, buff_tick_system, directive_executor_system, zone_tick_system,
};
use micro_core::systems::engine_override::engine_override_system;
use micro_core::systems::{
    initial_spawn_system, movement_system, tick_counter_system, visibility_update_system,
    ws_command::ActiveFogFaction, ws_command::WsCommandReceiver, ws_command::step_tick_system,
    ws_command::ws_command_system,
};
use micro_core::terrain::TerrainGrid;
use micro_core::visibility::FactionVisibility;

/// Maximum ticks before auto-exit in smoke test mode.
/// Set to 0 or remove this system for "run forever" mode.
const SMOKE_TEST_MAX_TICKS: u64 = 300; // ~5 seconds at 60 TPS

fn main() {
    let mut init_entity_count = None;
    let mut is_smoke_test = false;
    let mut is_training = false;
    let mut is_throttle = false;
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        if arg == "--entity-count" {
            if let Some(count) = args.next().and_then(|s| s.parse::<u32>().ok()) {
                init_entity_count = Some(count);
            }
        } else if arg == "--smoke-test" {
            is_smoke_test = true;
        } else if arg == "--training" {
            is_training = true;
        } else if arg == "--throttle" {
            is_throttle = true;
        }
    }

    let (tx, rx) = tokio::sync::broadcast::channel::<String>(100);
    let (ws_cmd_tx, ws_cmd_rx) = std::sync::mpsc::channel::<String>();

    std::thread::spawn(move || {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            micro_core::bridges::ws_server::start_server(rx, ws_cmd_tx).await;
        });
    });

    let mut app = App::new();

    // Configure AI bridge timeout BEFORE the plugin builds.
    // Training: long timeout (30s) — Rust must wait for Python inference.
    // Manual play: ZMQ bridge is NOT started — no Python connection.
    if is_training {
        app.insert_resource(micro_core::bridges::zmq_bridge::AiBridgeConfig {
            send_interval_ticks: 30,
            zmq_timeout_secs: 30,
        });
    }

    app.add_plugins(MinimalPlugins)
        .add_plugins(bevy_state::app::StatesPlugin)
        .set_runner(move |app| custom_runner(app, is_training, is_throttle));

    // ZMQ AI Bridge: ONLY in training mode.
    // In playground mode, Python training can run on port 5555 without
    // hijacking the Rust engine. We register the required resources/state
    // manually so other systems (movement, interaction) don't panic.
    if is_training {
        app.add_plugins(ZmqBridgePlugin);
    } else {
        // Playground: register the resources that systems expect, but
        // do NOT start the ZMQ thread or AI trigger/poll systems.
        use micro_core::bridges::zmq_bridge::{PendingReset, SimState};
        app.init_resource::<PendingReset>();
        app.init_state::<SimState>();
    }

    let mut config = SimulationConfig::default();
    if let Some(c) = init_entity_count {
        config.initial_entity_count = c;
    }

    // Terrain Grid (50×50 cells at 20px each = 1000×1000 world)
    let cell_size = 20.0;
    let grid_w = (config.world_width / cell_size).ceil() as u32;
    let grid_h = (config.world_height / cell_size).ceil() as u32;

    // Resources
    app.insert_resource(config)
        .init_resource::<TickCounter>()
        .init_resource::<NextEntityId>()
        .insert_resource(SimPaused(!is_training))
        .insert_resource(TrainingMode(is_training))
        .init_resource::<SimSpeed>()
        .init_resource::<SimStepRemaining>()
        .init_resource::<RemovalEvents>()
        .init_resource::<FactionBehaviorMode>()
        .init_resource::<NavigationRuleSet>()
        .init_resource::<InteractionRuleSet>()
        .init_resource::<RemovalRuleSet>()
        .insert_resource(SpatialHashGrid::new(cell_size))
        .init_resource::<FlowFieldRegistry>()
        .insert_resource(TerrainGrid::new(grid_w, grid_h, cell_size))
        .insert_resource(FactionVisibility::new(grid_w, grid_h, cell_size))
        .init_resource::<ActiveFogFaction>()
        // Phase 3 resources — required by directive_executor, flow_field_update, movement, zmq_bridge
        .init_resource::<ActiveZoneModifiers>()
        .init_resource::<InterventionTracker>()
        .init_resource::<FactionBuffs>()
        .init_resource::<BuffConfig>()
        .init_resource::<CooldownTracker>()
        .init_resource::<DensityConfig>()
        .init_resource::<AggroMaskRegistry>()
        .init_resource::<ActiveSubFactions>()
        .init_resource::<LatestDirective>()
        .init_resource::<micro_core::config::FactionTacticalOverrides>()
        // Boids 2.0 — Unit type registry for heterogeneous swarm behaviors
        .init_resource::<micro_core::config::UnitTypeRegistry>()
        // Terrain change flag — triggers ws_sync terrain broadcast after reset
        .init_resource::<TerrainChanged>()
        .insert_resource(micro_core::systems::ws_sync::BroadcastSender(tx))
        .insert_resource(WsCommandReceiver(std::sync::Mutex::new(ws_cmd_rx)));

    // Startup systems (run once) — disabled in training mode
    // In training mode, entities are spawned by ResetEnvironment from Python
    if !is_training {
        app.add_systems(Startup, initial_spawn_system);
        app.add_systems(Startup, default_playground_rules_system);
    }

    // Simulation systems — gated behind pause/step controls.
    // In TRAINING mode: also gated on SimState::Running for lock-step sync
    //   → Rust freezes during WaitingForAI (PPO batch collection is deterministic)
    // In PLAY mode: runs continuously regardless of AI state
    //   → If Python is slow, entities keep their last directive (graceful degradation)
    use micro_core::bridges::zmq_bridge::SimState;
    let sim_gate = |paused: Res<SimPaused>, step: Res<SimStepRemaining>| !paused.0 || step.0 > 0;

    if is_training {
        // ── Training: lock-step sync ────────────────────────
        app.add_systems(
            Update,
            (
                micro_core::systems::flow_field_update::flow_field_update_system,
                micro_core::spatial::update_spatial_grid_system,
                micro_core::systems::interaction::interaction_system,
                micro_core::systems::aoe_interaction::aoe_interaction_system,
                micro_core::systems::penetration::penetration_interaction_system,
                micro_core::systems::removal::removal_system,
                micro_core::systems::tactical_sensor::tactical_sensor_system,
                movement_system,
            )
                .chain()
                .run_if(sim_gate)
                .run_if(in_state(SimState::Running)),
        );
        app.add_systems(
            Update,
            (
                directive_executor_system,
                zone_tick_system,
                buff_tick_system,
            )
                .chain()
                .run_if(|paused: Res<SimPaused>, step: Res<SimStepRemaining>| !paused.0 || step.0 > 0)
                .run_if(in_state(SimState::Running))
                .before(movement_system),
        )
        .add_systems(
            Update,
            engine_override_system
                .after(movement_system)
                .run_if(|paused: Res<SimPaused>, step: Res<SimStepRemaining>| !paused.0 || step.0 > 0)
                .run_if(in_state(SimState::Running)),
        )
        .add_systems(
            Update,
            (
                tick_counter_system.run_if(in_state(SimState::Running)),
                ws_command_system,
                visibility_update_system,
                step_tick_system.after(movement_system),
                micro_core::systems::ws_sync::ws_sync_system,
            ),
        );
    } else {
        // ── Play mode: continuous simulation ────────────────
        app.add_systems(
            Update,
            (
                micro_core::systems::flow_field_update::flow_field_update_system,
                micro_core::spatial::update_spatial_grid_system,
                micro_core::systems::interaction::interaction_system,
                micro_core::systems::aoe_interaction::aoe_interaction_system,
                micro_core::systems::penetration::penetration_interaction_system,
                micro_core::systems::removal::removal_system,
                micro_core::systems::tactical_sensor::tactical_sensor_system,
                movement_system,
            )
                .chain()
                .run_if(sim_gate),
        );
        app.add_systems(
            Update,
            (
                directive_executor_system,
                zone_tick_system,
                buff_tick_system,
            )
                .chain()
                .run_if(|paused: Res<SimPaused>, step: Res<SimStepRemaining>| !paused.0 || step.0 > 0)
                .before(movement_system),
        )
        .add_systems(
            Update,
            engine_override_system
                .after(movement_system)
                .run_if(|paused: Res<SimPaused>, step: Res<SimStepRemaining>| !paused.0 || step.0 > 0),
        )
        .add_systems(
            Update,
            (
                tick_counter_system,
                ws_command_system,
                visibility_update_system,
                step_tick_system.after(movement_system),
                micro_core::systems::ws_sync::ws_sync_system,
                log_system,
            ),
        );
    }

    #[cfg(feature = "debug-telemetry")]
    {
        app.add_plugins(micro_core::plugins::TelemetryPlugin);
        app.add_systems(
            Update,
            micro_core::plugins::telemetry::flow_field_broadcast_system
                .after(micro_core::systems::flow_field_update::flow_field_update_system),
        );
    }

    if is_smoke_test {
        app.add_systems(Update, smoke_test_exit_system);
    }

    app.run();
}

/// Sets up a default "Swarm vs Defender" game profile for playground mode.
/// Without this, the context-agnostic engine starts with zero rules and
/// entities just sit idle. Provides bidirectional chase, proximity combat,
/// and removal at stat[0] ≤ 0 so the initial spawn works immediately.
///
/// Users can override these via WS commands (set_navigation, set_interaction,
/// set_removal, Algorithm Test presets, or Game Setup wizard).
fn default_playground_rules_system(
    mut nav_rules: ResMut<NavigationRuleSet>,
    mut interaction_rules: ResMut<InteractionRuleSet>,
    mut removal_rules: ResMut<RemovalRuleSet>,
) {
    use micro_core::bridges::zmq_protocol::NavigationTarget;
    use micro_core::rules::{InteractionRule, NavigationRule, RemovalCondition, RemovalRule, StatEffect};

    // Faction 0 chases Faction 1, and vice versa
    nav_rules.rules = vec![
        NavigationRule {
            follower_faction: 0,
            target: NavigationTarget::Faction { faction_id: 1 },
        },
        NavigationRule {
            follower_faction: 1,
            target: NavigationTarget::Faction { faction_id: 0 },
        },
    ];

    // Bidirectional proximity combat: 15-unit range, -10 DPS to stat[0]
    interaction_rules.rules = vec![
        InteractionRule {
            source_faction: 0,
            target_faction: 1,
            range: 15.0,
            effects: vec![StatEffect {
                stat_index: 0,
                delta_per_second: -10.0,
            }],
            source_class: None,
            target_class: None,
            range_stat_index: None,
            mitigation: None,
            cooldown_ticks: None,
            aoe: None,
            penetration: None,
        },
        InteractionRule {
            source_faction: 1,
            target_faction: 0,
            range: 15.0,
            effects: vec![StatEffect {
                stat_index: 0,
                delta_per_second: -20.0,
            }],
            source_class: None,
            target_class: None,
            range_stat_index: None,
            mitigation: None,
            cooldown_ticks: None,
            aoe: None,
            penetration: None,
        },
    ];

    // Remove entities when stat[0] (HP) ≤ 0
    removal_rules.rules = vec![RemovalRule {
        stat_index: 0,
        threshold: 0.0,
        condition: RemovalCondition::LessOrEqual,
    }];

    println!("[Playground] Default game profile loaded: bidirectional chase + combat + removal");
}

/// Logs simulation status every 60 ticks (~1 second).
fn log_system(counter: Res<TickCounter>, query: Query<&micro_core::components::Position>) {
    if counter.tick > 0 && counter.tick.is_multiple_of(60) {
        let entity_count = query.iter().count();
        println!("[Tick {}] Entities alive: {}", counter.tick, entity_count);
    }
}

/// Auto-exits after SMOKE_TEST_MAX_TICKS for CI-friendly testing.
/// Remove this system for "run forever" mode when bridges are added.
fn smoke_test_exit_system(counter: Res<TickCounter>, mut exit: MessageWriter<AppExit>) {
    if SMOKE_TEST_MAX_TICKS > 0 && counter.tick >= SMOKE_TEST_MAX_TICKS {
        println!("[Tick {}] Smoke test complete. Exiting.", counter.tick);
        exit.write(AppExit::Success);
    }
}

fn custom_runner(mut app: App, is_training: bool, is_throttle: bool) -> AppExit {
    let frame_duration = std::time::Duration::from_secs_f64(1.0 / 60.0);
    // Throttle: sleep to maintain 60 TPS even in training mode (human-observable)
    let should_sleep = !is_training || is_throttle;
    loop {
        let start = std::time::Instant::now();
        app.update();
        if let Some(exit_code) = app.should_exit() {
            return exit_code;
        }
        if should_sleep {
            let elapsed = start.elapsed();
            if elapsed < frame_duration {
                std::thread::sleep(frame_duration - elapsed);
            }
        }
    }
}
