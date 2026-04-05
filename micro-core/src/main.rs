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
use bevy_state::prelude::in_state;

use micro_core::components::NextEntityId;
use micro_core::config::{SimulationConfig, TickCounter, SimPaused, SimSpeed, SimStepRemaining};
use micro_core::bridges::zmq_bridge::{SimState, ZmqBridgePlugin};
use micro_core::rules::{RemovalEvents, FactionBehaviorMode, NavigationRuleSet, InteractionRuleSet, RemovalRuleSet};
use micro_core::spatial::SpatialHashGrid;
use micro_core::pathfinding::FlowFieldRegistry;
use micro_core::systems::{initial_spawn_system, movement_system, tick_counter_system, ws_command::WsCommandReceiver, ws_command::ws_command_system, ws_command::step_tick_system};

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
        .insert_resource(SpatialHashGrid::new(20.0))
        .init_resource::<FlowFieldRegistry>()
        .insert_resource(micro_core::systems::ws_sync::BroadcastSender(tx))
        .insert_resource(WsCommandReceiver(std::sync::Mutex::new(ws_cmd_rx)))
        // Startup systems (run once)
        .add_systems(Startup, initial_spawn_system)
        // Per-tick systems (run every frame)
        .add_systems(Update, (
            micro_core::systems::spawning::wave_spawn_system,
            micro_core::systems::flow_field_update::flow_field_update_system,
            micro_core::spatial::update_spatial_grid_system,
            micro_core::systems::interaction::interaction_system,
            micro_core::systems::removal::removal_system,
            movement_system,
            micro_core::systems::ws_sync::ws_sync_system,
        ).chain().run_if(in_state(SimState::Running)).run_if(|paused: Res<SimPaused>, step: Res<SimStepRemaining>| !paused.0 || step.0 > 0))
        .add_systems(Update, (
            tick_counter_system,
            ws_command_system,
            step_tick_system
                .run_if(in_state(SimState::Running))
                .after(movement_system),
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
