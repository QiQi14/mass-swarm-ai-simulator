//! # WebSocket Command System
//!
//! Receives and processes commands from the Debug Visualizer via WebSocket.
//!
//! ## Ownership
//! - **Task:** task_03_ws_bidirectional_commands
//! - **Contract:** implementation_plan.md → Phase 1 Micro-Phase 4
//!
//! ## Depends On
//! - `crate::config::{SimPaused, SimSpeed, SimStepRemaining, SimulationConfig}`
//! - `crate::bridges::ws_protocol::WsCommand`
//! - `crate::components::{Position, FactionId, StatBlock, Velocity, NextEntityId, EntityId}`

use bevy::prelude::*;
use std::sync::{mpsc, Mutex};
use rand::Rng;

use crate::bridges::ws_protocol::WsCommand;
use crate::components::{EntityId, FactionId, NextEntityId, Position, StatBlock, Velocity};
use crate::config::{SimPaused, SimSpeed, SimStepRemaining, SimulationConfig};

/// Resource wrapping the standard library MPSC receiver for WS commands.
#[derive(Resource)]
pub struct WsCommandReceiver(pub Mutex<mpsc::Receiver<String>>);

/// Processes incoming WebSocket commands and updates simulation state accordingly.
#[allow(clippy::too_many_arguments)]
pub fn ws_command_system(
    receiver: Res<WsCommandReceiver>,
    mut commands: Commands,
    mut next_id: ResMut<NextEntityId>,
    mut paused: ResMut<SimPaused>,
    mut speed: ResMut<SimSpeed>,
    mut step: ResMut<SimStepRemaining>,
    _config: Res<SimulationConfig>,
    faction_query: Query<(Entity, &FactionId)>,
) {
    let Ok(rx) = receiver.0.lock() else { return; };
    while let Ok(json) = rx.try_recv() {
        if let Ok(cmd) = serde_json::from_str::<WsCommand>(&json) {
            match cmd.cmd.as_str() {
                "toggle_sim" => {
                    paused.0 = !paused.0;
                    println!("[WS Command] Simulation {}", if paused.0 { "paused" } else { "resumed" });
                }
                "step" => {
                    let count = cmd.params.get("count")
                        .and_then(|v| v.as_u64())
                        .unwrap_or(1) as u32;
                    step.0 = count;
                    println!("[WS Command] Stepping {} tick(s)", count);
                }
                "spawn_wave" => {
                    let faction_id = cmd.params.get("faction_id").and_then(|v| v.as_u64()).unwrap_or(0) as u32;
                    let amount = cmd.params.get("amount").and_then(|v| v.as_u64()).unwrap_or(1) as u32;
                    let x = cmd.params.get("x").and_then(|v| v.as_f64()).unwrap_or(0.0) as f32;
                    let y = cmd.params.get("y").and_then(|v| v.as_f64()).unwrap_or(0.0) as f32;

                    let mut rng = rand::rng();
                    for _ in 0..amount {
                        commands.spawn((
                            EntityId { id: next_id.0 },
                            Position { x, y },
                            Velocity {
                                dx: rng.random_range(-1.0..1.0),
                                dy: rng.random_range(-1.0..1.0),
                            },
                            FactionId(faction_id),
                            StatBlock::with_defaults(&[(0, 1.0)]),
                        ));
                        next_id.0 += 1;
                    }
                    println!("[WS Command] Spawned {} faction_{} at ({}, {})", amount, faction_id, x, y);
                }
                "set_speed" => {
                    if let Some(m) = cmd.params.get("multiplier").and_then(|v| v.as_f64()) {
                        speed.multiplier = m as f32;
                        println!("[WS Command] Set speed to {}", speed.multiplier);
                    }
                }
                "kill_all" => {
                    if let Some(fid) = cmd.params.get("faction_id").and_then(|v| v.as_u64()) {
                        let target_faction = FactionId(fid as u32);
                        let mut count = 0;
                        for (entity, faction) in faction_query.iter() {
                            if *faction == target_faction {
                                commands.entity(entity).despawn();
                                count += 1;
                            }
                        }
                        println!("[WS Command] Killed {} faction_{} entities", count, fid);
                    }
                }
                other => {
                    eprintln!("[WS Command] Unknown: {}", other);
                }
            }
        }
    }
}

/// Decrements step counter and auto-pauses when step mode completes.
/// Runs every tick when steps remain (regardless of SimPaused).
pub fn step_tick_system(
    mut step: ResMut<SimStepRemaining>,
    mut paused: ResMut<SimPaused>,
) {
    if step.0 > 0 {
        step.0 -= 1;
        if step.0 == 0 {
            paused.0 = true;
            println!("[Step Mode] Step complete, auto-paused");
        }
    }
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use bevy::app::App;

    #[test]
    fn test_step_tick_system_decrements_and_pauses() {
        // Arrange
        let mut app = App::new();
        app.insert_resource(SimStepRemaining(2));
        app.insert_resource(SimPaused(false));
        app.add_systems(Update, step_tick_system);

        // Act 1
        app.update();
        assert_eq!(app.world().resource::<SimStepRemaining>().0, 1);
        assert_eq!(app.world().resource::<SimPaused>().0, false);

        // Act 2
        app.update();
        assert_eq!(app.world().resource::<SimStepRemaining>().0, 0);
        assert_eq!(app.world().resource::<SimPaused>().0, true);
    }
}
