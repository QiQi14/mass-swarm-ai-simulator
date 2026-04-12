//! # Movement System (Phase 2)
//!
//! Composite Steering: Macro Flow Field + Micro Boids Separation.
//! Multi-threaded via par_iter_mut() — each entity mutates only its own data.
//!
//! ## Ownership
//! - **Task:** task_06_flow_field_movement_spawning
//! - **Contract:** implementation_plan.md → Contract 7
//!
//! **File Size Rationale:** This module manages all physics and collision responses.
//! The size (480 lines) is due to collision grids, bouncing logic, and inline tests.
//! A single cohesive movement pass prevents coordinate desync bugs.
//!
//! ## Depends On
//! - `crate::components::{Position, Velocity, FactionId, MovementConfig}`
//! - `crate::spatial::SpatialHashGrid`
//! - `crate::pathfinding::FlowFieldRegistry`
//! - `crate::rules::{NavigationRuleSet, FactionBehaviorMode}`
//! - `crate::config::SimulationConfig`

use bevy::prelude::*;

use crate::components::EngineOverride;
use crate::components::EntityId;
use crate::components::{FactionId, MovementConfig, Position, Velocity};
use crate::config::FactionBuffs;
use crate::config::SimulationConfig;
use crate::pathfinding::FlowFieldRegistry;
use crate::rules::{FactionBehaviorMode, NavigationRuleSet};
use crate::spatial::SpatialHashGrid;

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
#[allow(clippy::too_many_arguments)]
#[allow(clippy::type_complexity)]
pub fn movement_system(
    telemetry: Option<ResMut<crate::plugins::telemetry::PerfTelemetry>>,
    grid: Res<SpatialHashGrid>,
    registry: Res<FlowFieldRegistry>,
    nav_rules: Res<NavigationRuleSet>,
    behavior_mode: Res<FactionBehaviorMode>,
    config: Res<SimulationConfig>,
    terrain: Res<crate::terrain::TerrainGrid>,
    faction_buffs: Res<FactionBuffs>,
    buff_config: Res<crate::config::BuffConfig>,
    mut query: Query<
        (
            Entity,
            &mut Position,
            &mut Velocity,
            &FactionId,
            &MovementConfig,
            &EntityId,
            &crate::components::TacticalState,
        ),
        Without<EngineOverride>,
    >,
    tick_res: Res<crate::config::TickCounter>,
) {
    let tick = tick_res.tick;
    let start = telemetry.as_ref().map(|_| std::time::Instant::now());
    let dt = 1.0 / 60.0;

    // PARALLEL ITERATOR: distribute across CPU cores
    query
        .par_iter_mut()
        .for_each(|(entity, mut pos, mut vel, faction, mc, entity_id, tactical)| {
            let current_pos = Vec2::new(pos.x, pos.y);

            // --- 1. MACRO PUSH: Flow Field or Waypoint ---
            let mut macro_dir = Vec2::ZERO;

            // Only sample flow field if faction is NOT in static mode
            if !behavior_mode.static_factions.contains(&faction.0) {
                if let Some(rule) = nav_rules
                    .rules
                    .iter()
                    .find(|r| r.follower_faction == faction.0)
                {
                    match &rule.target {
                        crate::bridges::zmq_protocol::NavigationTarget::Faction { faction_id } => {
                            if let Some(field) = registry.fields.get(faction_id) {
                                macro_dir = field.sample(current_pos);
                            }
                        }
                        crate::bridges::zmq_protocol::NavigationTarget::Waypoint { x, y } => {
                            let waypoint = Vec2::new(*x, *y);
                            let diff = waypoint - current_pos;
                            if diff.length_squared() > 1.0 {
                                macro_dir = diff.normalize();
                            }
                        }
                    }
                }
            }

            // --- 2. MICRO PUSH: Boids Separation (Zero-Allocation) ---
            let mut separation_dir = Vec2::ZERO;

            grid.for_each_in_radius(current_pos, mc.separation_radius, |n_ent, n_pos, _n_faction| {
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

            // --- 3. ENGAGEMENT RANGE HOLD ---
            // If this entity has an engagement range, suppress flow weight when
            // within range of nearest enemy along flow direction. This makes
            // ranged units hold position instead of charging into melee.
            let effective_flow_weight = if tactical.engagement_range > 0.0 {
                // Check if any enemy is within engagement range
                let engage_r = tactical.engagement_range;
                let my_faction = faction.0;
                let mut enemy_in_range = false;
                grid.for_each_in_radius(current_pos, engage_r, |_e, _p, e_faction| {
                    if e_faction != my_faction {
                        enemy_in_range = true;
                    }
                });
                if enemy_in_range {
                    0.0 // Suppress flow — hold position at range
                } else {
                    mc.flow_weight
                }
            } else {
                mc.flow_weight
            };

            // --- 4. BLEND & STEER (3-vector) ---
            // V_desired = (V_flow × W_flow) + (V_sep × W_sep) + (V_tactical × W_tactical)
            let desired = (macro_dir * effective_flow_weight)
                + (separation_dir * mc.separation_weight)
                + (tactical.direction * tactical.weight);
            let desired = desired.normalize_or_zero() * mc.max_speed;

            // Lerp velocity for organic momentum (entities curve, not snap)
            let new_vel = Vec2::new(vel.dx, vel.dy).lerp(desired, mc.steering_factor * dt);

            vel.dx = new_vel.x;
            vel.dy = new_vel.y;

            // --- 5. KINEMATICS, WALL SLIDING & CLAMPING ---
            let world_to_cell = |x: f32, y: f32| -> IVec2 {
                IVec2::new(
                    (x / terrain.cell_size).floor() as i32,
                    (y / terrain.cell_size).floor() as i32,
                )
            };

            let mut next_x = pos.x + vel.dx * dt;
            let mut next_y = pos.y + vel.dy * dt;

            // Check X axis independently — allows sliding along walls
            if terrain.get_hard_cost(world_to_cell(next_x, pos.y)) == u16::MAX {
                vel.dx = 0.0;
                next_x = pos.x; // Blocked on X — entity slides vertically
            }
            // Check Y axis independently
            if terrain.get_hard_cost(world_to_cell(pos.x, next_y)) == u16::MAX {
                vel.dy = 0.0;
                next_y = pos.y; // Blocked on Y — entity slides horizontally
            }

            // Apply soft terrain speed modifier (AFTER wall check, so entity is in a valid cell)
            let cell = world_to_cell(next_x, next_y);
            let soft = terrain.get_soft_cost(cell) as f32 / 100.0;
            let speed_mult = buff_config
                .movement_speed_stat
                .map(|stat_idx| faction_buffs.get_multiplier(faction.0, entity_id.id, stat_idx))
                .unwrap_or(1.0);
            let effective_speed = mc.max_speed * soft * speed_mult;

            let speed_sq = vel.dx * vel.dx + vel.dy * vel.dy;
            if speed_sq > effective_speed * effective_speed {
                let limit_ratio = if speed_sq > 0.0 {
                    effective_speed / speed_sq.sqrt()
                } else {
                    0.0
                };
                vel.dx *= limit_ratio;
                vel.dy *= limit_ratio;
                next_x = pos.x + vel.dx * dt;
                next_y = pos.y + vel.dy * dt;
            }


            pos.x = next_x.clamp(0.0, config.world_width);
            pos.y = next_y.clamp(0.0, config.world_height);
        });
    if let (Some(mut t), Some(s)) = (telemetry, start) {
        t.movement_us = s.elapsed().as_micros() as u32;
    }
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pathfinding::FlowField;

    fn build_test_app() -> App {
        let mut app = App::new();
        app.insert_resource(SpatialHashGrid::new(20.0));
        app.insert_resource(FlowFieldRegistry::default());
        app.insert_resource(NavigationRuleSet { rules: vec![] });
        let mut mode = FactionBehaviorMode {
            static_factions: std::collections::HashSet::new(),
        };
        // Faction 1 static by default
        mode.static_factions.insert(1);
        app.insert_resource(mode);
        app.insert_resource(SimulationConfig::default());
        app.insert_resource(FactionBuffs::default());
        app.init_resource::<crate::config::BuffConfig>();
        app.insert_resource(crate::terrain::TerrainGrid::new(50, 50, 20.0));
        app.insert_resource(crate::config::TickCounter { tick: 0 });
        app.add_systems(Update, movement_system);
        app
    }

    #[test]
    fn test_entity_with_movementconfig_follows_flow_field() {
        let mut app = build_test_app();

        let mut nav = app
            .world_mut()
            .get_resource_mut::<NavigationRuleSet>()
            .unwrap();
        nav.rules.push(crate::rules::NavigationRule {
            follower_faction: 0,
            target: crate::bridges::zmq_protocol::NavigationTarget::Faction { faction_id: 1 },
        });

        let mut reg = app
            .world_mut()
            .get_resource_mut::<FlowFieldRegistry>()
            .unwrap();
        let mut field = FlowField::new(10, 10, 20.0);
        // Force direction to be Vec2::X
        for d in field.directions.iter_mut() {
            *d = Vec2::X;
        }
        reg.fields.insert(1, field);

        let entity = app
            .world_mut()
            .spawn((
                EntityId { id: 1 },
                Position { x: 50.0, y: 50.0 },
                Velocity { dx: 0.0, dy: 0.0 },
                FactionId(0),
                MovementConfig {
                    max_speed: 60.0,
                    steering_factor: 5.0,
                    separation_radius: 6.0,
                    separation_weight: 1.5,
                    flow_weight: 1.0,
                },
                crate::components::TacticalState::default(),
            ))
            .id();

        app.update();

        let vel = app.world().get::<Velocity>(entity).unwrap();
        assert!(vel.dx > 0.0, "Entity should accelerate to the right");
    }

    #[test]
    fn test_static_faction_ignores_flow_field() {
        let mut app = build_test_app();

        let mut nav = app
            .world_mut()
            .get_resource_mut::<NavigationRuleSet>()
            .unwrap();
        nav.rules.push(crate::rules::NavigationRule {
            follower_faction: 1,
            target: crate::bridges::zmq_protocol::NavigationTarget::Faction { faction_id: 0 },
        }); // 1 is static

        let mut reg = app
            .world_mut()
            .get_resource_mut::<FlowFieldRegistry>()
            .unwrap();
        let mut field = FlowField::new(10, 10, 20.0);
        for d in field.directions.iter_mut() {
            *d = Vec2::X;
        }
        reg.fields.insert(0, field);

        let entity = app
            .world_mut()
            .spawn((
                EntityId { id: 1 },
                Position { x: 50.0, y: 50.0 },
                Velocity { dx: 0.0, dy: 0.0 },
                FactionId(1), // static
                MovementConfig {
                    max_speed: 60.0,
                    steering_factor: 5.0,
                    separation_radius: 6.0,
                    separation_weight: 1.5,
                    flow_weight: 1.0,
                },
                crate::components::TacticalState::default(),
            ))
            .id();

        app.update();

        let vel = app.world().get::<Velocity>(entity).unwrap();
        assert_eq!(vel.dx, 0.0, "Static entity should ignore flow field");
    }

    #[test]
    fn test_separation_pushes_entities_apart() {
        let mut app = build_test_app();

        // Two entities perfectly overlapping
        let e1 = app
            .world_mut()
            .spawn((
                EntityId { id: 1 },
                Position { x: 50.0, y: 50.0 },
                Velocity { dx: 0.0, dy: 0.0 },
                FactionId(0),
                MovementConfig {
                    max_speed: 60.0,
                    steering_factor: 5.0,
                    separation_radius: 6.0,
                    separation_weight: 1.5,
                    flow_weight: 1.0,
                },
                crate::components::TacticalState::default(),
            ))
            .id();

        let e2 = app
            .world_mut()
            .spawn((
                EntityId { id: 2 },
                Position { x: 50.0, y: 50.0 },
                Velocity { dx: 0.0, dy: 0.0 },
                FactionId(0),
                MovementConfig {
                    max_speed: 60.0,
                    steering_factor: 5.0,
                    separation_radius: 6.0,
                    separation_weight: 1.5,
                    flow_weight: 1.0,
                },
                crate::components::TacticalState::default(),
            ))
            .id();

        // Hack SpatialHashGrid to contain them so for_each_in_radius finds them
        let pos1 = app.world().get::<Position>(e1).unwrap();
        let p1 = Vec2::new(pos1.x, pos1.y);
        let mut grid = app
            .world_mut()
            .get_resource_mut::<SpatialHashGrid>()
            .unwrap();
        grid.rebuild(&[(e1, p1, 0), (e2, p1, 0)]);

        app.update();

        let v1 = app.world().get::<Velocity>(e1).unwrap();
        let v2 = app.world().get::<Velocity>(e2).unwrap();

        assert!(v1.dx != 0.0 || v1.dy != 0.0, "e1 should be pushed");
        assert!(v2.dx != 0.0 || v2.dy != 0.0, "e2 should be pushed");
    }

    #[test]
    fn test_boundary_clamping() {
        let mut app = build_test_app();

        let entity = app
            .world_mut()
            .spawn((
                EntityId { id: 1 },
                Position { x: 999.0, y: 50.0 },
                Velocity {
                    dx: 1000.0,
                    dy: 0.0,
                }, // Moving very fast right
                FactionId(0),
                MovementConfig {
                    max_speed: 60.0,
                    steering_factor: 5.0,
                    separation_radius: 6.0,
                    separation_weight: 1.5,
                    flow_weight: 1.0,
                },
                crate::components::TacticalState::default(),
            ))
            .id();

        app.update();

        let pos = app.world().get::<Position>(entity).unwrap();
        let config = app.world().get_resource::<SimulationConfig>().unwrap();
        assert!(
            pos.x <= config.world_width,
            "Position should be clamped, got {}",
            pos.x
        );
    }

    #[test]
    fn test_entity_without_movementconfig_excluded() {
        let mut app = build_test_app();

        let entity = app
            .world_mut()
            .spawn((
                EntityId { id: 1 },
                Position { x: 999.0, y: 50.0 },
                Velocity {
                    dx: 1000.0,
                    dy: 0.0,
                },
                FactionId(0),
                // NO MovementConfig
            ))
            .id();

        app.update();

        let pos = app.world().get::<Position>(entity).unwrap();
        assert_eq!(
            pos.x, 999.0,
            "Position should be unchanged because system skips it"
        );
    }

    #[test]
    fn test_wall_sliding_blocks_x_axis() {
        let mut app = build_test_app();

        // Put a wall at cell (3, 2). world positions: x=60-80, y=40-60
        let mut terrain = app
            .world_mut()
            .get_resource_mut::<crate::terrain::TerrainGrid>()
            .unwrap();
        terrain.set_cell(3, 2, u16::MAX, 100);

        let entity = app
            .world_mut()
            .spawn((
                EntityId { id: 1 },
                // Positioned right before the wall on X, moving Right + Down
                Position { x: 59.0, y: 50.0 },
                Velocity {
                    dx: 100.0,
                    dy: 10.0,
                },
                FactionId(0),
                MovementConfig {
                    max_speed: 60.0,
                    steering_factor: 5.0,
                    separation_radius: 6.0,
                    separation_weight: 1.5,
                    flow_weight: 1.0,
                },
                crate::components::TacticalState::default(),
            ))
            .id();

        app.update();

        let vel = app.world().get::<Velocity>(entity).unwrap();
        assert_eq!(vel.dx, 0.0, "Rightward movement should be blocked by wall");
        assert!(
            vel.dy > 0.0,
            "Downward movement should be preserved (slides vertically)"
        );
    }

    #[test]
    fn test_wall_sliding_blocks_y_axis() {
        let mut app = build_test_app();

        // Put a wall at cell (2, 3). world positions: x=40-60, y=60-80
        let mut terrain = app
            .world_mut()
            .get_resource_mut::<crate::terrain::TerrainGrid>()
            .unwrap();
        terrain.set_cell(2, 3, u16::MAX, 100);

        let entity = app
            .world_mut()
            .spawn((
                EntityId { id: 1 },
                // Positioned right above the wall on Y, moving Right + Down
                Position { x: 50.0, y: 59.0 },
                Velocity {
                    dx: 10.0,
                    dy: 100.0,
                },
                FactionId(0),
                MovementConfig {
                    max_speed: 60.0,
                    steering_factor: 5.0,
                    separation_radius: 6.0,
                    separation_weight: 1.5,
                    flow_weight: 1.0,
                },
                crate::components::TacticalState::default(),
            ))
            .id();

        app.update();

        let vel = app.world().get::<Velocity>(entity).unwrap();
        assert_eq!(vel.dy, 0.0, "Downward movement should be blocked by wall");
        assert!(
            vel.dx > 0.0,
            "Rightward movement should be preserved (slides horizontally)"
        );
    }

    #[test]
    fn test_soft_cost_reduces_speed() {
        let mut app = build_test_app();

        // Put mud at cell (2, 2) which reduces speed to 50%
        let mut terrain = app
            .world_mut()
            .get_resource_mut::<crate::terrain::TerrainGrid>()
            .unwrap();
        terrain.set_cell(2, 2, 100, 50); // 50 = half speed

        let mut mc = MovementConfig {
            max_speed: 60.0,
            steering_factor: 5.0,
            separation_radius: 6.0,
            separation_weight: 1.5,
            flow_weight: 1.0,
        };
        mc.max_speed = 100.0;

        let entity = app
            .world_mut()
            .spawn((
                EntityId { id: 1 },
                Position { x: 50.0, y: 50.0 },
                Velocity { dx: 200.0, dy: 0.0 }, // Try to move faster than max speed
                FactionId(0),
                mc,
                crate::components::TacticalState::default(),
            ))
            .id();

        app.update();

        let vel = app.world().get::<Velocity>(entity).unwrap();
        let speed = (vel.dx * vel.dx + vel.dy * vel.dy).sqrt();
        assert!(
            (speed - 50.0).abs() < 1.0,
            "Entity in mud should have speed capped to 50, got {}",
            speed
        );
    }
}
