//! # Movement System (Phase 2)
//!
//! Composite Steering: Macro Flow Field + Micro Boids Separation.
//! Multi-threaded via par_iter_mut() — each entity mutates only its own data.
//!
//! ## Ownership
//! - **Task:** task_06_flow_field_movement_spawning
//! - **Contract:** implementation_plan.md → Contract 7
//!
//! ## Depends On
//! - `crate::components::{Position, Velocity, FactionId, MovementConfig}`
//! - `crate::spatial::SpatialHashGrid`
//! - `crate::pathfinding::FlowFieldRegistry`
//! - `crate::rules::{NavigationRuleSet, FactionBehaviorMode}`
//! - `crate::config::SimulationConfig`

use bevy::prelude::*;
use bevy::platform::collections::HashMap;
use crate::components::{Position, Velocity, FactionId, MovementConfig};
use crate::spatial::SpatialHashGrid;
use crate::pathfinding::FlowFieldRegistry;
use crate::rules::{NavigationRuleSet, FactionBehaviorMode};
use crate::config::SimulationConfig;

/// Multi-threaded movement with Composite Steering.
///
/// ## Algorithm per entity
/// 1. **Macro Pull** — Sample flow field for entity's faction → direction vector.
/// 2. **Micro Push** — Query SpatialHashGrid for separation neighbors → push-back.
/// 3. **Blend & Steer** — Weighted sum → lerp velocity for organic momentum.
/// 4. **Kinematics** — Apply velocity × dt. Clamp to world boundaries.
///
/// ## Threading
/// Safe to `par_iter_mut()` because each entity mutates ONLY its own
/// `Position` and `Velocity`. Grid/Registry reads are purely immutable.
///
/// ## Entities WITHOUT MovementConfig
/// Entities without `MovementConfig` are NOT processed by this system.
/// They retain Phase 1 behavior (random drift) via the simple movement
/// system in the legacy path. The integration task (T08) should handle
/// which movement system runs for which entities.
#[allow(clippy::collapsible_if)]
pub fn movement_system(
    telemetry: Option<ResMut<crate::plugins::telemetry::PerfTelemetry>>,
    grid: Res<SpatialHashGrid>,
    registry: Res<FlowFieldRegistry>,
    nav_rules: Res<NavigationRuleSet>,
    behavior_mode: Res<FactionBehaviorMode>,
    config: Res<SimulationConfig>,
    mut query: Query<(Entity, &mut Position, &mut Velocity, &FactionId, &MovementConfig)>,
) {
    let start = telemetry.as_ref().map(|_| std::time::Instant::now());
    let dt = 1.0 / 60.0;

    // Cache follower→target mapping (small allocation, rules count is tiny)
    let follow_map: HashMap<u32, u32> = nav_rules.rules.iter()
        .map(|r| (r.follower_faction, r.target_faction))
        .collect();

    // PARALLEL ITERATOR: distribute across CPU cores
    query.par_iter_mut().for_each(|(entity, mut pos, mut vel, faction, mc)| {
        let current_pos = Vec2::new(pos.x, pos.y);

        // --- 1. MACRO PUSH: Flow Field ---
        let mut macro_dir = Vec2::ZERO;

        // Only sample flow field if faction is NOT in static mode
        if !behavior_mode.static_factions.contains(&faction.0) {
            if let Some(&target_faction) = follow_map.get(&faction.0) {
                if let Some(field) = registry.fields.get(&target_faction) {
                    macro_dir = field.sample(current_pos);
                }
            }
        }

        // --- 2. MICRO PUSH: Boids Separation (Zero-Allocation) ---
        let mut separation_dir = Vec2::ZERO;

        grid.for_each_in_radius(current_pos, mc.separation_radius, |n_ent, n_pos| {
            if n_ent != entity {
                let diff = current_pos - n_pos;
                let dist_sq = diff.length_squared();

                if dist_sq > 0.0001 {
                    // Inverse-linear repulsion: diff / |diff|² = direction / distance
                    // Pushes hard when close, softly when far. Zero sqrt().
                    separation_dir += diff / dist_sq;
                } else {
                    // Break perfect overlaps with deterministic spread
                    // Use entity index bits for pseudo-random direction
                    let bits = entity.to_bits();
                    let angle = (bits % 360) as f32 * std::f32::consts::TAU / 360.0;
                    separation_dir += Vec2::new(angle.cos(), angle.sin()) * 0.1;
                }
            }
        });

        // --- 3. BLEND & STEER ---
        let desired = (macro_dir * mc.flow_weight)
                    + (separation_dir * mc.separation_weight);
        let desired = desired.normalize_or_zero() * mc.max_speed;

        // Lerp velocity for organic momentum (entities curve, not snap)
        let new_vel = Vec2::new(vel.dx, vel.dy).lerp(desired, mc.steering_factor * dt);

        vel.dx = new_vel.x;
        vel.dy = new_vel.y;

        // --- 4. KINEMATICS & CLAMPING ---
        pos.x = (pos.x + vel.dx * dt).clamp(0.0, config.world_width);
        pos.y = (pos.y + vel.dy * dt).clamp(0.0, config.world_height);
    });
    if let (Some(mut t), Some(s)) = (telemetry, start) {
        t.movement_us = s.elapsed().as_micros() as u32;
    }
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rules::NavigationRule;
    use crate::pathfinding::FlowField;

    fn build_test_app() -> App {
        let mut app = App::new();
        app.insert_resource(SpatialHashGrid::new(20.0));
        app.insert_resource(FlowFieldRegistry::default());
        app.insert_resource(NavigationRuleSet { rules: vec![] });
        let mut mode = FactionBehaviorMode { static_factions: std::collections::HashSet::new() };
        // Faction 1 static by default
        mode.static_factions.insert(1);
        app.insert_resource(mode);
        app.insert_resource(SimulationConfig::default());
        app.add_systems(Update, movement_system);
        app
    }

    #[test]
    fn test_entity_with_movementconfig_follows_flow_field() {
        let mut app = build_test_app();
        
        let mut nav = app.world_mut().get_resource_mut::<NavigationRuleSet>().unwrap();
        nav.rules.push(NavigationRule { follower_faction: 0, target_faction: 1 });
        
        let mut reg = app.world_mut().get_resource_mut::<FlowFieldRegistry>().unwrap();
        let mut field = FlowField::new(10, 10, 20.0);
        // Force direction to be Vec2::X
        for d in field.directions.iter_mut() { *d = Vec2::X; }
        reg.fields.insert(1, field);

        let entity = app.world_mut().spawn((
            Position { x: 50.0, y: 50.0 },
            Velocity { dx: 0.0, dy: 0.0 },
            FactionId(0),
            MovementConfig::default(),
        )).id();

        app.update();

        let vel = app.world().get::<Velocity>(entity).unwrap();
        assert!(vel.dx > 0.0, "Entity should accelerate to the right");
    }

    #[test]
    fn test_static_faction_ignores_flow_field() {
        let mut app = build_test_app();
        
        let mut nav = app.world_mut().get_resource_mut::<NavigationRuleSet>().unwrap();
        nav.rules.push(NavigationRule { follower_faction: 1, target_faction: 0 }); // 1 is static
        
        let mut reg = app.world_mut().get_resource_mut::<FlowFieldRegistry>().unwrap();
        let mut field = FlowField::new(10, 10, 20.0);
        for d in field.directions.iter_mut() { *d = Vec2::X; }
        reg.fields.insert(0, field);

        let entity = app.world_mut().spawn((
            Position { x: 50.0, y: 50.0 },
            Velocity { dx: 0.0, dy: 0.0 },
            FactionId(1), // static
            MovementConfig::default(),
        )).id();

        app.update();

        let vel = app.world().get::<Velocity>(entity).unwrap();
        assert_eq!(vel.dx, 0.0, "Static entity should ignore flow field");
    }

    #[test]
    fn test_separation_pushes_entities_apart() {
        let mut app = build_test_app();
        
        // Two entities perfectly overlapping
        let e1 = app.world_mut().spawn((
            Position { x: 50.0, y: 50.0 },
            Velocity { dx: 0.0, dy: 0.0 },
            FactionId(0),
            MovementConfig::default(),
        )).id();
        
        let e2 = app.world_mut().spawn((
            Position { x: 50.0, y: 50.0 },
            Velocity { dx: 0.0, dy: 0.0 },
            FactionId(0),
            MovementConfig::default(),
        )).id();

        // Hack SpatialHashGrid to contain them so for_each_in_radius finds them
        let pos1 = app.world().get::<Position>(e1).unwrap();
        let p1 = Vec2::new(pos1.x, pos1.y);
        let mut grid = app.world_mut().get_resource_mut::<SpatialHashGrid>().unwrap();
        grid.rebuild(&[(e1, p1), (e2, p1)]);

        app.update();

        let v1 = app.world().get::<Velocity>(e1).unwrap();
        let v2 = app.world().get::<Velocity>(e2).unwrap();
        
        assert!(v1.dx != 0.0 || v1.dy != 0.0, "e1 should be pushed");
        assert!(v2.dx != 0.0 || v2.dy != 0.0, "e2 should be pushed");
    }

    #[test]
    fn test_boundary_clamping() {
        let mut app = build_test_app();
        
        let entity = app.world_mut().spawn((
            Position { x: 999.0, y: 50.0 },
            Velocity { dx: 1000.0, dy: 0.0 }, // Moving very fast right
            FactionId(0),
            MovementConfig::default(),
        )).id();

        app.update();

        let pos = app.world().get::<Position>(entity).unwrap();
        let config = app.world().get_resource::<SimulationConfig>().unwrap();
        assert!(pos.x <= config.world_width, "Position should be clamped, got {}", pos.x);
    }

    #[test]
    fn test_entity_without_movementconfig_excluded() {
        let mut app = build_test_app();
        
        let entity = app.world_mut().spawn((
            Position { x: 999.0, y: 50.0 },
            Velocity { dx: 1000.0, dy: 0.0 },
            FactionId(0),
            // NO MovementConfig
        )).id();

        app.update();

        let pos = app.world().get::<Position>(entity).unwrap();
        assert_eq!(pos.x, 999.0, "Position should be unchanged because system skips it");
    }
}
