---
Task_ID: task_06_flow_field_movement_spawning
Execution_Phase: Phase 2 (Parallel)
Model_Tier: standard
Target_Files:
  - micro-core/src/components/flow_field_follower.rs
  - micro-core/src/components/mod.rs
  - micro-core/src/systems/movement.rs
  - micro-core/src/systems/flow_field_update.rs
  - micro-core/src/systems/spawning.rs
Dependencies:
  - task_02_spatial_hash_grid
  - task_03_flow_field_registry
  - task_04_rule_resources
Context_Bindings:
  - context/conventions
  - context/architecture
  - skills/rust-code-standards
---

# STRICT INSTRUCTIONS

Create the FlowFieldFollower component, the flow field update system, modify the movement system for flow field integration, and add wave spawning.

**Read `implementation_plan.md` Contracts 4, 5, 7, 9, and 10.**

**DO NOT modify `systems/mod.rs` — Task 08 handles wiring.**

## 1. Create `micro-core/src/components/flow_field_follower.rs` [NEW]

```rust
use bevy::prelude::*;

/// Marker component. Entities with this opt into flow field navigation.
/// The movement system reads NavigationRuleSet to determine which flow field to follow.
#[derive(Component, Debug, Clone, Default)]
pub struct FlowFieldFollower;
```

Unit test: can be instantiated with `FlowFieldFollower::default()`.

## 2. Update `micro-core/src/components/mod.rs` [MODIFY]

Add `pub mod flow_field_follower;` and `pub use flow_field_follower::FlowFieldFollower;`.

## 3. Create `micro-core/src/systems/flow_field_update.rs` [NEW]

```rust
pub fn flow_field_update_system(
    mut registry: ResMut<FlowFieldRegistry>,
    nav_rules: Res<NavigationRuleSet>,
    query: Query<(&Position, &FactionId)>,
    config: Res<SimulationConfig>,
    tick: Res<TickCounter>,
)
```

Algorithm:
1. Only run every `config.flow_field_update_interval` ticks (check `tick.tick % interval == 0`). Skip tick 0.
2. Collect unique target faction IDs from `nav_rules.rules` (deduplicate).
3. For each unique target faction:
   - Gather all entity positions where `faction_id.0 == target_faction` → `Vec<Vec2>`.
   - If no entities found for this faction, skip (don't create empty field).
   - Create or reuse a `FlowField::new(width, height, config.flow_field_cell_size)` where width/height are derived from `config.world_width / config.flow_field_cell_size`.
   - Call `field.calculate(&goals, &[])` (no obstacles yet).
   - Insert into `registry.fields`.
4. Remove registry entries for faction IDs that are no longer targets in `nav_rules`.

## 4. Modify `micro-core/src/systems/movement.rs` [MODIFY]

Update `movement_system` signature to add:
- `registry: Res<FlowFieldRegistry>`
- `nav_rules: Res<NavigationRuleSet>`
- `behavior_mode: Res<FactionBehaviorMode>`
- `&FactionId` and `Option<&FlowFieldFollower>` to the entity query.

**Movement logic per entity:**
1. If entity HAS `FlowFieldFollower` AND faction is NOT in `behavior_mode.static_factions`:
   - Look up entity's `FactionId` in `nav_rules.rules` to find its `target_faction`.
   - Look up `target_faction` in `registry.fields`.
   - If a field exists: `let dir = field.sample(Vec2::new(pos.x, pos.y))`. If `dir != Vec2::ZERO`, override velocity: `vel.dx = dir.x * speed; vel.dy = dir.y * speed` where `speed = (vel.dx*vel.dx + vel.dy*vel.dy).sqrt()` (preserve original speed magnitude). If speed is 0, use a default speed of 1.0.
   - If no matching rule or field, keep current velocity unchanged.
2. If entity does NOT have `FlowFieldFollower` OR faction IS in `static_factions`: keep existing velocity unchanged (random drift from spawn).

**Boundary handling:** Replace any wrap-around logic with clamping:
```rust
pos.x = pos.x.clamp(0.0, config.world_width);
pos.y = pos.y.clamp(0.0, config.world_height);
```

## 5. Modify `micro-core/src/systems/spawning.rs` [MODIFY]

Add `wave_spawn_system`:

```rust
pub fn wave_spawn_system(
    tick: Res<TickCounter>,
    config: Res<SimulationConfig>,
    mut commands: Commands,
    mut next_id: ResMut<NextEntityId>,
)
```

Algorithm:
1. Only run every `config.wave_spawn_interval` ticks. Skip tick 0.
2. For each of `config.wave_spawn_count` entities:
   - Pick a random edge position: randomly select one of 4 edges, then random position along that edge.
   - Spawn with: `EntityId`, `Position`, `Velocity` (random direction, magnitude 1.0), `FactionId(config.wave_spawn_faction)`, `StatBlock::with_defaults(&config.wave_spawn_stat_defaults)`, `FlowFieldFollower`.
   - Increment `next_id.0`.

Also update `initial_spawn_system` to add `FlowFieldFollower` to faction 0 entities (those that match `wave_spawn_faction`).

## 6. Unit Tests

- **FlowFieldFollower entity moves toward goal:** Entity at (0,0) with FlowFieldFollower, flow field pointing right → velocity becomes (speed, 0).
- **Static faction ignores flow field:** Entity with FlowFieldFollower but faction in `static_factions` → velocity unchanged.
- **No matching rule:** Entity with FlowFieldFollower but no matching navigation rule → velocity unchanged.
- **No FlowFieldFollower:** Entity without marker → velocity unchanged, uses existing drift.
- **Boundary clamping:** Entity at world edge with velocity pointing outward → position clamps to boundary.
- **Wave spawn count:** After `wave_spawn_interval` ticks, exactly `wave_spawn_count` entities spawned.
- **Wave spawn edge position:** Spawned entities have position on a world edge (x=0 or x=world_width or y=0 or y=world_height).
- **Flow field update deduplication:** Two nav rules targeting same faction → only one flow field calculated.

---

# Verification_Strategy
Test_Type: unit
Test_Stack: cargo test
Acceptance_Criteria:
  - "FlowFieldFollower entities navigate toward correct target per NavigationRuleSet"
  - "Entities in static_factions use random drift even with FlowFieldFollower"
  - "Non-follower entities retain original velocity"
  - "Position clamps to world boundaries (no wrapping)"
  - "wave_spawn_system spawns correct count every N ticks"
  - "Multiple factions targeting same faction share one flow field calculation"
Suggested_Test_Commands:
  - "cd micro-core && cargo test movement"
  - "cd micro-core && cargo test spawning"
  - "cd micro-core && cargo test flow_field_update"
