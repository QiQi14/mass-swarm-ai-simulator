# Task R4: Split `config.rs` + Doc Tests

- **Task_ID:** task_r4_split_config_doctests
- **Execution_Phase:** 1 (parallel)
- **Model_Tier:** standard
- **Feature:** File Splitting Refactor

## Target_Files
- `micro-core/src/config.rs` → DELETE (becomes directory)
- `micro-core/src/config/mod.rs` [NEW]
- `micro-core/src/config/simulation.rs` [NEW]
- `micro-core/src/config/buff.rs` [NEW]
- `micro-core/src/config/zones.rs` [NEW]
- `micro-core/src/lib.rs` (update `mod config` if needed)

## Dependencies
- None (Phase 1)

## Context_Bindings
- `context/conventions`
- `skills/rust-code-standards` (Part 2.8: Doc Tests, Part 4: File Organization)

## Strict_Instructions

### Goal
Split `config.rs` (301 lines) into 3 files AND migrate pure function tests to doc tests. **Pure refactor for the split, doc test migration for test reduction.**

### Step 1: Create `simulation.rs`

Move:
- `SimulationConfig` struct + `Default` impl
- `TickCounter` struct
- `SimPaused` struct
- `SimSpeed` struct + `Default` impl
- `SimStepRemaining` struct

### Step 2: Create `buff.rs`

Move:
- `BuffConfig` struct
- `FactionBuffs` struct + `impl FactionBuffs` (get_multiplier, get_flat_add)
- `ActiveBuffGroup` struct + `impl ActiveBuffGroup` (targets_entity)
- `ActiveModifier` struct
- `ModifierType` enum
- `DensityConfig` struct + `Default` impl

**Doc test migration:** Add `/// # Examples` to these functions. Move corresponding `#[cfg(test)]` tests into doc tests:

```rust
/// Get the cumulative multiplier for a specific stat, respecting entity targeting.
///
/// Returns `1.0` if no active multiplier buff targets this entity.
///
/// # Examples
///
/// ```
/// use micro_core::config::{FactionBuffs, ActiveBuffGroup, ActiveModifier, ModifierType};
///
/// let mut buffs = FactionBuffs::default();
/// assert!((buffs.get_multiplier(0, 1, 0) - 1.0).abs() < f32::EPSILON);
///
/// buffs.buffs.insert(0, vec![ActiveBuffGroup {
///     modifiers: vec![ActiveModifier {
///         stat_index: 0,
///         modifier_type: ModifierType::Multiplier,
///         value: 1.5,
///     }],
///     remaining_ticks: 60,
///     targets: Some(vec![]),
/// }]);
/// assert!((buffs.get_multiplier(0, 1, 0) - 1.5).abs() < f32::EPSILON);
/// ```
pub fn get_multiplier(&self, faction: u32, entity_id: u32, stat_index: usize) -> f32 {
```

Similarly for `get_flat_add` and `targets_entity`.

### Step 3: Create `zones.rs`

Move:
- `ActiveZoneModifiers` struct
- `ZoneModifier` struct
- `InterventionTracker` struct
- `AggroMaskRegistry` struct + `impl` (is_combat_allowed)
- `ActiveSubFactions` struct

**Doc test for `is_combat_allowed`:**
```rust
/// # Examples
///
/// ```
/// use micro_core::config::AggroMaskRegistry;
///
/// let reg = AggroMaskRegistry::default();
/// assert!(reg.is_combat_allowed(0, 1)); // default: all pairs allowed
/// ```
```

### Step 4: Create `mod.rs`

```rust
//! # Configuration Resources
//!
//! Bevy ECS resources for simulation configuration, buff system, and zone modifiers.
//! All resources are injected at startup or via ZMQ ResetEnvironment.

mod simulation;
mod buff;
mod zones;

pub use simulation::*;
pub use buff::*;
pub use zones::*;
```

### Step 5: Delete original `config.rs`

### Step 6: Verify

```bash
cd micro-core && cargo test config && cargo test --doc && cargo clippy
```

**Critical:** `cargo test --doc` must pass — this validates all new doc test examples compile and execute correctly.

## Verification_Strategy
  Test_Type: unit
  Test_Stack: Rust (cargo test + cargo test --doc)
  Acceptance_Criteria:
    - "All existing tests pass"
    - "Doc tests pass (cargo test --doc)"
    - "Each file under 200 lines"
    - "External imports unchanged (pub use re-exports)"
    - "At least 4 functions have doc test examples"
    - "cargo clippy clean"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test config && cargo test --doc && cargo clippy"
