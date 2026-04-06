# Feature 1: Rust Input Contracts & Override System (v3 — Patched)

> **Tasks:** 01 (MacroDirective Protocol), 02 (EngineOverride Component), 05 (Directive Executor System)
> **Domain:** Rust / Bevy ECS
> **v3 Patches:** Vaporization Bug, Moses Effect, Ghost State Leakage, f32 Sort Panic

---

## Task 01: MacroDirective Protocol

**Task_ID:** `task_01_macro_directive_protocol`
**Execution_Phase:** 1 (parallel)
**Model_Tier:** `standard`
**Target_Files:** `micro-core/src/bridges/zmq_protocol.rs`
**Dependencies:** None
**Context_Bindings:**
  - `context/ipc-protocol`
  - `context/conventions`
  - `skills/rust-code-standards`

### Strict Instructions

1. Open `micro-core/src/bridges/zmq_protocol.rs`

2. Add the `NavigationTarget` enum:

```rust
/// Navigation target: dynamic (chase a faction) or static (go to a point).
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
#[serde(tag = "type")]
pub enum NavigationTarget {
    Faction { faction_id: u32 },
    Waypoint { x: f32, y: f32 },
}
```

3. Add the full `MacroDirective` enum (after existing `MacroAction` struct):

```rust
/// Macro-level strategic directives from ML Brain → Rust Core.
/// 8-action vocabulary enabling all three swarm-splitting strategies:
/// - Pheromone Gravity Wells (SetZoneModifier)
/// - Dynamic Sub-Faction Tagging (SplitFaction/MergeFaction)
/// - Boids Self-Organizing Flanking (emergent, no directive needed)
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
#[serde(tag = "directive")]
pub enum MacroDirective {
    Hold,

    UpdateNavigation {
        follower_faction: u32,
        target: NavigationTarget,
    },

    TriggerFrenzy {
        faction: u32,
        speed_multiplier: f32,
        duration_ticks: u32,
    },

    Retreat {
        faction: u32,
        retreat_x: f32,
        retreat_y: f32,
    },

    /// Positive cost_modifier = repel, Negative = attract
    SetZoneModifier {
        target_faction: u32,
        x: f32,
        y: f32,
        radius: f32,
        cost_modifier: f32,
    },

    /// Rust selects entities nearest to epicenter first (Quickselect O(N))
    SplitFaction {
        source_faction: u32,
        new_sub_faction: u32,
        percentage: f32,
        epicenter: [f32; 2],
    },

    MergeFaction {
        source_faction: u32,
        target_faction: u32,
    },

    SetAggroMask {
        source_faction: u32,
        target_faction: u32,
        allow_combat: bool,
    },
}
```

4. Add `ZoneModifierSnapshot`:

```rust
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct ZoneModifierSnapshot {
    pub target_faction: u32,
    pub x: f32,
    pub y: f32,
    pub radius: f32,
    pub cost_modifier: f32,
    pub ticks_remaining: u32,
}
```

5. Extend `StateSnapshot` (all with `#[serde(default)]`):
   - `pub density_maps: std::collections::HashMap<u32, Vec<f32>>`
   - `pub intervention_active: bool`
   - `pub active_zones: Vec<ZoneModifierSnapshot>`
   - `pub active_sub_factions: Vec<u32>`
   - `pub aggro_masks: std::collections::HashMap<String, bool>`

6. Unit tests for all 8 variants + `NavigationTarget` (12 tests total).

> **Anti-pattern:** Do NOT remove existing `MacroAction`. Task 07 handles migration.

### Verification_Strategy
```
Test_Type: unit
Test_Stack: cargo test (Rust)
Acceptance_Criteria:
  - All 8 MacroDirective variants serde roundtrip correctly
  - NavigationTarget both variants roundtrip correctly
  - JSON uses "directive" tag key, NavigationTarget uses "type" tag key
  - Existing MacroAction tests still pass
Suggested_Test_Commands:
  - "cd micro-core && cargo test zmq_protocol"
```

---

## Task 02: Phase 3 Resource Scaffolding + EngineOverride

**Task_ID:** `task_02_phase3_resources`
**Execution_Phase:** 1 (parallel)
**Model_Tier:** `basic`
**Target_Files:**
  - `micro-core/src/components/engine_override.rs` (NEW)
  - `micro-core/src/components/mod.rs` (MODIFY)
  - `micro-core/src/config.rs` (MODIFY)
  - `micro-core/src/systems/directive_executor.rs` (NEW — resource type only)
**Dependencies:** None
**Context_Bindings:**
  - `context/conventions`
  - `skills/rust-code-standards`

> [!TIP]
> **Why expand T02?** By defining ALL Phase 3 resource types here (data-only structs, no logic),
> T11 (WS Protocol) can also run in Phase 1. This gives us debug visualizer tools
> before any core AI logic is implemented.

### Strict Instructions

#### 1. EngineOverride Component (`components/engine_override.rs`)

```rust
#[derive(Component, Debug, Clone)]
pub struct EngineOverride {
    pub forced_velocity: Vec2,
    pub ticks_remaining: Option<u32>,
}
```

#### 2. Phase 3 Resources (`config.rs`)

Add these data-only resource types. **NO system logic** — systems are in T05.

```rust
/// Active zone modifiers (flow field cost overlays).
#[derive(Resource, Debug, Default)]
pub struct ActiveZoneModifiers {
    pub zones: Vec<ZoneModifier>,
}

#[derive(Debug, Clone)]
pub struct ZoneModifier {
    pub target_faction: u32,
    pub x: f32,
    pub y: f32,
    pub radius: f32,
    pub cost_modifier: f32,
    pub ticks_remaining: u32,
}

/// Tracks active Tier 1 overrides for intervention flag.
#[derive(Resource, Debug, Default)]
pub struct InterventionTracker {
    pub active: bool,
}

/// Per-faction speed buffs.
#[derive(Resource, Debug, Default)]
pub struct FactionSpeedBuffs {
    pub buffs: std::collections::HashMap<u32, (f32, u32)>,
}

/// Aggro mask: controls which faction pairs can fight.
/// Missing entry = combat allowed (default true).
#[derive(Resource, Debug, Default)]
pub struct AggroMaskRegistry {
    pub masks: std::collections::HashMap<(u32, u32), bool>,
}

impl AggroMaskRegistry {
    /// Missing entry = true (combat allowed by default).
    pub fn is_combat_allowed(&self, source: u32, target: u32) -> bool {
        *self.masks.get(&(source, target)).unwrap_or(&true)
    }
}

/// Tracks currently active sub-factions.
#[derive(Resource, Debug, Default)]
pub struct ActiveSubFactions {
    pub factions: Vec<u32>,
}
```

#### 3. LatestDirective Resource (`systems/directive_executor.rs`)

Create the file with ONLY the resource type. The system function is added by T05.

```rust
//! # Directive Executor (Resource scaffold)
//!
//! This file contains the LatestDirective resource type.
//! The directive_executor_system function is added by Task 05.

use bevy::prelude::*;
use crate::bridges::zmq_protocol::MacroDirective;

/// Holds the most recently received MacroDirective.
/// Set by ai_poll_system (T07), consumed by directive_executor_system (T05).
#[derive(Resource, Debug, Default)]
pub struct LatestDirective {
    pub directive: Option<MacroDirective>,
}
```

> **Note:** T05 appends to this file, adding the system and tick functions.
> T11 reads `LatestDirective` to show last directive in the debug visualizer.

#### 4. Register resources in `main.rs` during `app.build()`

All resources are registered with `init_resource::<T>()` so they exist from startup.

### Unit Tests

1. `test_engine_override_default_no_ticks`
2. `test_aggro_mask_default_allows_combat`
3. `test_aggro_mask_explicit_deny`
4. `test_zone_modifier_fields`
5. `test_all_resources_impl_default`

---

## Task 05: Directive Executor & Engine Override Systems (Patched)

**Task_ID:** `task_05_directive_executor_system`
**Execution_Phase:** 2
**Model_Tier:** `advanced`
**Target_Files:**
  - `micro-core/src/systems/directive_executor.rs` (NEW)
  - `micro-core/src/systems/engine_override.rs` (NEW)
  - `micro-core/src/systems/mod.rs` (MODIFY)
  - `micro-core/src/systems/movement.rs` (MODIFY)
  - `micro-core/src/config.rs` (MODIFY)
  - `micro-core/src/rules/interaction.rs` (MODIFY)
  - `micro-core/src/rules/navigation.rs` (MODIFY)
**Dependencies:** Task 01 (MacroDirective), Task 02 (EngineOverride)
**Context_Bindings:**
  - `context/architecture`
  - `context/conventions`
  - `context/ipc-protocol`
  - `skills/rust-code-standards`

> [!CAUTION]
> ## Critical Vulnerability Patches (v3)
> This task contains four architectural safety patches identified during review.
> **All four MUST be implemented as specified. Deviations will produce runtime panics or simulation corruption.**

### Resources (Defined in T02 — `config.rs`)

> [!NOTE]
> All resource structs (`ActiveZoneModifiers`, `AggroMaskRegistry`, `FactionSpeedBuffs`,
> `InterventionTracker`, `ActiveSubFactions`) are defined in **Task 02** (`config.rs`).
> `LatestDirective` is defined in **Task 02** (`systems/directive_executor.rs`).
> This task only adds the **system functions** that operate on them.

### Directive Executor System (`directive_executor.rs`)

```rust
//! # Directive Executor System
//!
//! Consumes the latest MacroDirective and applies ECS mutations.
//!
//! ## SAFETY INVARIANTS (v3 Patches)
//! 1. VAPORIZATION GUARD: directive.take() — consume once, never re-execute
//! 2. GHOST STATE CLEANUP: MergeFaction purges ALL registry entries for dissolved faction
//! 3. QUICKSELECT: SplitFaction uses select_nth_unstable_by (O(N), f32-safe)

use bevy::prelude::*;
use crate::bridges::zmq_protocol::{MacroDirective, NavigationTarget};
use crate::rules::{NavigationRuleSet, NavigationRule};
use crate::config::{ActiveZoneModifiers, ZoneModifier, FactionSpeedBuffs, AggroMaskRegistry, ActiveSubFactions};
use crate::components::{Position, FactionId};

/// Holds the most recently received MacroDirective.
/// Set by ai_poll_system, consumed by directive_executor_system.
#[derive(Resource, Debug, Default)]
pub struct LatestDirective {
    pub directive: Option<MacroDirective>,
}

/// Applies the latest MacroDirective to the ECS world.
///
/// ## PATCH 1: Vaporization Guard
/// Uses `latest.directive.take()` to consume the directive. Without this,
/// the system re-executes the same directive at 60Hz — SplitFaction 30%
/// would vaporize the entire army in <1 second (30% of 30% of 30%...).
pub fn directive_executor_system(
    mut latest: ResMut<LatestDirective>,    // ← ResMut, NOT Res
    mut nav_rules: ResMut<NavigationRuleSet>,
    mut speed_buffs: ResMut<FactionSpeedBuffs>,
    mut zones: ResMut<ActiveZoneModifiers>,
    mut aggro: ResMut<AggroMaskRegistry>,
    mut sub_factions: ResMut<ActiveSubFactions>,
    mut faction_query: Query<(Entity, &Position, &mut FactionId)>,
) {
    // ══════════════════════════════════════════════════════════════
    // PATCH 1: VAPORIZATION GUARD
    // take() consumes the Option, replacing it with None.
    // The directive executes EXACTLY ONCE, then is gone.
    // ══════════════════════════════════════════════════════════════
    let Some(directive) = latest.directive.take() else { return; };

    match directive {
        MacroDirective::Hold => { /* no-op */ },

        MacroDirective::UpdateNavigation { follower_faction, target } => {
            if let Some(rule) = nav_rules.rules.iter_mut()
                .find(|r| r.follower_faction == follower_faction)
            {
                rule.target = target;
            } else {
                nav_rules.rules.push(NavigationRule {
                    follower_faction,
                    target,
                });
            }
        },

        MacroDirective::TriggerFrenzy { faction, speed_multiplier, duration_ticks } => {
            speed_buffs.buffs.insert(faction, (speed_multiplier, duration_ticks));
        },

        MacroDirective::Retreat { faction, retreat_x, retreat_y } => {
            let target = NavigationTarget::Waypoint { x: retreat_x, y: retreat_y };
            if let Some(rule) = nav_rules.rules.iter_mut()
                .find(|r| r.follower_faction == faction)
            {
                rule.target = target;
            } else {
                nav_rules.rules.push(NavigationRule {
                    follower_faction: faction,
                    target,
                });
            }
        },

        MacroDirective::SetZoneModifier { target_faction, x, y, radius, cost_modifier } => {
            zones.zones.push(ZoneModifier {
                target_faction, x, y, radius, cost_modifier,
                ticks_remaining: 120, // ~2 seconds at 60 TPS
            });
        },

        MacroDirective::SplitFaction { source_faction, new_sub_faction, percentage, epicenter } => {
            // ══════════════════════════════════════════════════════════
            // PATCH 4: QUICKSELECT (O(N), f32-safe)
            //
            // Why not .sort()?
            //   1. f32 does NOT implement Ord (NaN violates total ordering).
            //      .sort() won't compile. .sort_by(f32::total_cmp) is O(N log N).
            //   2. We only need the K closest — full sort is wasteful.
            //
            // select_nth_unstable_by partitions in O(N) average:
            //   After the call, candidates[..split_count] contains the
            //   K smallest distances (unordered). Exactly what we need.
            // ══════════════════════════════════════════════════════════
            let epi_vec = Vec2::new(epicenter[0], epicenter[1]);

            // Pass 1: Collect (Entity, dist_squared) for source faction
            let mut candidates: Vec<(Entity, f32)> = faction_query.iter()
                .filter(|(_, _, f)| f.0 == source_faction)
                .map(|(entity, pos, _)| {
                    let dist_sq = Vec2::new(pos.x, pos.y).distance_squared(epi_vec);
                    (entity, dist_sq)
                })
                .collect();

            let split_count = ((candidates.len() as f32) * percentage).round() as usize;
            if split_count == 0 || split_count > candidates.len() { return; }

            // Quickselect: partition so [..split_count] are the K closest
            if split_count < candidates.len() {
                candidates.select_nth_unstable_by(split_count - 1, |a, b| {
                    a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal)
                });
            }

            // Pass 2: Reassign FactionId for selected entities
            for i in 0..split_count {
                if let Ok((_, _, mut faction)) = faction_query.get_mut(candidates[i].0) {
                    faction.0 = new_sub_faction;
                }
            }

            // Register sub-faction
            if !sub_factions.factions.contains(&new_sub_faction) {
                sub_factions.factions.push(new_sub_faction);
            }
        },

        MacroDirective::MergeFaction { source_faction, target_faction } => {
            // Re-tag all entities
            for (_, _, mut faction) in faction_query.iter_mut() {
                if faction.0 == source_faction {
                    faction.0 = target_faction;
                }
            }

            // ══════════════════════════════════════════════════════════
            // PATCH 3: GHOST STATE CLEANUP
            //
            // Purge ALL registry entries for the dissolved faction.
            // Without this, if Python reuses the same sub-faction ID,
            // the new army inherits stale speed buffs, aggro masks,
            // and zone modifiers — causing RL data divergence.
            // ══════════════════════════════════════════════════════════
            sub_factions.factions.retain(|&f| f != source_faction);
            nav_rules.rules.retain(|r| r.follower_faction != source_faction);
            zones.zones.retain(|z| z.target_faction != source_faction);
            speed_buffs.buffs.remove(&source_faction);
            aggro.masks.retain(|&(s, t), _| s != source_faction && t != source_faction);
        },

        MacroDirective::SetAggroMask { source_faction, target_faction, allow_combat } => {
            // Bidirectional: both directions must be set for symmetric combat rules
            aggro.masks.insert((source_faction, target_faction), allow_combat);
            aggro.masks.insert((target_faction, source_faction), allow_combat);
        },
    }
}
```

### Aggro Mask Integration (`interaction.rs`)

The existing `interaction_system` at line 62-66 already filters by `rule.source_faction`. Add `AggroMaskRegistry` check:

```rust
pub fn interaction_system(
    // ... existing params ...
    aggro: Res<AggroMaskRegistry>,  // NEW parameter
) {
    // ... existing setup ...

    for (source_entity, source_pos, source_faction) in q_ro.iter() {
        for rule in &rules.rules {
            if rule.source_faction != source_faction.0 {
                continue;
            }

            // ═══ NEW: Check aggro mask before processing ═══
            // "The Blinders" — SetAggroMask can disable combat between
            // specific faction pairs (e.g., flanking unit ignores frontline)
            if !aggro.is_combat_allowed(rule.source_faction, rule.target_faction) {
                continue;
            }

            // ... existing neighbor loop unchanged ...
        }
    }
}
```

### NavigationRule Update (`navigation.rs`)

```rust
use crate::bridges::zmq_protocol::NavigationTarget;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct NavigationRule {
    pub follower_faction: u32,
    pub target: NavigationTarget,  // replaces target_faction: u32
}

impl Default for NavigationRuleSet {
    fn default() -> Self {
        Self {
            rules: vec![NavigationRule {
                follower_faction: 0,
                target: NavigationTarget::Faction { faction_id: 1 },
            }],
        }
    }
}
```

### Zone Modifier Cost Overlay in `flow_field_update_system`

> [!CAUTION]
> ## PATCH 2: MOSES EFFECT GUARD
> Zone modifier cost overlays MUST skip tiles where `cost == u16::MAX` (impassable walls).
> Without this guard, a negative `cost_modifier` (attraction pheromone) converts walls
> into traversable terrain — entities clip through solid rock.
>
> The existing Dijkstra guard at `flow_field.rs:160` (`if terrain_penalty == u16::MAX { continue; }`)
> operates on the cost_map AFTER overlay. If the overlay already reduced `u16::MAX` to `65035`,
> Dijkstra's guard never fires. The fix MUST be applied at the overlay step.

```rust
// In flow_field_update_system, AFTER copying terrain.hard_costs into a mutable cost_map,
// BEFORE passing cost_map to field.calculate():

for zone in active_zones.zones.iter() {
    if zone.target_faction != follower_faction { continue; }

    let cx = (zone.x / cell_size).floor() as i32;
    let cy = (zone.y / cell_size).floor() as i32;
    let r_cells = (zone.radius / cell_size).ceil() as i32;

    for dy in -r_cells..=r_cells {
        for dx in -r_cells..=r_cells {
            let nx = cx + dx;
            let ny = cy + dy;
            if nx < 0 || nx >= grid_w as i32 || ny < 0 || ny >= grid_h as i32 {
                continue;
            }
            let dist = ((dx * dx + dy * dy) as f32).sqrt() * cell_size;
            if dist > zone.radius { continue; }

            let idx = (ny as u32 * grid_w as u32 + nx as u32) as usize;
            let current_cost = cost_map[idx];

            // ══════════════════════════════════════════════════════
            // PATCH 2: MOSES EFFECT GUARD
            // NEVER modify impassable tiles. A wall is a wall is a wall.
            // Without this, cost_modifier = -500 on a wall tile converts
            // u16::MAX (65535) → 65035, making it traversable.
            // ══════════════════════════════════════════════════════
            if current_cost == u16::MAX { continue; }

            // Clamp upper to u16::MAX - 1 to prevent accidentally
            // creating phantom walls via positive cost_modifier
            let adjusted = (current_cost as f32 + zone.cost_modifier)
                .clamp(1.0, (u16::MAX - 1) as f32);
            cost_map[idx] = adjusted as u16;
        }
    }
}
```

### Engine Override System (`engine_override.rs`)

*(Unchanged from previous version)*

```rust
pub fn engine_override_system(
    mut commands: Commands,
    mut query: Query<(Entity, &mut Velocity, &mut EngineOverride)>,
    mut tracker: ResMut<InterventionTracker>,
) {
    tracker.active = !query.is_empty();
    for (entity, mut vel, mut over) in query.iter_mut() {
        vel.0 = over.forced_velocity;
        if let Some(ref mut ticks) = over.ticks_remaining {
            *ticks = ticks.saturating_sub(1);
            if *ticks == 0 {
                commands.entity(entity).remove::<EngineOverride>();
            }
        }
    }
}
```

### Tick-Down Systems

```rust
/// Decrements zone modifier timers and removes expired ones.
pub fn zone_tick_system(mut zones: ResMut<ActiveZoneModifiers>) {
    zones.zones.retain_mut(|z| {
        z.ticks_remaining = z.ticks_remaining.saturating_sub(1);
        z.ticks_remaining > 0
    });
}

/// Decrements speed buff timers and removes expired ones.
pub fn speed_buff_tick_system(mut buffs: ResMut<FactionSpeedBuffs>) {
    buffs.buffs.retain(|_, (_, ticks)| {
        *ticks = ticks.saturating_sub(1);
        *ticks > 0
    });
}
```

### Movement System Split (`movement.rs`)

Add `Without<EngineOverride>` filter and speed buff application:

```rust
pub fn movement_system(
    mut query: Query<
        (&mut Position, &mut Velocity, &FactionId, &MovementConfig),
        Without<EngineOverride>,  // ← Tier 1 override: skip these
    >,
    speed_buffs: Res<FactionSpeedBuffs>,
    // ... existing params ...
) {
    // ... existing logic ...

    // Apply speed buff:
    let speed_mult = speed_buffs.buffs.get(&faction.0)
        .map(|(mult, _)| *mult)
        .unwrap_or(1.0);
    // final_speed *= speed_mult;
}
```

### Module Registration (`systems/mod.rs`)

```rust
pub mod directive_executor;
pub mod engine_override;
```

---

## Unit Tests (Expanded with Regression Tests for Patches)

### Standard Tests (14)
1. `test_directive_hold_is_noop`
2. `test_directive_update_navigation_faction`
3. `test_directive_update_navigation_waypoint`
4. `test_directive_trigger_frenzy_sets_buff`
5. `test_directive_retreat_sets_waypoint`
6. `test_directive_set_zone_modifier`
7. `test_directive_split_faction_by_epicenter`
8. `test_directive_split_faction_percentage`
9. `test_directive_merge_faction`
10. `test_directive_set_aggro_mask_disables_combat`
11. `test_aggro_mask_default_allows_combat`
12. `test_engine_override_forces_velocity`
13. `test_engine_override_countdown_and_removal`
14. `test_movement_system_skips_overridden`

### Patch Regression Tests (8)

> [!IMPORTANT]
> **These tests are MANDATORY. They specifically reproduce the four vulnerabilities.**

15. **`test_vaporization_guard_directive_consumed_once`**
    - Setup: Insert a SplitFaction(30%) directive into LatestDirective
    - Run directive_executor_system **twice** (simulating 2 consecutive ticks)
    - Assert: First run splits 30% of entities. Second run is a no-op (directive is None).
    - Without patch: second run would split 30% of the remaining 70%, creating a cascade.

16. **`test_vaporization_guard_latest_is_none_after_execution`**
    - After running the system once, assert `latest.directive.is_none()`.

17. **`test_moses_effect_wall_remains_impassable`**
    - Setup: Create a TerrainGrid with a wall at (2,2) (`cost = u16::MAX`)
    - Apply a SetZoneModifier with `cost_modifier = -500.0` covering cell (2,2)
    - Run flow_field_update_system
    - Assert: The wall cell's cost in the flow field is STILL `u16::MAX`, not `65035`.
    - Assert: Flow field direction at wall cell is `Vec2::ZERO`.

18. **`test_moses_effect_non_wall_reduced_by_modifier`**
    - Same setup but on a normal tile (cost=100)
    - Assert: Cost is reduced from 100 to max(100 - 500, 1) = 1 (clamped).

19. **`test_ghost_state_merge_cleans_zones`**
    - Setup: SplitFaction → SetZoneModifier targeting sub-faction → MergeFaction
    - Assert: After merge, `active_zones.zones` has no entries for the dissolved faction.

20. **`test_ghost_state_merge_cleans_speed_buffs`**
    - Setup: SplitFaction → TriggerFrenzy for sub-faction → MergeFaction
    - Assert: After merge, `speed_buffs.buffs` has no entry for the dissolved faction.

21. **`test_ghost_state_merge_cleans_aggro_masks`**
    - Setup: SplitFaction → SetAggroMask for sub-faction → MergeFaction
    - Assert: After merge, `aggro.masks` has no entries involving the dissolved faction.

22. **`test_split_faction_quickselect_correct_count`**
    - Setup: 100 entities of faction 0, SplitFaction(30%, epicenter=[500,500])
    - Assert: Exactly 30 entities have FactionId changed to new_sub_faction.
    - Assert: The 30 selected entities are the closest to epicenter (verify min/max distances).

### Verification_Strategy
```
Test_Type: unit
Test_Stack: cargo test (Rust)
Acceptance_Criteria:
  - All 8 directives handled correctly
  - PATCH 1: Directive consumed on first read, None on second
  - PATCH 2: u16::MAX tiles immune to zone modifier cost changes
  - PATCH 3: MergeFaction purges ALL registry entries for dissolved faction
  - PATCH 4: SplitFaction uses select_nth_unstable_by (compiles, O(N))
  - All existing 111+ tests still pass
Suggested_Test_Commands:
  - "cd micro-core && cargo test directive_executor"
  - "cd micro-core && cargo test engine_override"
  - "cd micro-core && cargo test interaction"
  - "cd micro-core && cargo test movement"
  - "cd micro-core && cargo test flow_field"
```
