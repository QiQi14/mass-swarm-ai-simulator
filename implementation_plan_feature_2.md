# Feature 2: State Vectorization & ZMQ Protocol Upgrade (v3 — Patched)

> **Tasks:** 03 (State Vectorizer), 07 (ZMQ Protocol Upgrade)
> **Domain:** Rust / Bevy ECS + IPC Bridge
> **v3 Patches:** Removed Rust-side channel packing (Vectorization Redundancy fix)

---

## Task 03: State Vectorizer System

**Task_ID:** `task_03_state_vectorizer`
**Execution_Phase:** 1 (parallel)
**Model_Tier:** `standard`
**Target_Files:**
  - `micro-core/src/systems/state_vectorizer.rs` (NEW)
  - `micro-core/src/systems/mod.rs` (MODIFY)
**Dependencies:** None
**Context_Bindings:**
  - `context/architecture`
  - `context/conventions`
  - `skills/rust-code-standards`

### Strict Instructions

> [!IMPORTANT]
> ## Vectorization Redundancy Fix
> This module contains ONLY raw data export functions (`build_density_maps`, `build_summary_stats`).
>
> **DO NOT** implement `pack_density_channels` or any NN-specific channel packing in Rust.
> Rust is the **Physics Engine** — it exports raw `HashMap<u32, Vec<f32>>` (one density grid per faction, including sub-factions).
> Python's `vectorizer.py` is the **Adapter** — it packs dynamic faction maps into fixed 4-channel tensors for the neural network.
>
> This follows the Data Isolation principle: NN architecture concerns (channel count, packing order) belong in Python, not in the simulation core.

Create `micro-core/src/systems/state_vectorizer.rs`:

```rust
//! # State Vectorizer
//!
//! Compresses 10,000+ entity positions into fixed-size spatial heatmaps.
//! Produces one density channel per faction (including sub-factions).
//!
//! ## Responsibility Boundary
//! This module produces RAW density data as HashMap<faction_id, Vec<f32>>.
//! It does NOT pack data into fixed NN channels — that is Python's job.
//!
//! ## Algorithm
//! 1. Iterate all entities with Position + FactionId
//! 2. Map world position → grid cell: floor(pos / cell_size)
//! 3. Increment cell counter for that faction
//! 4. Normalize: cell_value / max_density (configurable)
//!
//! ## Ownership
//! - **Task:** task_03_state_vectorizer

use std::collections::HashMap;

/// Default maximum density for normalization.
/// Cells with more entities than this are clamped to 1.0.
pub const DEFAULT_MAX_DENSITY: f32 = 50.0;

/// Builds density heatmaps from entity positions.
///
/// Returns a HashMap where each key is a faction_id and each value
/// is a flat Vec<f32> of size (grid_w × grid_h), row-major order.
/// Values are normalized to [0.0, 1.0].
///
/// Sub-factions (created by SplitFaction) automatically get their own
/// density channel — no special handling needed.
pub fn build_density_maps(
    entities: &[(f32, f32, u32)],
    grid_w: u32,
    grid_h: u32,
    cell_size: f32,
    max_density: f32,
) -> HashMap<u32, Vec<f32>> {
    let total_cells = (grid_w * grid_h) as usize;
    let mut count_maps: HashMap<u32, Vec<u32>> = HashMap::new();

    for &(x, y, faction) in entities {
        let cx = (x / cell_size).floor() as i32;
        let cy = (y / cell_size).floor() as i32;

        if cx < 0 || cx >= grid_w as i32 || cy < 0 || cy >= grid_h as i32 {
            continue;
        }

        let idx = (cy as u32 * grid_w + cx as u32) as usize;
        let counts = count_maps
            .entry(faction)
            .or_insert_with(|| vec![0u32; total_cells]);
        counts[idx] += 1;
    }

    count_maps
        .into_iter()
        .map(|(faction, counts)| {
            let normalized: Vec<f32> = counts
                .iter()
                .map(|&c| (c as f32 / max_density).min(1.0))
                .collect();
            (faction, normalized)
        })
        .collect()
}

/// Builds summary statistics from entity data.
///
/// Returns (own_count, enemy_count, own_avg_stat0, enemy_avg_stat0)
/// normalized to [0.0, 1.0] for NN input.
pub fn build_summary_stats(
    entities: &[(f32, f32, u32, f32)],
    brain_faction: u32,
    max_entities: f32,
) -> [f32; 4] {
    let mut own_count = 0u32;
    let mut enemy_count = 0u32;
    let mut own_stat_sum = 0.0f32;
    let mut enemy_stat_sum = 0.0f32;

    for &(_, _, faction, stat0) in entities {
        if faction == brain_faction {
            own_count += 1;
            own_stat_sum += stat0;
        } else {
            enemy_count += 1;
            enemy_stat_sum += stat0;
        }
    }

    [
        (own_count as f32 / max_entities).min(1.0),
        (enemy_count as f32 / max_entities).min(1.0),
        if own_count > 0 { own_stat_sum / own_count as f32 } else { 0.0 },
        if enemy_count > 0 { enemy_stat_sum / enemy_count as f32 } else { 0.0 },
    ]
}
```

### Module Registration (`systems/mod.rs`)

```rust
pub mod state_vectorizer;
```

### Unit Tests

1. `test_density_map_single_entity` — 1 entity at known position → correct cell
2. `test_density_map_multiple_factions` — 2 factions → 2 separate density maps
3. `test_density_map_sub_faction` — Faction 101 (sub-faction) gets its own map
4. `test_density_map_normalization` — 50 entities at max_density=50 → 1.0
5. `test_density_map_clamping` — 100 entities at max_density=50 → clamped to 1.0
6. `test_density_map_out_of_bounds_ignored` — Entity at (-10, -10) doesn't crash
7. `test_density_map_empty_entities` — Empty input → empty HashMap
8. `test_density_map_grid_boundaries` — Entity at exact grid edge
9. `test_summary_stats_basic` — Correct counts and averages
10. `test_summary_stats_empty` — No entities → all zeros

### Verification_Strategy
```
Test_Type: unit
Test_Stack: cargo test (Rust)
Acceptance_Criteria:
  - Density maps produced for all factions including sub-factions
  - NO pack_density_channels function exists in this module
  - Normalization clamps to [0.0, 1.0]
  - Out-of-bounds entities don't panic
Suggested_Test_Commands:
  - "cd micro-core && cargo test state_vectorizer"
```

---

## Task 07: ZMQ Protocol Upgrade

**Task_ID:** `task_07_zmq_protocol_upgrade`
**Execution_Phase:** 3 (sequential)
**Model_Tier:** `advanced`
**Target_Files:**
  - `micro-core/src/bridges/zmq_bridge/systems.rs` (MODIFY)
  - `micro-core/src/bridges/zmq_protocol.rs` (MODIFY)
  - `micro-core/src/bridges/zmq_bridge/mod.rs` (MODIFY)
  - `micro-core/src/systems/flow_field_update.rs` (MODIFY)
**Dependencies:** Task 01, Task 03, Task 05
**Context_Bindings:**
  - `context/ipc-protocol`
  - `context/architecture`
  - `context/conventions`
  - `skills/rust-code-standards`

### Strict Instructions

#### 1. Upgrade `build_state_snapshot`

Integrate raw density maps (no channel packing) and new snapshot fields:

```rust
use crate::systems::state_vectorizer::{build_density_maps, DEFAULT_MAX_DENSITY};
use crate::config::{ActiveZoneModifiers, InterventionTracker, ActiveSubFactions, AggroMaskRegistry};

fn build_state_snapshot(
    // ... existing params ...
    zones: &ActiveZoneModifiers,
    intervention: &InterventionTracker,
    sub_factions: &ActiveSubFactions,
    aggro: &AggroMaskRegistry,
) -> StateSnapshot {
    // ... existing entity loop (fog-filtered) ...

    // Raw density maps — HashMap<faction_id, Vec<f32>>
    // Sub-factions automatically get their own key
    let entity_positions: Vec<(f32, f32, u32)> = entities
        .iter()
        .map(|e| (e.x, e.y, e.faction_id))
        .collect();

    let density_maps = build_density_maps(
        &entity_positions,
        terrain.width, terrain.height,
        terrain.cell_size, DEFAULT_MAX_DENSITY,
    );

    // Zone modifier snapshots
    let active_zones = zones.zones.iter()
        .map(|z| ZoneModifierSnapshot {
            target_faction: z.target_faction,
            x: z.x, y: z.y, radius: z.radius,
            cost_modifier: z.cost_modifier,
            ticks_remaining: z.ticks_remaining,
        })
        .collect();

    // Aggro mask serialization
    let aggro_masks = aggro.masks.iter()
        .map(|((s, t), &v)| (format!("{}_{}", s, t), v))
        .collect();

    StateSnapshot {
        // ... existing fields ...
        density_maps,
        intervention_active: intervention.active,
        active_zones,
        active_sub_factions: sub_factions.factions.clone(),
        aggro_masks,
    }
}
```

#### 2. Upgrade `ai_poll_system` — Parse `MacroDirective`

```rust
// Try new MacroDirective first, fallback to legacy MacroAction
match serde_json::from_str::<MacroDirective>(&reply_json) {
    Ok(directive) => {
        latest_directive.directive = Some(directive);
    }
    Err(_) => {
        if let Ok(_action) = serde_json::from_str::<MacroAction>(&reply_json) {
            latest_directive.directive = Some(MacroDirective::Hold);
        }
    }
}
```

#### 3. Update `flow_field_update_system`

Two changes:

**A. Handle `NavigationTarget` variants:**

```rust
// Replace the current target_faction extraction (line 45-47):
// BEFORE: .map(|r| (r.follower_faction, r.target_faction))
// AFTER:  Handle NavigationTarget enum

for rule in nav_rules.rules.iter() {
    let follower = rule.follower_faction;

    match &rule.target {
        NavigationTarget::Faction { faction_id } => {
            // Existing logic: fog-filtered enemy positions as goals
            let goals = /* ... query visible entities of faction_id ... */;
            // ... calculate flow field ...
        }
        NavigationTarget::Waypoint { x, y } => {
            // Static waypoint: single goal coordinate, no fog filtering
            let goals = vec![Vec2::new(*x, *y)];
            // ... calculate flow field ...
        }
    }
}
```

**B. Zone modifier cost overlay (with MOSES EFFECT GUARD):**

Before calling `field.calculate()`, create a mutable cost_map clone and overlay zone modifiers:

```rust
// Clone terrain costs for modification
let mut cost_map = terrain.hard_costs.clone();

// Apply zone modifier overlays (see Feature 1 PATCH 2 for the guard)
for zone in active_zones.zones.iter() {
    if zone.target_faction != follower { continue; }

    let cx = (zone.x / cell_size).floor() as i32;
    let cy = (zone.y / cell_size).floor() as i32;
    let r_cells = (zone.radius / cell_size).ceil() as i32;

    for dy in -r_cells..=r_cells {
        for dx in -r_cells..=r_cells {
            let nx = cx + dx;
            let ny = cy + dy;
            if nx < 0 || nx >= grid_w as i32 || ny < 0 || ny >= grid_h as i32 { continue; }
            let dist = ((dx * dx + dy * dy) as f32).sqrt() * cell_size;
            if dist > zone.radius { continue; }

            let idx = (ny as u32 * grid_w as u32 + nx as u32) as usize;
            let current_cost = cost_map[idx];

            // PATCH 2: MOSES EFFECT GUARD — never modify walls
            if current_cost == u16::MAX { continue; }

            let adjusted = (current_cost as f32 + zone.cost_modifier)
                .clamp(1.0, (u16::MAX - 1) as f32);
            cost_map[idx] = adjusted as u16;
        }
    }
}

// Pass modified cost_map to flow field calculation
field.calculate(&goals, &terrain.hard_obstacles(), Some(&cost_map));
```

#### 4. Register Resources in ZmqBridgePlugin (`mod.rs`)

```rust
app.init_resource::<LatestDirective>();
app.init_resource::<ActiveZoneModifiers>();
app.init_resource::<InterventionTracker>();
app.init_resource::<FactionSpeedBuffs>();
app.init_resource::<AggroMaskRegistry>();
app.init_resource::<ActiveSubFactions>();
```

### Unit Tests

1. `test_snapshot_includes_density_maps`
2. `test_snapshot_sub_faction_density` — Faction 101 has its own density map key
3. `test_snapshot_intervention_flag`
4. `test_snapshot_active_zones`
5. `test_snapshot_aggro_masks_serialization`
6. `test_ai_poll_parses_all_directive_variants`
7. `test_ai_poll_legacy_fallback`
8. `test_flow_field_waypoint_target`
9. `test_flow_field_zone_modifier_attract`
10. `test_flow_field_zone_modifier_repel`
11. **`test_flow_field_zone_modifier_wall_immune`** — (PATCH 2 regression: wall cell unchanged after overlay)

### Verification_Strategy
```
Test_Type: unit + integration
Test_Stack: cargo test (Rust)
Acceptance_Criteria:
  - StateSnapshot includes all new fields (density_maps, active_zones, aggro_masks, etc.)
  - density_maps is raw HashMap, NOT pre-packed channels
  - Zone modifier cost overlay respects MOSES EFFECT GUARD
  - NavigationTarget::Waypoint produces correct flow field
  - All existing tests pass after NavigationRule migration
Suggested_Test_Commands:
  - "cd micro-core && cargo test zmq"
  - "cd micro-core && cargo test flow_field"
  - "cd micro-core && cargo test state_vectorizer"
```
