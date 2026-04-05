//! # Telemetry Plugin
//!
//! Zero-cost telemetry infrastructure behind `debug-telemetry` feature flag.
//! Provides `PerfTelemetry` resource and `flow_field_broadcast_system`.
//!
//! ## Ownership
//! - **Task:** task_07_ipc_visualizer_upgrades
//! - **Contract:** implementation_plan_task_07.md → §2.1
//!
//! ## Feature Gate
//! This entire module is `#[cfg(feature = "debug-telemetry")]`.
//! Production builds (`--no-default-features`) compile this out completely.

use bevy::prelude::*;
use serde::{Deserialize, Serialize};

use crate::config::{SimulationConfig, TickCounter};
use crate::pathfinding::flow_field::FlowFieldRegistry;
use crate::systems::ws_sync::BroadcastSender;
use crate::bridges::ws_protocol::WsMessage;

/// Accumulated per-tick performance metrics.
/// Inserted as a Bevy Resource ONLY by TelemetryPlugin.
/// Systems access via `Option<ResMut<PerfTelemetry>>` — returns `None`
/// when the plugin is not loaded (production builds).
#[derive(Resource, Debug, Default, Clone, Serialize, Deserialize)]
pub struct PerfTelemetry {
    pub spatial_us: u32,
    pub flow_field_us: u32,
    pub interaction_us: u32,
    pub removal_us: u32,
    pub movement_us: u32,
    pub ws_sync_us: u32,
    pub entity_count: u32,
}

pub struct TelemetryPlugin;

impl Plugin for TelemetryPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<PerfTelemetry>();
    }
}

/// Broadcasts flow field vectors to the debug visualizer.
/// Compiled only with `debug-telemetry` feature.
pub fn flow_field_broadcast_system(
    tick: Res<TickCounter>,
    config: Res<SimulationConfig>,
    registry: Res<FlowFieldRegistry>,
    sender: Res<BroadcastSender>,
) {
    if tick.tick == 0 || !tick.tick.is_multiple_of(config.flow_field_update_interval) {
        return;
    }

    for (&faction_id, field) in registry.fields.iter() {
        let grid_w = field.width;
        let grid_h = field.height;

        let mut vectors = Vec::with_capacity((grid_w * grid_h) as usize);
        
        for y in 0..grid_h {
            for x in 0..grid_w {
                let wx = x as f32 * field.cell_size + field.cell_size / 2.0;
                let wy = y as f32 * field.cell_size + field.cell_size / 2.0;
                let dir = field.sample(Vec2::new(wx, wy));
                vectors.push([dir.x, dir.y]);
            }
        }

        let msg = WsMessage::FlowFieldSync {
            target_faction: faction_id,
            grid_width: grid_w,
            grid_height: grid_h,
            cell_size: field.cell_size,
            vectors,
        };

        if let Ok(json_str) = serde_json::to_string(&msg) {
            let _ = sender.0.send(json_str);
        }
    }
}
