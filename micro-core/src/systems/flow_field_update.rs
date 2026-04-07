//! # Flow Field Update System
//!
//! Recalculates flow fields at ~2 TPS (every N ticks).
//! Decoupled from the 60 TPS physics loop.
//!
//! ## Ownership
//! - **Task:** task_07_zmq_protocol_upgrade
//! - **Contract:** implementation_plan.md → Contract 7
//!
//! ## Depends On
//! - `crate::bridges::zmq_protocol::NavigationTarget`
//! - `crate::config::ActiveZoneModifiers`

use crate::bridges::zmq_protocol::NavigationTarget;
use crate::components::{FactionId, Position};
use crate::config::{SimulationConfig, TickCounter};
use crate::pathfinding::FlowFieldRegistry;
use crate::rules::NavigationRuleSet;
use crate::systems::flow_field_safety::apply_zone_overlays;
use crate::visibility::FactionVisibility;
use bevy::prelude::*;

/// Recalculates flow fields for navigating factions.
/// Runs every `config.flow_field_update_interval` ticks (~2 TPS at interval=30).
///
/// **Fog-of-War aware:** Only enemy positions visible to the follower faction
/// are used as flow field goals. If no enemies are visible, the flow field
/// is removed and entities idle until new targets enter their vision.
///
/// **NavigationTarget support:** Handles both `Faction` (dynamic chase) and
/// `Waypoint` (static coordinate) targets. Waypoints bypass fog filtering.
///
/// **Zone modifier overlay:** Applies cost overlays from `ActiveZoneModifiers`
/// before flow field calculation. Respects PATCH 2: MOSES EFFECT GUARD —
/// wall tiles (`u16::MAX`) are immune to cost modifiers.
#[allow(clippy::too_many_arguments)]
pub fn flow_field_update_system(
    telemetry: Option<ResMut<crate::plugins::telemetry::PerfTelemetry>>,
    tick: Res<TickCounter>,
    config: Res<SimulationConfig>,
    nav_rules: Res<NavigationRuleSet>,
    terrain: Res<crate::terrain::TerrainGrid>,
    visibility: Res<FactionVisibility>,
    active_zones: Res<crate::config::ActiveZoneModifiers>,
    query: Query<(&Position, &FactionId)>,
    mut registry: ResMut<FlowFieldRegistry>,
) {
    let start = telemetry.as_ref().map(|_| std::time::Instant::now());
    // Skip tick 0 and only run at configured interval
    if tick.tick == 0 || !tick.tick.is_multiple_of(config.flow_field_update_interval) {
        if let (Some(mut t), _) = (telemetry, start) {
            t.flow_field_us = 0; // set to 0 when skipped
        }
        return;
    }

    let cell_size = config.flow_field_cell_size;
    let grid_w = (config.world_width / cell_size).ceil() as usize;
    let grid_h = (config.world_height / cell_size).ceil() as usize;

    // Visibility grid parameters
    let vis_cell_size = visibility.cell_size;
    let vis_w = visibility.grid_width as i32;
    let vis_h = visibility.grid_height as i32;

    // Track which flow field keys we produce this tick, for cleanup
    let mut produced_keys: Vec<u32> = Vec::new();

    // Process each navigation rule independently
    for rule in nav_rules.rules.iter() {
        let follower = rule.follower_faction;

        match &rule.target {
            NavigationTarget::Faction { faction_id } => {
                let target = *faction_id;

                // Gather fog-filtered goal positions for this target faction
                let mut goals: Vec<Vec2> = Vec::new();
                for (pos, faction) in query.iter() {
                    if faction.0 != target {
                        continue;
                    }

                    // Check if this entity is visible to the follower faction
                    let cx = (pos.x / vis_cell_size).floor() as i32;
                    let cy = (pos.y / vis_cell_size).floor() as i32;

                    if cx < 0 || cx >= vis_w || cy < 0 || cy >= vis_h {
                        continue;
                    }
                    let cell_idx = (cy as u32 * visibility.grid_width + cx as u32) as usize;

                    let is_visible = visibility
                        .visible
                        .get(&follower)
                        .is_some_and(|grid| FactionVisibility::get_bit(grid, cell_idx));

                    if is_visible {
                        goals.push(Vec2::new(pos.x, pos.y));
                    }
                }

                if goals.is_empty() {
                    // No visible goals → remove flow field so entities idle
                    registry.fields.remove(&target);
                    continue;
                }

                // Clone terrain costs and apply zone modifier overlays
                let mut cost_map = terrain.hard_costs.clone();
                apply_zone_overlays(
                    &mut cost_map,
                    &active_zones,
                    follower,
                    cell_size,
                    grid_w,
                    grid_h,
                );

                let mut field =
                    crate::pathfinding::FlowField::new(grid_w as u32, grid_h as u32, cell_size);
                field.calculate(&goals, &terrain.hard_obstacles(), Some(&cost_map));
                registry.fields.insert(target, field);
                produced_keys.push(target);
            }

            NavigationTarget::Waypoint { x, y } => {
                // Static waypoint: single goal coordinate, no fog filtering needed.
                // Use the follower faction ID as the flow field key so entities
                // of this faction follow this field.
                let goals = vec![Vec2::new(*x, *y)];

                // Clone terrain costs and apply zone modifier overlays
                let mut cost_map = terrain.hard_costs.clone();
                apply_zone_overlays(
                    &mut cost_map,
                    &active_zones,
                    follower,
                    cell_size,
                    grid_w,
                    grid_h,
                );

                // Register under a waypoint-specific key.
                // We use a synthetic "target" key derived from the follower faction
                // plus a large offset to avoid collision with real faction IDs.
                // However, the movement system uses the flow field keyed by
                // the target faction from NavRules. For waypoint targets, we
                // use a sentinel key: follower_faction + 100000.
                let waypoint_key = follower + 100_000;
                let mut field =
                    crate::pathfinding::FlowField::new(grid_w as u32, grid_h as u32, cell_size);
                field.calculate(&goals, &terrain.hard_obstacles(), Some(&cost_map));
                registry.fields.insert(waypoint_key, field);
                produced_keys.push(waypoint_key);
            }
        }
    }

    // Clean up fields for rules no longer present
    registry.fields.retain(|k, _| produced_keys.contains(k));

    if let (Some(mut t), Some(s)) = (telemetry, start) {
        t.flow_field_us = s.elapsed().as_micros() as u32;
    }
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
#[path = "flow_field_update_tests.rs"]
mod tests;
