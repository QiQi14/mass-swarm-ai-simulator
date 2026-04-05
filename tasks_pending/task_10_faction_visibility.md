# Task 10 — Faction Visibility & VisionRadius

## Metadata
- **Task_ID:** task_10_faction_visibility
- **Execution_Phase:** Phase 1 (Parallel)
- **Model_Tier:** standard
- **Dependencies:** None
- **Context_Bindings:**
  - `.agents/skills/rust-code-standards/SKILL.md`
  - `implementation_plan.md` → Feature 2: Fog of War + Inter-Layer Architecture

## Target Files
- `micro-core/src/visibility.rs` — **NEW**
- `micro-core/src/components.rs` — **MODIFY** (add VisionRadius)
- `micro-core/src/lib.rs` — **MODIFY** (register module)

## Contract

### VisionRadius Component
```rust
#[derive(Component, Debug, Clone)]
pub struct VisionRadius(pub f32);

impl Default for VisionRadius {
    fn default() -> Self { Self(80.0) }
}
```

### FactionVisibility Resource (Bit-Packed)

A 50×50 grid = 2,500 cells. Stored as `Vec<u32>` where each `u32` holds 32 cells.
Total per faction: `ceil(2500/32) = 79 integers`.

Two grids per faction:
- **explored**: Cells EVER seen by any entity of this faction. Persists across ticks.
- **visible**: Cells CURRENTLY within vision range. Rebuilt every tick (transient).

## Strict Instructions

### 1. Modify `micro-core/src/components.rs`

Add the `VisionRadius` component as defined above. This is a simple newtype wrapper.

### 2. Create `micro-core/src/visibility.rs`

```rust
//! # Faction Visibility
//!
//! Per-faction fog of war state — bit-packed, self-contained resource.
//! Works without the debug visualizer. ML brain reads this via ZMQ.
//!
//! ## Ownership
//! - **Task:** task_10_faction_visibility
//! - **Contract:** implementation_plan.md → Feature 2: Fog of War
//!
//! ## Bit-Packing
//! Grid is stored as `Vec<u32>` — each u32 holds 32 cells.
//! 50×50 grid = 2,500 cells = 79 integers per faction.
//!
//! ## Depends On
//! - `crate::components::{Position, FactionId, VisionRadius}`

use bevy::prelude::*;
use bevy::platform::collections::HashMap;
```

Implement the `FactionVisibility` struct as a `Resource`:
- Fields: `grid_width: u32`, `grid_height: u32`, `cell_size: f32`
- `explored: HashMap<u32, Vec<u32>>` — bit-packed per faction
- `visible: HashMap<u32, Vec<u32>>` — bit-packed per faction

**Static helper methods** (these work on `&mut [u32]` slices, not `&self`):

1. `pub fn bitpack_len(grid_width: u32, grid_height: u32) -> usize`
   - Returns `((grid_width * grid_height) as usize + 31) / 32`

2. `pub fn set_bit(grid: &mut [u32], index: usize)`
   - `grid[index / 32] |= 1 << (index % 32)`

3. `pub fn get_bit(grid: &[u32], index: usize) -> bool`
   - `(grid[index / 32] >> (index % 32)) & 1 == 1`

4. `pub fn clear_all(grid: &mut [u32])`
   - `grid.iter_mut().for_each(|v| *v = 0)`

**Instance methods:**

5. `pub fn new(grid_width: u32, grid_height: u32, cell_size: f32) -> Self`
   - Initialize with empty HashMaps

6. `pub fn ensure_faction(&mut self, faction_id: u32)`
   - Creates explored + visible grids for a faction if they don't exist yet
   - Size: `bitpack_len(self.grid_width, self.grid_height)`

7. `pub fn reset_explored(&mut self)`
   - Clear ALL explored grids (for scenario reload)

### 3. Register in `micro-core/src/lib.rs`

Add `pub mod visibility;`

## Important Notes

- This task creates the **data structures only**. The `visibility_update_system` that populates these grids is in Task 12.
- VisionRadius defaults to 80.0 world units — 4 cells at cell_size=20.
- The bit-packing helpers are static methods because they operate on raw `&mut [u32]` slices, which can be borrowed from HashMap values without holding a mutable reference to the whole struct.

## Verification Strategy

**Test_Type:** unit
**Test_Stack:** `cargo test` (standard Rust)

**Mandated tests (in `visibility.rs`):**

1. `test_bitpack_len_50x50` — `bitpack_len(50, 50)` returns `79`
2. `test_bitpack_len_edge_case_32` — `bitpack_len(4, 8)` (32 cells) returns `1`
3. `test_set_get_bit_roundtrip` — Set bits at indices 0, 31, 32, 2499 → verify all true, others false
4. `test_clear_all_zeros_grid` — Set bits, call `clear_all`, verify all false
5. `test_ensure_faction_creates_grids` — `ensure_faction(0)` creates explored and visible entries
6. `test_ensure_faction_idempotent` — Calling twice doesn't reset existing data
7. `test_reset_explored_clears_all_factions` — Set explored bits for 3 factions, `reset_explored()`, verify all cleared
8. `test_vision_radius_default` — `VisionRadius::default().0` == 80.0

**Commands:**
```bash
cd micro-core && cargo test visibility
cd micro-core && cargo test test_vision_radius
```
