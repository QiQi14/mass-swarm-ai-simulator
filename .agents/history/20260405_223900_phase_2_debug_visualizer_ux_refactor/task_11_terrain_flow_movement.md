# Task 11 — Flow Field & Movement Terrain Integration

## Metadata
- **Task_ID:** task_11_terrain_flow_movement
- **Execution_Phase:** Phase 2 (depends on Task 09)
- **Model_Tier:** advanced
- **Dependencies:**
  - Task 09 (`terrain.rs` — `TerrainGrid` resource)
- **Context_Bindings:**
  - `.agents/skills/rust-code-standards/SKILL.md`
  - `implementation_plan.md` → Feature 3: Terrain Editor → Flow Field + Movement sections

## Target Files
- `micro-core/src/pathfinding/flow_field.rs` — **MODIFY**
- `micro-core/src/systems/flow_field_update.rs` — **MODIFY**
- `micro-core/src/systems/movement.rs` — **MODIFY**

## Contract: Integer Cost Map in Dijkstra

### Flow Field `calculate()` Signature Change
```rust
// OLD:
pub fn calculate(&mut self, goals: &[Vec2], obstacles: &[IVec2])

// NEW:
pub fn calculate(&mut self, goals: &[Vec2], obstacles: &[IVec2], cost_map: Option<&[u16]>)
```

When `cost_map` is `None`, behavior is **identical** to current (backward compatible).
When `Some`, the inner Dijkstra loop uses pure integer math:

```rust
let terrain_penalty = cost_map
    .map(|cm| cm[self.cell_index(neighbor)])
    .unwrap_or(100);

// Absolute wall — skip entirely (never enters BFS queue)
if terrain_penalty == u16::MAX { continue; }

// Integer math: (10 × 200) / 100 = 20 (double cost for mud)
let effective_cost = (move_cost * terrain_penalty as u32) / 100;
let next_cost = cost.saturating_add(effective_cost);
```

### Movement System: Kinematic Wall-Sliding

Before applying position change, check X and Y axes INDEPENDENTLY:

```rust
let world_to_cell = |x: f32, y: f32| -> IVec2 {
    IVec2::new(
        (x / terrain.cell_size).floor() as i32,
        (y / terrain.cell_size).floor() as i32,
    )
};

// Check X axis independently — allows sliding along walls
if terrain.get_hard_cost(world_to_cell(next_x, pos.y)) == u16::MAX {
    vel.dx = 0.0;
    next_x = pos.x;  // Blocked on X — entity slides vertically
}
// Check Y axis independently
if terrain.get_hard_cost(world_to_cell(pos.x, next_y)) == u16::MAX {
    vel.dy = 0.0;
    next_y = pos.y;  // Blocked on Y — entity slides horizontally
}

// Apply soft terrain speed modifier (AFTER wall check, so entity is in a valid cell)
let cell = world_to_cell(next_x, next_y);
let soft = terrain.get_soft_cost(cell) as f32 / 100.0;
let effective_speed = mc.max_speed * soft;
```

## Strict Instructions

### 1. Modify `micro-core/src/pathfinding/flow_field.rs`

**a.** Add `cost_map: Option<&[u16]>` parameter to `calculate()`.

**b.** In the Dijkstra expansion loop (after anti-corner-cutting check), add terrain cost logic:
- Read `terrain_penalty` from `cost_map` at neighbor index, default `100`
- If `terrain_penalty == u16::MAX`, `continue` (absolute wall — skip BFS)
- Calculate `effective_cost = (move_cost * terrain_penalty as u32) / 100`
- Use `effective_cost` instead of `move_cost` for `next_cost`

**c.** Also add the `u16::MAX` check in the gradient phase (Phase 2 of calculate):
- In `get_cost` closure, if the neighbor's cost_map entry is `u16::MAX`, treat it same as obstacle (return `current_cost`)

**d.** CRITICAL: Update ALL existing calls to `calculate()` to pass `None` as third argument. All existing tests must still pass unchanged.

### 2. Modify `micro-core/src/systems/flow_field_update.rs`

**a.** Add `terrain: Res<TerrainGrid>` to the system signature (import from `crate::terrain`).

**b.** Change the `field.calculate()` call:
```rust
// OLD:
field.calculate(goals, &[]);
// NEW:
field.calculate(goals, &terrain.hard_obstacles(), Some(&terrain.hard_costs));
```

### 3. Modify `micro-core/src/systems/movement.rs`

**a.** Add `terrain: Res<TerrainGrid>` to the system signature.

**b.** After computing `next_x`, `next_y` from velocity, add kinematic wall-sliding (per-axis check as shown in contract above).

**c.** After wall-sliding, apply `soft_cost` speed modifier to `effective_speed`.

**d.** Ensure the system compiles with the new `Res<TerrainGrid>` — this resource is registered in `main.rs` (Task 14 integration, but already pre-registered from Task 07 session).

## Verification Strategy

**Test_Type:** unit
**Test_Stack:** `cargo test` (standard Rust)

**Mandated tests:**

In `flow_field.rs`:
1. `test_cost_map_none_backward_compatible` — `calculate(goals, &[], None)` produces same result as before
2. `test_cost_map_200_doubles_chamfer_cost` — Set cost=200 for a cell, verify its integration cost is ~2× normal
3. `test_cost_map_max_acts_as_wall` — Set cost=u16::MAX for a cell, verify it's treated as obstacle (MAX cost, no direction)
4. `test_cost_map_125_slightly_increases_cost` — Verify pushable terrain has marginally higher cost than clear

In `flow_field_update.rs`:
5. `test_flow_field_update_uses_terrain` — Build app with TerrainGrid wall → verify flow field routes around it

In `movement.rs`:
6. `test_wall_sliding_blocks_x_axis` — Entity moving right into wall → X zeroed, Y preserved (slides vertically)
7. `test_wall_sliding_blocks_y_axis` — Entity moving down into wall → Y zeroed, X preserved (slides horizontally)
8. `test_soft_cost_reduces_speed` — Entity in soft_cost=50 cell moves at half speed

**Commands:**
```bash
cd micro-core && cargo test flow_field
cd micro-core && cargo test movement
```
