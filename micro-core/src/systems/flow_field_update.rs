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

/// Recalculates flow fields for navigating factions.
/// Runs every `config.flow_field_update_interval` ticks (~2 TPS at interval=30).
pub fn flow_field_update_system(
    telemetry: Option<ResMut<crate::plugins::telemetry::PerfTelemetry>>,
    tick: Res<TickCounter>,
    config: Res<SimulationConfig>,
    nav_rules: Res<NavigationRuleSet>,
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

    // Deduplicate target factions from nav rules
    let target_factions: Vec<u32> = {
        let mut targets: Vec<u32> = nav_rules.rules.iter()
            .map(|r| r.target_faction)
            .collect();
        targets.sort_unstable();
        targets.dedup();
        targets
    };

    // Gather goal positions per target faction (O(N) pass)
    let mut faction_goals: HashMap<u32, Vec<Vec2>> = HashMap::default();
    for (pos, faction) in query.iter() {
        if target_factions.contains(&faction.0) {
            faction_goals.entry(faction.0)
                .or_default()
                .push(Vec2::new(pos.x, pos.y));
        }
    }

    // Calculate flow fields using Task 03 algorithm
    let cell_size = config.flow_field_cell_size;
    let grid_w = (config.world_width / cell_size).ceil() as usize;  // cell_size from Task 02
    let grid_h = (config.world_height / cell_size).ceil() as usize;

    for &target in &target_factions {
        if let Some(goals) = faction_goals.get(&target) {
            if goals.is_empty() { continue; }

            let mut field = crate::pathfinding::FlowField::new(grid_w as u32, grid_h as u32, cell_size);
            field.calculate(goals, &[]); // No obstacles in Phase 2
            registry.fields.insert(target, field);
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
        app.add_systems(Update, flow_field_update_system);
        app
    }

    #[test]
    fn test_flow_field_update_runs_at_interval() {
        let mut app = build_app();
        
        let mut nav = app.world_mut().get_resource_mut::<NavigationRuleSet>().unwrap();
        nav.rules.push(NavigationRule { follower_faction: 0, target_faction: 1 });

        app.world_mut().spawn((Position { x: 50.0, y: 50.0 }, FactionId(1)));

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
}
