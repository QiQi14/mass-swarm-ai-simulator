# Changelog for Task 11 (Terrain Flow Movement)

## Touched Files
- `micro-core/src/pathfinding/flow_field.rs`
- `micro-core/src/systems/flow_field_update.rs`
- `micro-core/src/systems/movement.rs`

## Contract Fulfillment
- Modified `FlowField::calculate` signature to take `cost_map: Option<&[u16]>`. Implemented inverted integer cost logic `(move_cost * hard_cost) / 100` and skipped BFS queue on `u16::MAX`.
- Modified `flow_field_update_system` to include `terrain: Res<TerrainGrid>` and pass `terrain.hard_obstacles()` and `Some(&terrain.hard_costs)` to `calculate`.
- Modified `movement_system` to include `terrain: Res<TerrainGrid>`. Implemented kinematic wall-sliding on X and Y axes independently, zeroing velocities and preventing overlap on `u16::MAX` boundaries. Applied `soft_cost` speed modifiers as velocity caps (`vel *= limit_ratio`) ensuring entities safely slow down over mud and pushable terrain without paralysis.

## Deviations/Notes
- Velocity cap limit is used for `soft_cost` reduction, taking the vector components smoothly. If current speed exceeds `effective_speed`, it is cleanly scaled rather than directly substituting the exact requested `desired` speed magnitude, guaranteeing stability across physics ticks.

## Human Interventions
- None.
