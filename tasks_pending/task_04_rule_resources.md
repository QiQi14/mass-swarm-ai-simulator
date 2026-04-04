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

Create all config-driven rule resources for the Universal Core. These are DATA ONLY — no systems.

**Read `implementation_plan.md` Contracts 5, 6, and 10 for exact structs.**

## 1. Create `micro-core/src/rules/mod.rs` [NEW]

Re-export all public types from sub-modules:
```rust
pub mod interaction;
pub mod removal;
pub mod navigation;
pub mod behavior;

pub use interaction::{InteractionRuleSet, InteractionRule, StatEffect, RemovalEvents};
pub use removal::{RemovalRuleSet, RemovalRule, RemovalCondition};
pub use navigation::{NavigationRuleSet, NavigationRule};
pub use behavior::FactionBehaviorMode;
```

## 2. Create `micro-core/src/rules/interaction.rs` [NEW]

```rust
use bevy::prelude::*;
use serde::{Deserialize, Serialize};

#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct InteractionRuleSet {
    pub rules: Vec<InteractionRule>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InteractionRule {
    pub source_faction: u32,
    pub target_faction: u32,
    pub range: f32,
    pub effects: Vec<StatEffect>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StatEffect {
    pub stat_index: usize,
    pub delta_per_second: f32,
}

/// Accumulates entity IDs removed this tick for WS broadcast.
#[derive(Resource, Debug, Default)]
pub struct RemovalEvents {
    pub removed_ids: Vec<u32>,
}
```

Implement `Default` for `InteractionRuleSet` — swarm demo config:
- Rule 1: source=0, target=1, range=15.0, effects=`[(stat_index: 0, delta_per_second: -10.0)]`
- Rule 2: source=1, target=0, range=15.0, effects=`[(stat_index: 0, delta_per_second: -20.0)]`

## 3. Create `micro-core/src/rules/removal.rs` [NEW]

```rust
use bevy::prelude::*;
use serde::{Deserialize, Serialize};

#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct RemovalRuleSet {
    pub rules: Vec<RemovalRule>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RemovalRule {
    pub stat_index: usize,
    pub threshold: f32,
    pub condition: RemovalCondition,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum RemovalCondition {
    LessOrEqual,
    GreaterOrEqual,
}
```

Implement `Default` for `RemovalRuleSet`:
- Rule 1: stat_index=0, threshold=0.0, condition=LessOrEqual

## 4. Create `micro-core/src/rules/navigation.rs` [NEW]

```rust
use bevy::prelude::*;
use serde::{Deserialize, Serialize};

#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct NavigationRuleSet {
    pub rules: Vec<NavigationRule>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NavigationRule {
    pub follower_faction: u32,
    pub target_faction: u32,
}
```

Implement `Default`: one rule `{ follower_faction: 0, target_faction: 1 }`.

## 5. Create `micro-core/src/rules/behavior.rs` [NEW]

```rust
use bevy::prelude::*;
use std::collections::HashSet;

#[derive(Resource, Debug, Clone)]
pub struct FactionBehaviorMode {
    pub static_factions: HashSet<u32>,
}

impl Default for FactionBehaviorMode {
    fn default() -> Self {
        let mut static_factions = HashSet::new();
        static_factions.insert(1); // Defenders start static
        Self { static_factions }
    }
}
```

## 6. Update `micro-core/src/lib.rs` [MODIFY]

Add `pub mod rules;` after existing module declarations.

## 7. Unit Tests

For each resource:
- Default has expected number of rules/entries.
- Serialization roundtrip (JSON) preserves all fields for Serialize+Deserialize types.
- `RemovalCondition` enum covers both variants.
- `FactionBehaviorMode::default()` has faction 1 in `static_factions`.
- `NavigationRuleSet::default()` has exactly 1 rule with follower=0, target=1.

---

# Verification_Strategy
Test_Type: unit
Test_Stack: cargo test
Acceptance_Criteria:
  - "Default InteractionRuleSet has 2 rules (faction 0→1 and 1→0)"
  - "Default RemovalRuleSet has 1 rule (stat[0] <= 0.0)"
  - "Default NavigationRuleSet has 1 rule (faction 0 → faction 1)"
  - "Default FactionBehaviorMode has faction 1 in static_factions"
  - "All rule types survive JSON serialization roundtrip"
Suggested_Test_Commands:
  - "cd micro-core && cargo test rules"
