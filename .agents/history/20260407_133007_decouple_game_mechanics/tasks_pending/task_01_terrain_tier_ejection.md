# Task 01: Terrain Tier Ejection

- **Task_ID:** task_01_terrain_tier_ejection
- **Execution_Phase:** 1 (parallel with Task 02)
- **Model_Tier:** standard
- **Feature:** Decoupling Game Mechanics

## Target_Files
- `micro-core/src/terrain.rs`

## Dependencies
- None (Phase 1 — no prior tasks required)

## Context_Bindings
- `context/architecture`
- `context/ipc-protocol`
- `skills/rust-code-standards`

## Strict_Instructions

### Goal
Remove hardcoded terrain tier constants from `terrain.rs`. Replace them with instance fields on `TerrainGrid` so the thresholds are injectable from the game profile via ZMQ.

### Step 1: Remove Constants

Delete these three `pub const` declarations at the top of `terrain.rs`:
```rust
pub const TERRAIN_DESTRUCTIBLE_MIN: u16 = 60_001;
pub const TERRAIN_DESTRUCTIBLE_MAX: u16 = 65_534;
pub const TERRAIN_PERMANENT_WALL: u16 = u16::MAX;
```

### Step 2: Add Fields to `TerrainGrid`

Add two new fields to the `TerrainGrid` struct:

```rust
pub struct TerrainGrid {
    pub width: u32,
    pub height: u32,
    pub cell_size: f32,
    pub hard_costs: Vec<u16>,
    pub soft_costs: Vec<u16>,
    /// Costs >= this value are impassable permanent walls.
    /// Default: u16::MAX (65535). Set to 0 to disable wall detection.
    pub impassable_threshold: u16,
    /// Costs in [destructible_min, impassable_threshold) are destructible walls.
    /// Default: 0 (no destructible walls unless configured).
    pub destructible_min: u16,
}
```

### Step 3: Update `TerrainGrid::new()`

The constructor must initialize the new fields with sensible defaults (these are "safe empty" — no wall detection unless configured):

```rust
pub fn new(width: u32, height: u32, cell_size: f32) -> Self {
    let size = (width * height) as usize;
    Self {
        width,
        height,
        cell_size,
        hard_costs: vec![100u16; size],
        soft_costs: vec![100u16; size],
        impassable_threshold: u16::MAX,
        destructible_min: 0,
    }
}
```

> **Design Note:** `impassable_threshold: u16::MAX` keeps the existing behavior where `u16::MAX` = wall. This is NOT game logic — it's the engine's default interpretation of the cost grid. The game profile can override this. `destructible_min: 0` means "no destructible walls" by default — the game profile injects the actual range.

### Step 4: Update Tier Helper Methods

Replace all references to the deleted constants with instance field references:

**`is_destructible()`:**
```rust
pub fn is_destructible(&self, cell: IVec2) -> bool {
    if self.destructible_min == 0 { return false; } // Feature disabled
    let cost = self.get_hard_cost(cell);
    cost >= self.destructible_min && cost < self.impassable_threshold
}
```

**`is_permanent_wall()`:**
```rust
pub fn is_permanent_wall(&self, cell: IVec2) -> bool {
    self.get_hard_cost(cell) >= self.impassable_threshold
}
```

**`is_wall()`:**
```rust
pub fn is_wall(&self, cell: IVec2) -> bool {
    let cost = self.get_hard_cost(cell);
    cost >= self.impassable_threshold || (self.destructible_min > 0 && cost >= self.destructible_min)
}
```

**`damage_cell()`:**
```rust
pub fn damage_cell(&mut self, cell: IVec2, damage: u16) -> bool {
    if !self.in_bounds(cell) { return false; }
    let idx = (cell.y as u32 * self.width + cell.x as u32) as usize;
    let cost = self.hard_costs[idx];

    // Permanent walls are immune
    if cost >= self.impassable_threshold { return false; }

    // Destructible walls — apply damage
    if self.destructible_min > 0 && cost >= self.destructible_min {
        let new_cost = cost.saturating_sub(damage);
        if new_cost < self.destructible_min {
            self.hard_costs[idx] = 100; // Collapse to passable
            return true;
        }
        self.hard_costs[idx] = new_cost;
    }

    false
}
```

### Step 5: Update Serialization

Add `#[serde(default)]` to the new fields so JSON deserialization is backward compatible:

```rust
#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct TerrainGrid {
    pub width: u32,
    pub height: u32,
    pub cell_size: f32,
    pub hard_costs: Vec<u16>,
    pub soft_costs: Vec<u16>,
    #[serde(default = "default_impassable")]
    pub impassable_threshold: u16,
    #[serde(default)]
    pub destructible_min: u16,
}

fn default_impassable() -> u16 { u16::MAX }
```

### Step 6: Fix ALL Tests

Update every test in `terrain.rs` that references the deleted constants. Replace:
- `TERRAIN_DESTRUCTIBLE_MIN` → `grid.destructible_min` or a local `let` value
- `TERRAIN_DESTRUCTIBLE_MAX` → `grid.impassable_threshold - 1`
- `TERRAIN_PERMANENT_WALL` → `grid.impassable_threshold` or `u16::MAX`

For tests that test tier behavior, you MUST configure the grid's thresholds first:
```rust
let mut grid = TerrainGrid::new(5, 5, 20.0);
grid.impassable_threshold = u16::MAX;
grid.destructible_min = 60_001;
```

Rewrite `test_tier_constants_correct_order` → `test_tier_thresholds_injectable` that verifies the fields can be set and the methods respond correctly.

Add a new test: `test_destructible_disabled_by_default` that verifies `is_destructible()` returns false when `destructible_min == 0`.

### Step 7: Verify

```bash
cd micro-core && cargo test terrain
cd micro-core && cargo clippy
```

All terrain tests must pass. No clippy warnings from this file.

## Verification_Strategy
  Test_Type: unit
  Test_Stack: Rust (cargo test)
  Acceptance_Criteria:
    - "All terrain tests pass (no references to deleted constants)"
    - "TerrainGrid serialization roundtrip includes new fields"
    - "is_destructible returns false when destructible_min == 0"
    - "is_wall and is_destructible use instance fields"
    - "`cargo clippy` produces no new warnings"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test terrain"
    - "cd micro-core && cargo clippy"
