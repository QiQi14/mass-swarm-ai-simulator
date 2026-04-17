# Task B1: Rust Directives + FactionTacticalOverrides Resource

- **Task_ID:** `B1_rust_directives`
- **Execution_Phase:** 1 (Brain Phase B)
- **Model_Tier:** `advanced`
- **Live_System_Impact:** `destructive` — modifies directive enum + executor

## Target_Files
- `micro-core/src/bridges/zmq_protocol/directives.rs` — MODIFY
- `micro-core/src/systems/directive_executor/executor.rs` — MODIFY
- `micro-core/src/config/tactical_overrides.rs` — NEW
- `micro-core/src/config/mod.rs` — MODIFY (add `pub mod tactical_overrides;`)
- `micro-core/src/main.rs` — MODIFY (init resource)
- `micro-core/src/bridges/zmq_bridge/reset.rs` — MODIFY (clear on reset)

## Dependencies
- None (first task in Brain Phase B)

## Context_Bindings
- `strategy_brief.md` — §Engine Capability Inventory, §Action Space v3
- `research_digest.md` — §SplitFaction, §TacticalBehavior, §Integration Points (Fix 2 + Fix 3)
- `implementation_plan_brain_v3.md` — Contracts 1, 2
- `.agents/skills/rust-code-standards/SKILL.md`

## Strict_Instructions

### 1. Add `class_filter` to SplitFaction (directives.rs)

Add `class_filter: Option<u32>` with `#[serde(default)]` to the `SplitFaction` variant:

```rust
SplitFaction {
    source_faction: u32,
    new_sub_faction: u32,
    percentage: f32,
    epicenter: [f32; 2],
    #[serde(default)]
    class_filter: Option<u32>,  // None = all classes, Some(id) = only class_id
}
```

### 2. Add SetTacticalOverride variant (directives.rs)

```rust
SetTacticalOverride {
    faction: u32,
    behavior: Option<TacticalBehaviorPayload>,  // None = clear override
}
```

The `TacticalBehaviorPayload` enum already exists in `zmq_protocol/payloads.rs` — verify it has `Kite { trigger_radius, weight }` and `PeelForAlly { ... }` variants. Use `#[serde(tag = "type")]` for JSON discrimination.

### 3. Create FactionTacticalOverrides resource (config/tactical_overrides.rs)

```rust
use bevy_ecs::prelude::*;
use std::collections::HashMap;
use crate::config::unit_registry::TacticalBehavior;

#[derive(Resource, Default, Debug)]
pub struct FactionTacticalOverrides {
    pub overrides: HashMap<u32, Vec<TacticalBehavior>>,
}
```

Register in `config/mod.rs`: `pub mod tactical_overrides;`

### 4. Handle class_filter in SplitFaction executor (executor.rs)

The current `faction_query` is `Query<(Entity, &Position, &mut FactionId)>`. Add `&UnitClassId` to the query:

```rust
// Updated query tuple:
Query<(Entity, &Position, &mut FactionId, &UnitClassId)>
```

In the SplitFaction handler, filter candidates by class:

```rust
.filter(|(_, _, f, class_id)| {
    f.0 == source_faction
        && class_filter.map_or(true, |cf| class_id.0 == cf)
})
```

**Verify** that all other directive handlers using `faction_query` are compatible (MergeFaction, Retreat). They should destructure with `(entity, _, faction, _)` — the extra `&UnitClassId` is ignored.

### 5. Handle SetTacticalOverride in executor (executor.rs)

Add a new match arm:

```rust
MacroDirective::SetTacticalOverride { faction, behavior } => {
    match behavior {
        Some(payload) => {
            let behaviors = payload_to_tactical_behaviors(payload);
            tactical_overrides.overrides.insert(faction, behaviors);
        }
        None => {
            tactical_overrides.overrides.remove(&faction);
        }
    }
}
```

You'll need to convert `TacticalBehaviorPayload` → `Vec<TacticalBehavior>`. The conversion already exists in `zmq_bridge` for spawn configs — find and reuse the pattern.

Add `ResMut<FactionTacticalOverrides>` to the executor system params.

### 6. MergeFaction cleanup (executor.rs)

In the `MergeFaction` handler block (after removing nav_rules, zones, buffs, aggro, interaction_rules), add:

```rust
tactical_overrides.overrides.remove(&source_faction);
```

### 7. ResetEnvironment cleanup (reset.rs)

In reset handler, clear all overrides:

```rust
tactical_overrides.overrides.clear();
```

### 8. Init resource (main.rs)

Add to the app builder:

```rust
.init_resource::<FactionTacticalOverrides>()
```

## Verification_Strategy
```
Test_Type: unit + compilation
Acceptance_Criteria:
  - "SplitFaction with class_filter: null splits all classes (backward compat)"
  - "SplitFaction with class_filter: 1 only splits entities with UnitClassId(1)"
  - "SetTacticalOverride with behavior: Kite inserts into FactionTacticalOverrides"
  - "SetTacticalOverride with behavior: null removes from FactionTacticalOverrides"
  - "MergeFaction removes tactical overrides for source faction"
  - "ResetEnvironment clears all tactical overrides"
  - "cargo check passes"
  - "cargo test passes (all 251+ tests)"
  - "cargo clippy clean"
Suggested_Test_Commands:
  - "cd micro-core && cargo check"
  - "cd micro-core && cargo test"
  - "cd micro-core && cargo clippy -- -D warnings"
```
