---
Task_ID: task_05_interaction_removal_systems
Execution_Phase: Phase 2 (Parallel)
Model_Tier: standard
Target_Files:
  - micro-core/src/systems/interaction.rs
  - micro-core/src/systems/removal.rs
Dependencies:
  - task_02_spatial_hash_grid
  - task_04_rule_resources
Context_Bindings:
  - context/conventions
  - context/architecture
  - skills/rust-code-standards
---

# STRICT INSTRUCTIONS

Implement the generic Interaction System and Removal System. These are config-driven — they process rules, not hardcoded game logic.

**Read `implementation_plan.md` Contracts 5, 6, and 7 for signatures.**

**DO NOT modify `systems/mod.rs` — Task 08 handles wiring.**

## 1. Create `micro-core/src/systems/interaction.rs` [NEW]

```rust
pub fn interaction_system(
    grid: Res<SpatialHashGrid>,
    rules: Res<InteractionRuleSet>,
    mut query: Query<(Entity, &Position, &mut StatBlock, &FactionId)>,
)
```

Algorithm:
1. **First pass (collect):** For each entity, check its faction against all `InteractionRule.source_faction` matches. For matching rules, query `grid.query_radius(entity.position, rule.range)`. For each neighbor in range with matching `target_faction`, accumulate stat modifications into a `HashMap<Entity, Vec<(usize, f32)>>`. Delta per tick = `effect.delta_per_second / 60.0`.
2. **Second pass (apply):** Iterate the collected modifications. For each entity, apply all accumulated stat changes to its `StatBlock`.

> **Why two passes?** Bevy does not allow mutable and immutable access to the same query simultaneously. The collect→apply pattern avoids borrow conflicts.

**Important:** The entity querying its neighbors must NOT affect itself (skip if neighbor entity == self).

## 2. Create `micro-core/src/systems/removal.rs` [NEW]

```rust
pub fn removal_system(
    rules: Res<RemovalRuleSet>,
    query: Query<(Entity, &EntityId, &StatBlock)>,
    mut commands: Commands,
    mut events: ResMut<RemovalEvents>,
)
```

Algorithm:
1. Clear `events.removed_ids` at the start of each tick.
2. For each entity with a `StatBlock`:
   - For each `RemovalRule`: check the stat at `rule.stat_index`.
   - If `condition == LessOrEqual` and `stat <= threshold`, OR `condition == GreaterOrEqual` and `stat >= threshold`:
     - Push `entity_id.id` into `events.removed_ids`.
     - Despawn the entity via `commands.entity(entity).despawn()`.
     - Break (don't process more rules for this entity).

## 3. Unit Tests

### Interaction Tests:
- **Two enemies in range:** Spawn entity A (faction 0) and entity B (faction 1) within 15.0 units. After one tick of `interaction_system`, entity B's stat[0] should decrease by `10.0 / 60.0`. Entity A's stat[0] should decrease by `20.0 / 60.0`.
- **Same faction, no rule:** Two faction 0 entities near each other — no stat change (no self-interaction rule in default config).
- **Out of range:** Two entities of different factions at distance > 15.0 — no stat change.

### Removal Tests:
- **Entity dies:** Entity with stat[0] = 0.0 → despawned, ID appears in `RemovalEvents`.
- **Entity alive:** Entity with stat[0] = 0.5 → not removed.
- **GreaterOrEqual condition:** Custom rule with `GreaterOrEqual` threshold 100.0. Entity with stat[0] = 100.0 → removed.

---

# Verification_Strategy
Test_Type: unit
Test_Stack: cargo test
Acceptance_Criteria:
  - "interaction_system reduces target stat by delta_per_second / 60 per tick"
  - "Same-faction entities do not interact (unless rule exists)"
  - "removal_system despawns entities crossing stat threshold"
  - "RemovalEvents contains despawned entity IDs"
Suggested_Test_Commands:
  - "cd micro-core && cargo test interaction"
  - "cd micro-core && cargo test removal"
