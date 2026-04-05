//! # Flow Field Update System
//!
//! Recalculates flow fields at ~2 TPS (every N ticks).
//! Decoupled from the 60 TPS physics loop.
//!
//! ## Ownership
//! - **Task:** task_06_flow_field_movement_spawning
//! - **Contract:** implementation_plan.md → Contract 7

use bevy::prelude::*;
use bevy::platform::collections::HashMap;
use crate::components::{Position, FactionId};
use crate::config::{SimulationConfig, TickCounter};
use crate::pathfinding::FlowFieldRegistry;
use crate::rules::NavigationRuleSet;
use crate::visibility::FactionVisibility;

/// Recalculates flow fields for navigating factions.
/// Runs every `config.flow_field_update_interval` ticks (~2 TPS at interval=30).
///
/// **Fog-of-War aware:** Only enemy positions visible to the follower faction
/// are used as flow field goals. If no enemies are visible, the flow field
/// is removed and entities idle until new targets enter their vision.
pub fn flow_field_update_system(
    telemetry: Option<ResMut<crate::plugins::telemetry::PerfTelemetry>>,
    tick: Res<TickCounter>,
    config: Res<SimulationConfig>,
    nav_rules: Res<NavigationRuleSet>,
    terrain: Res<crate::terrain::TerrainGrid>,
    visibility: Res<FactionVisibility>,
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

    // Build follower→target mapping from nav rules
    // Also collect unique target factions
    let follower_to_target: Vec<(u32, u32)> = nav_rules.rules.iter()
        .map(|r| (r.follower_faction, r.target_faction))
        .collect();

    let target_factions: Vec<u32> = {
        let mut targets: Vec<u32> = follower_to_target.iter().map(|&(_, t)| t).collect();
        targets.sort_unstable();
        targets.dedup();
        targets
    };

    // For each target faction, gather goals ONLY from cells visible
    // to at least one follower faction that targets it.
    //
    // Example: faction 0 targets faction 1 → only use faction 1 entities
    // that are in faction 0's visible cells.
    let vis_cell_size = visibility.cell_size;
    let vis_w = visibility.grid_width as i32;
    let vis_h = visibility.grid_height as i32;

    // Collect which follower factions target each target faction
    let mut followers_by_target: HashMap<u32, Vec<u32>> = HashMap::default();
    for &(follower, target) in &follower_to_target {
        followers_by_target.entry(target).or_default().push(follower);
    }

    // Gather fog-filtered goal positions per target faction
    let mut faction_goals: HashMap<u32, Vec<Vec2>> = HashMap::default();
    for (pos, faction) in query.iter() {
        if !target_factions.contains(&faction.0) {
            continue;
        }

        // Check if this entity is visible to ANY follower faction
        let cx = (pos.x / vis_cell_size).floor() as i32;
        let cy = (pos.y / vis_cell_size).floor() as i32;

        if cx < 0 || cx >= vis_w || cy < 0 || cy >= vis_h {
            continue; // out of grid bounds
        }
        let cell_idx = (cy as u32 * visibility.grid_width + cx as u32) as usize;

        if let Some(followers) = followers_by_target.get(&faction.0) {
            let is_visible = followers.iter().any(|follower_fid| {
                visibility.visible.get(follower_fid)
                    .map_or(false, |grid| FactionVisibility::get_bit(grid, cell_idx))
            });

            if is_visible {
                faction_goals.entry(faction.0)
                    .or_default()
                    .push(Vec2::new(pos.x, pos.y));
            }
        }
    }

    // Calculate flow fields using Task 03 algorithm
    let cell_size = config.flow_field_cell_size;
    let grid_w = (config.world_width / cell_size).ceil() as usize;
    let grid_h = (config.world_height / cell_size).ceil() as usize;

    for &target in &target_factions {
        if let Some(goals) = faction_goals.get(&target) {
            if goals.is_empty() { continue; }

            let mut field = crate::pathfinding::FlowField::new(grid_w as u32, grid_h as u32, cell_size);
            field.calculate(goals, &terrain.hard_obstacles(), Some(&terrain.hard_costs));
            registry.fields.insert(target, field);
        } else {
            // No visible goals → remove flow field so entities idle
            registry.fields.remove(&target);
        }
    }

    // Clean up fields for factions no longer targeted
    registry.fields.retain(|k, _| target_factions.contains(k));
    
    if let (Some(mut t), Some(s)) = (telemetry, start) {
        t.flow_field_us = s.elapsed().as_micros() as u32;
    }
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rules::NavigationRule;

    fn build_app() -> App {
        let mut app = App::new();
        app.insert_resource(TickCounter::default());
        app.insert_resource(SimulationConfig::default());
        app.insert_resource(NavigationRuleSet { rules: vec![] });
        app.insert_resource(FlowFieldRegistry::default());
        app.insert_resource(crate::terrain::TerrainGrid::new(50, 50, 20.0));
        app.insert_resource(FactionVisibility::new(50, 50, 20.0));
        app.add_systems(Update, flow_field_update_system);
        app
    }

    /// Helper: mark a world position as visible for a faction
    fn mark_visible(app: &mut App, faction: u32, world_x: f32, world_y: f32) {
        let mut vis = app.world_mut().get_resource_mut::<FactionVisibility>().unwrap();
        vis.ensure_faction(faction);
        let cx = (world_x / vis.cell_size).floor() as u32;
        let cy = (world_y / vis.cell_size).floor() as u32;
        let idx = (cy * vis.grid_width + cx) as usize;
        FactionVisibility::set_bit(vis.visible.get_mut(&faction).unwrap(), idx);
    }

    #[test]
    fn test_flow_field_update_runs_at_interval() {
        let mut app = build_app();
        
        let mut nav = app.world_mut().get_resource_mut::<NavigationRuleSet>().unwrap();
        nav.rules.push(NavigationRule { follower_faction: 0, target_faction: 1 });

        app.world_mut().spawn((Position { x: 50.0, y: 50.0 }, FactionId(1)));
        // Mark target position as visible to follower faction 0
        mark_visible(&mut app, 0, 50.0, 50.0);

        // Tick 1 -> no update
        app.world_mut().get_resource_mut::<TickCounter>().unwrap().tick = 1;
        app.update();
        assert!(app.world().get_resource::<FlowFieldRegistry>().unwrap().fields.is_empty());

        // Tick 30 -> update
        app.world_mut().get_resource_mut::<TickCounter>().unwrap().tick = 30;
        app.update();
        assert!(app.world().get_resource::<FlowFieldRegistry>().unwrap().fields.contains_key(&1));
    }

    #[test]
    fn test_deduplicates_target_factions() {
        let mut app = build_app();
        
        let mut nav = app.world_mut().get_resource_mut::<NavigationRuleSet>().unwrap();
        nav.rules.push(NavigationRule { follower_faction: 0, target_faction: 1 });
        nav.rules.push(NavigationRule { follower_faction: 2, target_faction: 1 }); // duplicate target

        app.world_mut().spawn((Position { x: 50.0, y: 50.0 }, FactionId(1)));
        // Mark visible for both follower factions
        mark_visible(&mut app, 0, 50.0, 50.0);
        mark_visible(&mut app, 2, 50.0, 50.0);

        app.world_mut().get_resource_mut::<TickCounter>().unwrap().tick = 30;
        app.update();
        
        let reg = app.world().get_resource::<FlowFieldRegistry>().unwrap();
        assert_eq!(reg.fields.len(), 1, "Should only calculate one field for faction 1");
    }

    #[test]
    fn test_cleans_up_stale_fields() {
        let mut app = build_app();
        
        // Setup initial stale field
        let mut reg = app.world_mut().get_resource_mut::<FlowFieldRegistry>().unwrap();
        reg.fields.insert(99, crate::pathfinding::FlowField::new(10, 10, 20.0));

        // Nav rules don't target 99
        app.world_mut().get_resource_mut::<TickCounter>().unwrap().tick = 30;
        app.update();
        
        let reg = app.world().get_resource::<FlowFieldRegistry>().unwrap();
        assert!(!reg.fields.contains_key(&99), "Stale field should be removed");
    }

    #[test]
    fn test_flow_field_update_uses_terrain() {
        let mut app = build_app();
        
        let mut nav = app.world_mut().get_resource_mut::<NavigationRuleSet>().unwrap();
        nav.rules.push(NavigationRule { follower_faction: 0, target_faction: 1 });

        app.world_mut().spawn((Position { x: 50.0, y: 50.0 }, FactionId(1)));
        mark_visible(&mut app, 0, 50.0, 50.0);

        // Add a wall directly between a point and the goal
        let mut terrain = app.world_mut().get_resource_mut::<crate::terrain::TerrainGrid>().unwrap();
        terrain.set_cell(2, 2, u16::MAX, 0);

        app.world_mut().get_resource_mut::<TickCounter>().unwrap().tick = 30;
        app.update();
        
        let reg = app.world().get_resource::<FlowFieldRegistry>().unwrap();
        let field = reg.fields.get(&1).unwrap();
        
        // Check that the wall cell is considered an obstacle with MAX cost
        let wall_idx = (2 * field.width + 2) as usize;
        assert_eq!(field.costs[wall_idx], u16::MAX, "Wall cell should have MAX cost in updated flow field");
    }

    #[test]
    fn test_fog_of_war_filters_invisible_targets() {
        let mut app = build_app();
        
        let mut nav = app.world_mut().get_resource_mut::<NavigationRuleSet>().unwrap();
        nav.rules.push(NavigationRule { follower_faction: 0, target_faction: 1 });

        // Target exists but is NOT in faction 0's visible cells
        app.world_mut().spawn((Position { x: 500.0, y: 500.0 }, FactionId(1)));
        // Don't mark visible — target should be invisible

        app.world_mut().get_resource_mut::<TickCounter>().unwrap().tick = 30;
        app.update();
        
        let reg = app.world().get_resource::<FlowFieldRegistry>().unwrap();
        assert!(!reg.fields.contains_key(&1), 
            "Flow field should NOT exist for invisible targets");
    }
}
