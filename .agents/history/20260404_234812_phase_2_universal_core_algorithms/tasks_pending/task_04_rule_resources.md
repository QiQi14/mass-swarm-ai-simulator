---
Task_ID: task_04_rule_resources
Execution_Phase: Phase 1 (Parallel)
Model_Tier: basic
Target_Files:
  - micro-core/src/rules/mod.rs
  - micro-core/src/rules/interaction.rs
  - micro-core/src/rules/removal.rs
  - micro-core/src/rules/navigation.rs
  - micro-core/src/rules/behavior.rs
  - micro-core/src/lib.rs
Dependencies:
  - task_01_context_agnostic_refactor
Context_Bindings:
  - context/conventions
  - skills/rust-code-standards
---

# STRICT INSTRUCTIONS

Create all config-driven rule resources for the Universal Core. These are **DATA ONLY — no systems**.

**Read `implementation_plan.md` Contracts 5, 6, 10 AND the deep-dive spec `implementation_plan_task_04.md` for the exact structs, default configs, and unit tests.**

> **CRITICAL:** The spec file `implementation_plan_task_04.md` (project root) contains complete Rust code for all 5 files. Adopt the architecture and contracts — verify correctness before implementation.

## File Structure

### 1. `micro-core/src/rules/mod.rs` [NEW]
Re-export all public types from sub-modules.

### 2. `micro-core/src/rules/interaction.rs` [NEW]
- `InteractionRuleSet` resource with `Vec<InteractionRule>`
- `InteractionRule`: source_faction, target_faction, range, effects
- `StatEffect`: stat_index, delta_per_second
- `RemovalEvents` resource (Contract 6): `Vec<u32>` of removed IDs
- `Default` → swarm demo: faction 0→1 @ -10.0/s, faction 1→0 @ -20.0/s

### 3. `micro-core/src/rules/removal.rs` [NEW]
- `RemovalRuleSet` resource with `Vec<RemovalRule>`
- `RemovalRule`: stat_index, threshold, condition
- `RemovalCondition` enum: LessOrEqual, GreaterOrEqual
- `Default` → stat[0] <= 0.0

### 4. `micro-core/src/rules/navigation.rs` [NEW]
- `NavigationRuleSet` resource with `Vec<NavigationRule>`
- `NavigationRule`: follower_faction, target_faction
- `Default` → follower=0, target=1

### 5. `micro-core/src/rules/behavior.rs` [NEW]
- `FactionBehaviorMode` resource with `HashSet<u32>` static_factions
- `Default` → faction 1 in static_factions

### 6. Update `micro-core/src/lib.rs` [MODIFY]
Add `pub mod rules;` after existing module declarations.

## Unit Tests (10 tests)
- Default InteractionRuleSet: 2 rules, correct factions
- InteractionRuleSet serde roundtrip
- RemovalEvents default empty
- Default RemovalRuleSet: 1 rule, stat_index=0, LessOrEqual
- RemovalCondition variants distinct
- RemovalRuleSet serde roundtrip
- Default NavigationRuleSet: 1 rule, follower=0, target=1
- NavigationRuleSet serde roundtrip
- Default FactionBehaviorMode: faction 1 static, faction 0 not
- FactionBehaviorMode not serializable (no Serialize — uses HashSet)

---

# Verification_Strategy
Test_Type: unit
Test_Stack: cargo test
Acceptance_Criteria:
  - "Default InteractionRuleSet has 2 rules (faction 0→1 and 1→0)"
  - "Default RemovalRuleSet has 1 rule (stat[0] <= 0.0)"
  - "Default NavigationRuleSet has 1 rule (faction 0 → faction 1)"
  - "Default FactionBehaviorMode has faction 1 in static_factions"
  - "All Serialize+Deserialize types survive JSON roundtrip"
  - "RemovalEvents default is empty"
Suggested_Test_Commands:
  - "cd micro-core && cargo test rules"
