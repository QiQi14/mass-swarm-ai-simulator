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

use micro_core::components::NextEntityId;
use micro_core::config::{SimulationConfig, TickCounter, SimPaused, SimSpeed, SimStepRemaining, ActiveZoneModifiers, InterventionTracker, FactionSpeedBuffs, AggroMaskRegistry, ActiveSubFactions};
use micro_core::bridges::zmq_bridge::ZmqBridgePlugin;
use micro_core::rules::{RemovalEvents, FactionBehaviorMode, NavigationRuleSet, InteractionRuleSet, RemovalRuleSet};
use micro_core::spatial::SpatialHashGrid;
use micro_core::pathfinding::FlowFieldRegistry;
use micro_core::terrain::TerrainGrid;
use micro_core::visibility::FactionVisibility;
use micro_core::systems::{initial_spawn_system, movement_system, tick_counter_system, visibility_update_system, ws_command::WsCommandReceiver, ws_command::ws_command_system, ws_command::step_tick_system, ws_command::ActiveFogFaction};
use micro_core::systems::directive_executor::{LatestDirective, directive_executor_system, zone_tick_system, speed_buff_tick_system};
use micro_core::systems::engine_override::engine_override_system;

/// Maximum ticks before auto-exit in smoke test mode.
/// Set to 0 or remove this system for "run forever" mode.
const SMOKE_TEST_MAX_TICKS: u64 = 300; // ~5 seconds at 60 TPS

fn main() {
    let mut init_entity_count = None;
    let mut is_smoke_test = false;
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        if arg == "--entity-count" {
            if let Some(count) = args.next().and_then(|s| s.parse::<u32>().ok()) {
                init_entity_count = Some(count);
            }
        } else if arg == "--smoke-test" {
            is_smoke_test = true;
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
    app.add_plugins(MinimalPlugins)
        .add_plugins(bevy_state::app::StatesPlugin)
        .set_runner(custom_runner)
        .add_plugins(ZmqBridgePlugin);

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
        .init_resource::<SimPaused>()
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
        .init_resource::<FactionSpeedBuffs>()
        .init_resource::<AggroMaskRegistry>()
        .init_resource::<ActiveSubFactions>()
        .init_resource::<LatestDirective>()
        .insert_resource(micro_core::systems::ws_sync::BroadcastSender(tx))
        .insert_resource(WsCommandReceiver(std::sync::Mutex::new(ws_cmd_rx)))
        // Startup systems (run once)
        .add_systems(Startup, initial_spawn_system)
        // Per-tick systems (run every frame)
        // Simulation systems — gated behind pause/step controls
        .add_systems(Update, (
            micro_core::systems::spawning::wave_spawn_system,
            micro_core::systems::flow_field_update::flow_field_update_system,
            micro_core::spatial::update_spatial_grid_system,
            micro_core::systems::interaction::interaction_system,
            micro_core::systems::removal::removal_system,
            movement_system,
        ).chain().run_if(|paused: Res<SimPaused>, step: Res<SimStepRemaining>| !paused.0 || step.0 > 0))
        .add_systems(Update, (
            directive_executor_system,
            zone_tick_system,
            speed_buff_tick_system,
        ).chain().run_if(|paused: Res<SimPaused>, step: Res<SimStepRemaining>| !paused.0 || step.0 > 0).before(movement_system))
        .add_systems(Update, engine_override_system
            .after(movement_system)
            .run_if(|paused: Res<SimPaused>, step: Res<SimStepRemaining>| !paused.0 || step.0 > 0))
        // Always-running systems (work while paused for terrain painting and fog preview)
        .add_systems(Update, (
            tick_counter_system,
            ws_command_system,
            visibility_update_system,
            step_tick_system
                .after(movement_system),
            micro_core::systems::ws_sync::ws_sync_system,
            log_system,
        ));

    #[cfg(feature = "debug-telemetry")]
    app.add_plugins(micro_core::plugins::TelemetryPlugin);

    if is_smoke_test {
        app.add_systems(Update, smoke_test_exit_system);
    }

    app.run();
}

/// Logs simulation status every 60 ticks (~1 second).
fn log_system(
    counter: Res<TickCounter>,
    query: Query<&micro_core::components::Position>,
) {
    if counter.tick > 0 && counter.tick.is_multiple_of(60) {
        let entity_count = query.iter().count();
        println!("[Tick {}] Entities alive: {}", counter.tick, entity_count);
    }
}

/// Auto-exits after SMOKE_TEST_MAX_TICKS for CI-friendly testing.
/// Remove this system for "run forever" mode when bridges are added.
fn smoke_test_exit_system(
    counter: Res<TickCounter>,
    mut exit: MessageWriter<AppExit>,
) {
    if SMOKE_TEST_MAX_TICKS > 0 && counter.tick >= SMOKE_TEST_MAX_TICKS {
        println!("[Tick {}] Smoke test complete. Exiting.", counter.tick);
        exit.write(AppExit::Success);
    }
}

fn custom_runner(mut app: App) -> AppExit {
    let frame_duration = std::time::Duration::from_secs_f64(1.0 / 60.0);
    loop {
        let start = std::time::Instant::now();
        app.update();
        if let Some(exit_code) = app.should_exit() {
            return exit_code;
        }
        let elapsed = start.elapsed();
        if elapsed < frame_duration {
            std::thread::sleep(frame_duration - elapsed);
        }
    }
}
