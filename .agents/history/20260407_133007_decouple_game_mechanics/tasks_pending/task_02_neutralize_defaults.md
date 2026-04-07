# Task 02: Neutralize All Defaults + Remove Wave Spawn

- **Task_ID:** task_02_neutralize_defaults
- **Execution_Phase:** 1 (parallel with Task 01)
- **Model_Tier:** standard
- **Feature:** Decoupling Game Mechanics

## Target_Files
- `micro-core/src/rules/interaction.rs`
- `micro-core/src/rules/removal.rs`
- `micro-core/src/components/movement_config.rs`
- `micro-core/src/systems/spawning.rs`
- `micro-core/src/systems/mod.rs`

## Dependencies
- None (Phase 1 — no prior tasks required)

## Context_Bindings
- `context/architecture`
- `skills/rust-code-standards`

## Strict_Instructions

### Goal
Neutralize all hardcoded game defaults so the engine does nothing unless externally configured. Remove the wave_spawn_system entirely.

### Step 1: Neutralize InteractionRuleSet Default (V1)

In `micro-core/src/rules/interaction.rs`, replace the `Default` impl:

**After:**
```rust
impl Default for InteractionRuleSet {
    /// Empty ruleset — no combat unless explicitly configured by game profile.
    fn default() -> Self {
        Self { rules: vec![] }
    }
}
```

**Fix tests:**
1. `test_interaction_rule_set_default` → assert `rules.len() == 0`
2. `test_interaction_rule_set_factions` → DELETE (no factions in empty default)
3. `test_interaction_rule_set_serde_roundtrip` → keep but test empty roundtrip
4. ADD new test: `test_interaction_rule_set_explicit_construction` — create rules manually, verify fields

### Step 2: Neutralize RemovalRuleSet Default (V10)

In `micro-core/src/rules/removal.rs`, replace the `Default` impl:

**Before:**
```rust
impl Default for RemovalRuleSet {
    fn default() -> Self {
        Self {
            rules: vec![RemovalRule {
                stat_index: 0,
                threshold: 0.0,
                condition: RemovalCondition::LessOrEqual,
            }],
        }
    }
}
```

**After:**
```rust
impl Default for RemovalRuleSet {
    /// Empty ruleset — no entity removal unless configured by game profile.
    fn default() -> Self {
        Self { rules: vec![] }
    }
}
```

**Fix tests:**
1. `test_removal_rule_set_default` → assert `rules.len() == 0`
2. `test_removal_rule_set_serde_roundtrip` → keep but test empty roundtrip
3. ADD new test: `test_removal_rule_explicit_construction` — build a rule manually, verify fields

### Step 3: Neutralize MovementConfig Default (V2)

In `micro-core/src/components/movement_config.rs`, set all defaults to zero:

```rust
impl Default for MovementConfig {
    /// Zero movement — entities don't move unless configured by game profile.
    fn default() -> Self {
        Self {
            max_speed: 0.0,
            steering_factor: 0.0,
            separation_radius: 0.0,
            separation_weight: 0.0,
            flow_weight: 0.0,
        }
    }
}
```

### Step 4: Remove Wave Spawn System (V8)

**In `micro-core/src/systems/spawning.rs`:**
1. Remove the entire `wave_spawn_system` function
2. Remove the `wave_spawn_system` tests

Keep `initial_spawn_system` for standalone demo.

**In `micro-core/src/systems/mod.rs`:**
Remove `wave_spawn_system` from the `pub use` statement.

### Step 5: Verify

```bash
cd micro-core && cargo test --lib
cd micro-core && cargo clippy
```

> **NOTE:** `main.rs` compile error expected (removed `wave_spawn_system`). Task 03 handles `main.rs`. Use `cargo test --lib` to test library crate only.

## Verification_Strategy
  Test_Type: unit
  Test_Stack: Rust (cargo test)
  Acceptance_Criteria:
    - "InteractionRuleSet::default() returns empty rules vec"
    - "RemovalRuleSet::default() returns empty rules vec"  
    - "MovementConfig::default() returns all zeros"
    - "wave_spawn_system removed from spawning.rs and mod.rs"
    - "All remaining tests pass: `cargo test --lib`"
    - "`cargo clippy` produces no new warnings"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test --lib"
    - "cd micro-core && cargo clippy"
