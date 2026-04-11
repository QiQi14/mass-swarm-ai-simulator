# Task 03: Interaction System Upgrade

**Task_ID:** `task_03_interaction_system_upgrade`
**Feature:** Heterogeneous Swarm Mechanics
**Execution_Phase:** 2 (Sequential — after T01 and T02)
**Model_Tier:** `advanced`

## Target_Files
- `micro-core/src/systems/interaction.rs` [MODIFY]

## Dependencies
- T01: `UnitClassId` component exists in `crate::components::UnitClassId`
- T02: Expanded `InteractionRule` (with `source_class`, `target_class`, `range_stat_index`, `mitigation`, `cooldown_ticks`), `MitigationRule`, `MitigationMode`, `CooldownTracker`

## Context_Bindings
- `context/engine-mechanics`
- `context/conventions`
- `skills/rust-code-standards`
- `implementation_plan_feature_1.md` (Task 03 section)

## Contract Reference
See `implementation_plan_feature_1.md` → Task 03 for detailed architectural notes.

## Strict_Instructions

### Overview

Upgrade `interaction_system` in `micro-core/src/systems/interaction.rs` to support:
1. **Unit class filtering** (source_class / target_class)
2. **Dynamic range from StatBlock** (range_stat_index)
3. **Stat-driven mitigation** (PercentReduction / FlatReduction)
4. **Per-entity cooldowns** (cooldown_ticks via CooldownTracker)

### 1. Expand Query to Include UnitClassId

Change the read-only query from:
```rust
q_ro: Query<(Entity, &Position, &FactionId, &EntityId)>,
```
to:
```rust
q_ro: Query<(Entity, &Position, &FactionId, &EntityId, &UnitClassId)>,
```

Add import: `use crate::components::UnitClassId;`

### 2. Add CooldownTracker to System Parameters

Add parameter: `mut cooldowns: ResMut<crate::config::CooldownTracker>`

At the **start** of the system (before the entity loop), call `cooldowns.tick()` to decrement all active cooldowns.

### 3. Enumerate Rules with Index

Change:
```rust
for rule in &rules.rules {
```
to:
```rust
for (rule_idx, rule) in rules.rules.iter().enumerate() {
```

### 4. Add Unit Class Filtering (after faction check)

After the `source_faction` check and aggro mask check, add:

```rust
// Unit class filtering — skip if source class doesn't match
if let Some(required_class) = rule.source_class {
    if source_class.0 != required_class {
        continue;
    }
}
```

Where `source_class` is destructured from the expanded `q_ro` tuple: `(source_entity, source_pos, source_faction, source_id, source_class)`.

### 5. Implement Dynamic Range

BEFORE the `grid.query_radius()` call, compute effective range:

```rust
let effective_range = if let Some(stat_idx) = rule.range_stat_index {
    // Read source entity's stat for dynamic range
    // q_rw.get() returns a read-only reference (no mutable borrow)
    q_rw.get(source_entity)
        .ok()
        .and_then(|sb| sb.0.get(stat_idx).copied())
        .unwrap_or(rule.range)
} else {
    rule.range
};
```

Then use `effective_range` in: `grid.query_radius(center, effective_range)`

> **CRITICAL NOTE:** `q_rw.get(entity)` is a READ (shared borrow), not a WRITE. Only `q_rw.get_mut(entity)` takes a mutable borrow. Reading from `Query<&mut StatBlock>` is safe as long as you don't hold the borrow while calling `get_mut()` on the same query.

### 6. Add Target Class Filtering (inside neighbor loop)

After the neighbor faction check, add:

```rust
if let Some(required_class) = rule.target_class {
    if let Ok((_, _, _, _, neighbor_class)) = q_ro.get(neighbor_entity) {
        if neighbor_class.0 != required_class {
            continue;
        }
    }
}
```

Note: the `q_ro.get(neighbor_entity)` already happens — reuse the existing lookup result. Restructure:

```rust
if let Ok((_, _, neighbor_faction, _, neighbor_class)) = q_ro.get(neighbor_entity) {
    if neighbor_faction.0 != rule.target_faction {
        continue;
    }
    if let Some(required_class) = rule.target_class {
        if neighbor_class.0 != required_class {
            continue;
        }
    }
    // ... proceed to effects
}
```

### 7. Implement Cooldown Check

Before applying effects to a neighbor, check cooldown:

```rust
if let Some(cd_ticks) = rule.cooldown_ticks {
    if !cooldowns.can_fire(source_id.id, rule_idx) {
        continue; // Skip this rule for this source entity
    }
}
```

IMPORTANT: The cooldown check should be OUTSIDE the neighbor loop (before it), since cooldowns are per-entity-per-rule, not per-neighbor. If the entity is on cooldown, skip ALL neighbors for this rule.

After processing all neighbors for this rule (at least one hit), start the cooldown:

```rust
// After neighbor loop, if at least one effect was applied:
if let Some(cd_ticks) = rule.cooldown_ticks {
    if applied_any_effect {
        cooldowns.start_cooldown(source_id.id, rule_idx, cd_ticks);
    }
}
```

Use a boolean `applied_any_effect` flag inside the neighbor loop.

### 8. Implement Stat-Driven Mitigation

Inside the effect application block, compute the mitigated delta:

```rust
for effect in &rule.effects {
    if effect.stat_index < stat_block.0.len() {
        // Compute mitigated delta
        let base_delta = effect.delta_per_second * tick_delta * damage_mult;
        let final_delta = if let Some(ref mit) = rule.mitigation {
            // Read mitigation stat from target BEFORE get_mut
            let mit_value = q_rw.get(neighbor_entity)
                .ok()
                .and_then(|sb| sb.0.get(mit.stat_index).copied())
                .unwrap_or(0.0);
            match mit.mode {
                crate::rules::MitigationMode::PercentReduction => {
                    base_delta * (1.0 - mit_value.clamp(0.0, 1.0))
                }
                crate::rules::MitigationMode::FlatReduction => {
                    let abs_reduced = (base_delta.abs() - mit_value).max(0.0);
                    abs_reduced * base_delta.signum()
                }
            }
        } else {
            base_delta
        };

        if let Ok(mut stat_block) = q_rw.get_mut(neighbor_entity) {
            stat_block.0[effect.stat_index] += final_delta;
            applied_any_effect = true;
        }
    }
}
```

**IMPORTANT BORROW PATTERN:** Read mitigation stat via `q_rw.get()` (shared borrow, released), THEN write via `q_rw.get_mut()`. Don't hold both simultaneously.

### 9. Update ALL Existing Tests

All existing tests spawn entities WITHOUT `UnitClassId`. You MUST add `UnitClassId::default()` to every entity spawn in the test module. Also add `CooldownTracker` resource:

```rust
fn setup_app() -> App {
    let mut app = App::new();
    // ... existing resources ...
    app.init_resource::<crate::config::CooldownTracker>();  // NEW
    app.add_systems(Update, interaction_system);
    app
}
```

And in spawns:
```rust
app.world_mut().spawn((
    EntityId { id: 1 },
    Position { x: 0.0, y: 0.0 },
    FactionId(0),
    StatBlock::with_defaults(&[(0, 100.0)]),
    UnitClassId::default(),  // NEW
))
```

### 10. Add New Tests

Add these tests (use `setup_app()` helper):

- **`test_class_filtering_source`** — Rule with `source_class: Some(1)`. Spawn source as class 0, target as class 0. Verify NO damage. Then spawn source as class 1. Verify damage applied.

- **`test_class_filtering_target`** — Rule with `target_class: Some(2)`. Spawn target as class 0. Verify NO damage. Spawn target as class 2. Verify damage.

- **`test_dynamic_range`** — Rule with `range_stat_index: Some(3)`, `range: 10.0`. Spawn source with `stat[3] = 50.0`. Place target at distance 30 (out of fixed range 10, but in dynamic range 50). Verify damage applied.

- **`test_mitigation_percent`** — Rule with mitigation `PercentReduction` on `stat_index: 4`. Target has `stat[4] = 0.5`. Verify damage reduced by 50%.

- **`test_mitigation_flat`** — Rule with mitigation `FlatReduction` on `stat_index: 4`. Target has `stat[4] = 5.0`. Base damage = 10.0/sec. Verify effective damage = 5.0/sec.

- **`test_cooldown_prevents_rapid_fire`** — Rule with `cooldown_ticks: Some(60)`. Verify: frame 1 = damage applied, frames 2-60 = no damage, frame 61 = damage applied again.

- **`test_backward_compat_no_new_fields`** — Rule with all new fields as `None`. Verify identical behavior to existing tests (no class filter, no dynamic range, no mitigation, no cooldown).

## Anti-Patterns
- ❌ Do NOT use `unsafe` for query conflicts — use Bevy's disjoint query + careful borrow scoping
- ❌ Do NOT allocate Vec/HashMap inside the hot loop — O(1) HashMap lookups only
- ❌ Do NOT break the O(N×R×K) performance — cooldown is O(1) HashMap lookup
- ❌ Do NOT modify any other files — this task only touches `interaction.rs`

## Verification_Strategy

```yaml
Test_Type: unit + integration
Test_Stack: cargo test (Rust)
Acceptance_Criteria:
  - "All 4 existing interaction tests pass unchanged"
  - "Class filtering correctly skips non-matching entities"
  - "Dynamic range reads from StatBlock correctly"
  - "Mitigation reduces damage correctly for both PercentReduction and FlatReduction"
  - "Cooldown prevents rapid-fire and expires correctly"
  - "Backward compat: rules with no new fields behave identically to before"
  - "cargo test (full suite) passes — no regressions"
Suggested_Test_Commands:
  - "cd micro-core && cargo test systems::interaction -- --nocapture"
  - "cd micro-core && cargo test"
```
