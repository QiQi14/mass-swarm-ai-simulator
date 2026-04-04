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
use micro_core::systems::{initial_spawn_system, movement_system, tick_counter_system, ws_command::WsCommandReceiver, ws_command::ws_command_system, ws_command::step_tick_system};

/// Maximum ticks before auto-exit in smoke test mode.
/// Set to 0 or remove this system for "run forever" mode.
const SMOKE_TEST_MAX_TICKS: u64 = 300; // ~5 seconds at 60 TPS

fn main() {
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
        .add_plugins(ZmqBridgePlugin)
        // Resources
        .init_resource::<SimulationConfig>()
        .init_resource::<TickCounter>()
        .init_resource::<NextEntityId>()
        .init_resource::<SimPaused>()
        .init_resource::<SimSpeed>()
        .init_resource::<SimStepRemaining>()
        .insert_resource(micro_core::systems::ws_sync::BroadcastSender(tx))
        .insert_resource(WsCommandReceiver(std::sync::Mutex::new(ws_cmd_rx)))
        // Startup systems (run once)
        .add_systems(Startup, initial_spawn_system)
        // Per-tick systems (run every frame)
        .add_systems(Update, (
            tick_counter_system,
            ws_command_system,
            movement_system
                .run_if(in_state(SimState::Running))
                .run_if(|paused: Res<SimPaused>, step: Res<SimStepRemaining>| !paused.0 || step.0 > 0),
            step_tick_system
                .run_if(in_state(SimState::Running))
                .after(movement_system),
            log_system,
            micro_core::systems::ws_sync::ws_sync_system,
        ));

    if std::env::args().any(|a| a == "--smoke-test") {
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
