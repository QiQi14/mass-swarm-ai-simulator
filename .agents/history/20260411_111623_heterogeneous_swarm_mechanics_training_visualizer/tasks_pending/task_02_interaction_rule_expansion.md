# Task 02: InteractionRule Expansion + CooldownTracker

**Task_ID:** `task_02_interaction_rule_expansion`
**Feature:** Heterogeneous Swarm Mechanics
**Execution_Phase:** 1 (Parallel)
**Model_Tier:** `standard`

## Target_Files
- `micro-core/src/rules/interaction.rs` [MODIFY]
- `micro-core/src/config/cooldown.rs` [NEW]
- `micro-core/src/config/mod.rs` [MODIFY]

## Dependencies
None

## Context_Bindings
- `context/engine-mechanics`
- `skills/rust-code-standards`

## Contract Reference
See `implementation_plan.md` → Contracts C2 and C3 for the exact type definitions.

## Strict_Instructions

### 1. Add New Types to `micro-core/src/rules/interaction.rs`

Add these new types AFTER the existing `StatEffect` struct:

```rust
/// Stat-driven damage mitigation applied to the TARGET entity.
/// The engine doesn't know what "armor" or "shield" means — it just math.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct MitigationRule {
    /// Stat index on the TARGET entity providing mitigation value.
    pub stat_index: usize,
    /// How mitigation is applied to damage.
    pub mode: MitigationMode,
}

/// How damage mitigation math is computed.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum MitigationMode {
    /// damage = base_damage * (1.0 - target_stat.clamp(0.0, 1.0))
    /// Example: stat=0.3 → 30% damage reduction
    PercentReduction,
    /// damage = (base_damage.abs() - target_stat).max(0.0) * base_damage.signum()
    /// Example: stat=10.0 → 10 flat damage absorbed
    FlatReduction,
}
```

### 2. Expand `InteractionRule` Struct

Add the following fields to the existing `InteractionRule` struct, AFTER the existing `effects` field. All new fields MUST have `#[serde(default)]` for backward compatibility:

```rust
/// Filter: only apply this rule when the SOURCE entity has this class.
/// None = any class (backward compatible default).
#[serde(default)]
pub source_class: Option<u32>,

/// Filter: only apply this rule when the TARGET entity has this class.
/// None = any class (backward compatible default).
#[serde(default)]
pub target_class: Option<u32>,

/// If set, use the SOURCE entity's StatBlock[idx] as the combat range
/// instead of the fixed `range` field. Falls back to `range` if stat is missing.
#[serde(default)]
pub range_stat_index: Option<usize>,

/// Optional stat-driven damage mitigation on the TARGET.
#[serde(default)]
pub mitigation: Option<MitigationRule>,

/// If set, each source entity can only fire this rule every N ticks.
/// Tracked by `CooldownTracker` resource.
#[serde(default)]
pub cooldown_ticks: Option<u32>,
```

### 3. Update Existing Tests

The existing tests in `interaction.rs` construct `InteractionRule` structs. You MUST update them to include the 5 new fields (all set to `None`), or use struct update syntax `..Default::default()`. Since `InteractionRule` does not derive `Default`, you must add the fields explicitly.

**IMPORTANT:** The struct does NOT derive `Default`. Do not add `Default` — it would require a default `range` which doesn't make semantic sense. Instead, update each test's construction explicitly.

### 4. Add New Tests for MitigationRule

- `test_mitigation_rule_serde_roundtrip` — test both `PercentReduction` and `FlatReduction` survive JSON roundtrip
- `test_interaction_rule_backward_compat` — create a rule from legacy JSON (no new fields) and verify it deserializes with all new fields as `None`

### 5. Create `micro-core/src/config/cooldown.rs`

```rust
//! # Cooldown Tracker
//!
//! Per-entity, per-rule cooldown tracking for interaction rules with cooldown_ticks.
//! The engine doesn't know what the cooldown represents — just a tick counter.
//!
//! ## Ownership
//! - **Task:** task_02_interaction_rule_expansion
//! - **Contract:** implementation_plan.md → Contract C3
//!
//! ## Depends On
//! - None

use bevy::prelude::*;
use std::collections::HashMap;

/// Tracks interaction cooldowns per entity per rule.
///
/// Key: (entity_id: u32, rule_index: usize)
/// Value: ticks remaining before this entity can fire this rule again.
///
/// Cleared on environment reset. Ticked each frame by interaction_system.
#[derive(Resource, Debug, Default)]
pub struct CooldownTracker {
    pub cooldowns: HashMap<(u32, usize), u32>,
}

impl CooldownTracker {
    /// Decrement all active cooldowns by 1 tick. Remove expired entries.
    pub fn tick(&mut self) {
        self.cooldowns.retain(|_, ticks| {
            *ticks = ticks.saturating_sub(1);
            *ticks > 0
        });
    }

    /// Check if an entity can fire a specific rule (not on cooldown).
    pub fn can_fire(&self, entity_id: u32, rule_index: usize) -> bool {
        !self.cooldowns.contains_key(&(entity_id, rule_index))
    }

    /// Start cooldown for an entity-rule pair.
    pub fn start_cooldown(&mut self, entity_id: u32, rule_index: usize, ticks: u32) {
        if ticks > 0 {
            self.cooldowns.insert((entity_id, rule_index), ticks);
        }
    }

    /// Remove all cooldowns for a specific entity (called on entity despawn).
    pub fn remove_entity(&mut self, entity_id: u32) {
        self.cooldowns.retain(|&(eid, _), _| eid != entity_id);
    }
}
```

### 6. Add Tests for CooldownTracker

- `test_cooldown_tracker_default` — empty by default
- `test_cooldown_tick_decrements` — start cooldown of 3, tick 3 times, verify removed
- `test_cooldown_can_fire` — verify `can_fire` returns false during cooldown, true after expiry
- `test_cooldown_remove_entity` — verify entity-specific cleanup

### 7. Modify `micro-core/src/config/mod.rs`

Add:
```rust
pub mod cooldown;
```
And add to re-exports:
```rust
pub use cooldown::CooldownTracker;
```

## Anti-Patterns
- ❌ Do NOT add `UnitClassId` to any structs — that's T01's scope
- ❌ Do NOT modify `interaction_system` — that's T03's scope
- ❌ Do NOT use strings for `MitigationMode` — use proper Rust enum with serde derive
- ❌ Do NOT derive `Default` on `InteractionRule` — a default range of 0.0 is semantically wrong

## Verification_Strategy

```yaml
Test_Type: unit
Test_Stack: cargo test (Rust)
Acceptance_Criteria:
  - "InteractionRule with all new fields set to None deserializes identically to legacy JSON format"
  - "MitigationRule serde roundtrip works for both PercentReduction and FlatReduction"
  - "CooldownTracker.tick() decrements and removes expired entries"
  - "CooldownTracker.can_fire() returns true when not on cooldown, false during cooldown"
  - "CooldownTracker.start_cooldown() prevents firing for exactly N ticks"
  - "CooldownTracker.remove_entity() clears only that entity's cooldowns"
  - "cargo test (full suite) still passes — no regressions"
Suggested_Test_Commands:
  - "cd micro-core && cargo test rules::interaction"
  - "cd micro-core && cargo test config::cooldown"
  - "cd micro-core && cargo test"
```
