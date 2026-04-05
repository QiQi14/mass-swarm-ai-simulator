---
Task_ID: task_06_flow_field_movement_spawning
Execution_Phase: Phase 2 (Parallel)
Model_Tier: standard
Target_Files:
  - micro-core/src/components/movement_config.rs
  - micro-core/src/components/mod.rs
  - micro-core/src/config.rs
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

Implement Composite Steering (Macro Flow Field + Micro Boids Separation), flow field updater, and wave spawning.

**Read `implementation_plan.md` Contracts 4, 5, 7, 9, 10 AND the deep-dive spec `implementation_plan_task_06.md` for the full architecture, math, code, and unit tests.**

> **CRITICAL:** The spec file `implementation_plan_task_06.md` (project root) contains the Composite Steering algorithm, Zero-Sqrt separation math, par_iter_mut parallelism design, and all corrections applied to the human-provided code. Adopt the architecture and verify correctness before implementation.

**DO NOT modify `systems/mod.rs` — Task 08 handles wiring.**

## Architecture

### Composite Steering (Macro + Micro)
- **Macro Pull:** Sample FlowFieldRegistry for the entity's faction → direction vector.
- **Micro Push:** Query SpatialHashGrid via `for_each_in_radius` for Boids separation → push-back.
- **Blend:** `desired = (flow_dir × flow_weight) + (separation × separation_weight)`
- **Steer:** `velocity = lerp(current_vel, desired, steering_factor × dt)`

### Zero-Sqrt Separation
`diff / dist_sq` gives inverse-linear repulsion (magnitude = 1/distance). Zero `sqrt()` calls.

### Multi-threaded via `par_iter_mut()`
Safe because each entity mutates ONLY its own Position and Velocity. Grid + Registry reads are immutable.

### Zero-Allocation: `for_each_in_radius`
Use closure-based spatial query (Task 02 API), NOT `query_radius()`. Avoids 600K heap allocs/sec.

## Mandatory Design Decisions

1. **Keep existing `Velocity { dx, dy }`** — Do NOT change to `Velocity(Vec2)`. Breaks WS serialization.
2. **Fixed delta `1.0 / 60.0`** — NOT `Res<Time>`. ML determinism.
3. **Position clamping** — NOT toroidal wrapping.
4. **Use `tick.tick`** — NOT `tick.0`. TickCounter has named field.
5. **Use `config.world_width`** — NOT hardcoded `1000.0`.

## File Structure

### 1. `micro-core/src/components/movement_config.rs` [NEW]
`MovementConfig` component with: max_speed, steering_factor, separation_radius, separation_weight, flow_weight. Default impl. Replaces the old `FlowFieldFollower` marker.

### 2. `micro-core/src/components/mod.rs` [MODIFY]
Add `pub mod movement_config;` and `pub use movement_config::MovementConfig;`.

### 3. `micro-core/src/config.rs` [MODIFY]
Add to SimulationConfig: `flow_field_update_interval: u64`, `wave_spawn_interval: u64`, `wave_spawn_count: u32`, `wave_spawn_faction: u32`, `wave_spawn_stat_defaults: Vec<(usize, f32)>`.

### 4. `micro-core/src/systems/movement.rs` [MODIFY — FULL REWRITE]
Multi-threaded movement system with Composite Steering. See spec §5.4 for complete code.

### 5. `micro-core/src/systems/flow_field_update.rs` [NEW]
Recalculates flow fields at ~2 TPS. See spec §5.5.

### 6. `micro-core/src/systems/spawning.rs` [MODIFY]
Add `wave_spawn_system`. Update `initial_spawn_system` to add `MovementConfig` to faction 0 entities.

## Unit Tests (11 tests)

### Movement:
- Entity with MovementConfig follows flow field direction
- Static faction ignores flow field
- Separation pushes overlapping entities apart
- Boundary clamping works
- Entity without MovementConfig excluded

### Flow Field Update:
- Runs at configured interval only
- Deduplicates target factions
- Cleans up stale fields

### Spawning:
- Wave spawn creates correct count at interval
- Spawned entities have MovementConfig
- Skip tick 0

---

# Verification_Strategy
Test_Type: unit
Test_Stack: cargo test
Acceptance_Criteria:
  - "MovementConfig entities navigate toward flow field targets"
  - "Separation prevents entity stacking (Zero-Sqrt)"
  - "Static factions use random drift"
  - "Position clamps to world boundaries"
  - "par_iter_mut used for multi-threaded update"
  - "for_each_in_radius used (NOT query_radius) in movement"
  - "Flow field updates at config interval, not every tick"
  - "Wave spawn creates correct count"
  - "Uses existing Velocity { dx, dy } struct"
Suggested_Test_Commands:
  - "cd micro-core && cargo test movement"
  - "cd micro-core && cargo test spawning"
  - "cd micro-core && cargo test flow_field_update"
