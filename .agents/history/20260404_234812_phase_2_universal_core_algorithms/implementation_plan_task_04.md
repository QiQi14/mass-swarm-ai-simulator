# Task 04 — Rule Resources (Full Specification)

> **Parent Plan:** [`implementation_plan.md`](./implementation_plan.md) → Contracts 5, 6, 10
> **This file:** Exhaustive spec for the Executor agent.

**Phase:** 1 (Parallel) | **Tier:** `basic` | **Domain:** Data Model  
**Target Files:** `rules/mod.rs` [NEW], `rules/interaction.rs` [NEW], `rules/removal.rs` [NEW], `rules/navigation.rs` [NEW], `rules/behavior.rs` [NEW], `lib.rs` [MODIFY]  
**Dependencies:** Task 01 (only for `FactionId` concept — no code dependency)  
**Context Bindings:** `context/conventions`, `skills/rust-code-standards`

---

## 1. Overview

This task creates **DATA ONLY** resources — no systems, no algorithms. These are config-driven rule sets that the Interaction System (Task 05) and Movement System (Task 06) will read.

The Micro-Core is context-agnostic: it processes numeric faction IDs and stat indices. The meaning of "faction 0 = swarm" or "stat[0] = health" is defined by the adapter layer, not here.

---

## 2. Full Rust Implementation

### 2.1 `micro-core/src/rules/mod.rs` [NEW]

```rust
//! # Rule Resources
//!
//! Config-driven rule sets for interactions, removals, navigation, and behavior.
//! These are DATA ONLY — no systems.
//!
//! ## Ownership
//! - **Task:** task_04_rule_resources
//! - **Contract:** implementation_plan.md → Contracts 5, 6, 10

pub mod interaction;
pub mod removal;
pub mod navigation;
pub mod behavior;

pub use interaction::{InteractionRuleSet, InteractionRule, StatEffect, RemovalEvents};
pub use removal::{RemovalRuleSet, RemovalRule, RemovalCondition};
pub use navigation::{NavigationRuleSet, NavigationRule};
pub use behavior::FactionBehaviorMode;
```

### 2.2 `micro-core/src/rules/interaction.rs` [NEW]

```rust
//! # Interaction Rules
//!
//! Defines what happens when entities of different factions are in proximity.
//! Loaded from config — zero hardcoded game logic.
//!
//! ## Ownership
//! - **Task:** task_04_rule_resources
//! - **Contract:** implementation_plan.md → Contract 5

use bevy::prelude::*;
use serde::{Deserialize, Serialize};

/// Config-driven interaction rules. Each rule defines source→target faction
/// proximity effects on the target's StatBlock.
#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct InteractionRuleSet {
    pub rules: Vec<InteractionRule>,
}

/// A single interaction rule: when source_faction entity is within range
/// of target_faction entity, apply effects to target's StatBlock.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InteractionRule {
    /// Faction ID of the entity causing the interaction.
    pub source_faction: u32,
    /// Faction ID of the entity receiving the effects.
    pub target_faction: u32,
    /// Range in world units at which this interaction activates.
    pub range: f32,
    /// Effects to apply to the TARGET entity's StatBlock.
    pub effects: Vec<StatEffect>,
}

/// A single stat modification. Applied to target entity per tick.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StatEffect {
    /// Index into the target's StatBlock array.
    pub stat_index: usize,
    /// Change per second. Negative = damage, positive = heal/buff.
    /// Normalized to per-tick by the interaction system: `delta * (1.0/60.0)`.
    pub delta_per_second: f32,
}

/// Accumulates entity IDs removed this tick for WebSocket broadcast.
/// Cleared at the start of each tick by the removal system.
#[derive(Resource, Debug, Default)]
pub struct RemovalEvents {
    pub removed_ids: Vec<u32>,
}

impl Default for InteractionRuleSet {
    /// Swarm demo default config:
    /// - Rule 1: faction 0 damages faction 1 at -10.0/sec (stat[0])
    /// - Rule 2: faction 1 damages faction 0 at -20.0/sec (stat[0])
    fn default() -> Self {
        Self {
            rules: vec![
                InteractionRule {
                    source_faction: 0,
                    target_faction: 1,
                    range: 15.0,
                    effects: vec![StatEffect { stat_index: 0, delta_per_second: -10.0 }],
                },
                InteractionRule {
                    source_faction: 1,
                    target_faction: 0,
                    range: 15.0,
                    effects: vec![StatEffect { stat_index: 0, delta_per_second: -20.0 }],
                },
            ],
        }
    }
}
```

### 2.3 `micro-core/src/rules/removal.rs` [NEW]

```rust
//! # Removal Rules
//!
//! Defines when entities are removed from simulation based on stat thresholds.
//!
//! ## Ownership
//! - **Task:** task_04_rule_resources
//! - **Contract:** implementation_plan.md → Contract 5

use bevy::prelude::*;
use serde::{Deserialize, Serialize};

/// Config-driven removal rules. Checked each tick by the removal system.
#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct RemovalRuleSet {
    pub rules: Vec<RemovalRule>,
}

/// A single removal rule: remove entity when stat[index] crosses threshold.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RemovalRule {
    /// Which stat index to monitor.
    pub stat_index: usize,
    /// Threshold value for removal.
    pub threshold: f32,
    /// Direction of comparison.
    pub condition: RemovalCondition,
}

/// Direction of threshold comparison for removal.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum RemovalCondition {
    /// Remove when stat <= threshold (e.g., "health" drops to 0).
    LessOrEqual,
    /// Remove when stat >= threshold (e.g., "corruption" reaches 100).
    GreaterOrEqual,
}

impl Default for RemovalRuleSet {
    /// Swarm demo default: remove when stat[0] (health) <= 0.0.
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

### 2.4 `micro-core/src/rules/navigation.rs` [NEW]

```rust
//! # Navigation Rules
//!
//! Defines which factions navigate toward which factions via flow fields.
//!
//! ## Ownership
//! - **Task:** task_04_rule_resources
//! - **Contract:** implementation_plan.md → Contract 5

use bevy::prelude::*;
use serde::{Deserialize, Serialize};

/// Config-driven navigation matrix. The flow_field_update_system reads this
/// to decide which flow fields to calculate and which factions use them.
#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct NavigationRuleSet {
    pub rules: Vec<NavigationRule>,
}

/// A single navigation rule: follower_faction follows flow field toward target_faction.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NavigationRule {
    /// Faction ID of entities that will follow the flow field.
    pub follower_faction: u32,
    /// Faction ID of entities used as goals (flow field converges on them).
    pub target_faction: u32,
}

impl Default for NavigationRuleSet {
    /// Swarm demo default: faction 0 navigates toward faction 1.
    fn default() -> Self {
        Self {
            rules: vec![NavigationRule {
                follower_faction: 0,
                target_faction: 1,
            }],
        }
    }
}
```

### 2.5 `micro-core/src/rules/behavior.rs` [NEW]

```rust
//! # Faction Behavior Mode
//!
//! Runtime-toggleable per-faction behavior: static (random drift) vs brain-driven.
//!
//! ## Ownership
//! - **Task:** task_04_rule_resources
//! - **Contract:** implementation_plan.md → Contract 10

use bevy::prelude::*;
use std::collections::HashSet;

/// Controls per-faction behavior mode at runtime.
/// Factions in `static_factions` use random drift (Phase 1 behavior).
/// All other factions follow NavigationRuleSet flow fields (brain-driven).
///
/// Toggleable via Debug Visualizer: `set_faction_mode` WS command.
#[derive(Resource, Debug, Clone)]
pub struct FactionBehaviorMode {
    /// Set of faction IDs currently in "static" mode (random drift).
    /// Factions NOT in this set follow flow fields.
    pub static_factions: HashSet<u32>,
}

impl Default for FactionBehaviorMode {
    /// Swarm demo default: faction 1 (defenders) starts in static mode.
    fn default() -> Self {
        let mut static_factions = HashSet::new();
        static_factions.insert(1);
        Self { static_factions }
    }
}
```

### 2.6 `micro-core/src/lib.rs` [MODIFY]

Add `pub mod rules;` after existing module declarations.

---

## 3. Unit Tests

Each file should contain its own `#[cfg(test)] mod tests { ... }`:

- **InteractionRuleSet::default()** — has 2 rules (faction 0→1 and 1→0)
- **InteractionRuleSet source/target factions** — rule[0]: source=0, target=1; rule[1]: source=1, target=0
- **InteractionRuleSet serde roundtrip** — JSON serialize→deserialize preserves all fields
- **RemovalEvents::default()** — `removed_ids` is empty
- **RemovalRuleSet::default()** — 1 rule, stat_index=0, condition=LessOrEqual
- **RemovalCondition variants** — LessOrEqual ≠ GreaterOrEqual
- **RemovalRuleSet serde roundtrip** — JSON preserve
- **NavigationRuleSet::default()** — 1 rule, follower=0, target=1
- **NavigationRuleSet serde roundtrip** — JSON preserve
- **FactionBehaviorMode::default()** — faction 1 in static_factions, faction 0 NOT

---

## 4. Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: unit
  Test_Stack: cargo test
  Acceptance_Criteria:
    - "Default InteractionRuleSet has 2 rules (faction 0→1 and 1→0)"
    - "Default RemovalRuleSet has 1 rule (stat[0] <= 0.0)"
    - "Default NavigationRuleSet has 1 rule (faction 0 → faction 1)"
    - "Default FactionBehaviorMode has faction 1 in static_factions"
    - "All rule types survive JSON serialization roundtrip"
    - "RemovalEvents default is empty"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test rules"
```
