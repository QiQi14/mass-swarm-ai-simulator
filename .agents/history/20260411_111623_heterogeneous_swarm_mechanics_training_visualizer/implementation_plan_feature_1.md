# Feature 1: UnitClassId & Interaction Overhaul (Rust Core + Python Profile)

> Detail file for Tasks T01–T05 and T07.

---

## Task 01: UnitClassId Component

**Task_ID:** `task_01_unit_class_component`
**Execution_Phase:** 1 (Parallel)
**Model_Tier:** `basic`
**Target_Files:**
- `micro-core/src/components/unit_class.rs` [NEW]
- `micro-core/src/components/mod.rs` [MODIFY]

**Context_Bindings:**
- `skills/rust-code-standards`

**Dependencies:** None

### Strict Instructions

1. **Create `micro-core/src/components/unit_class.rs`:**
   ```rust
   //! # UnitClassId Component
   //!
   //! Context-agnostic unit class identifier.
   //! The Micro-Core never knows what class 0 or class 1 means.
   //! The game profile defines the mapping (e.g., class 0 = "Infantry", class 1 = "Sniper").
   
   use bevy::prelude::*;
   use serde::{Deserialize, Serialize};
   
   /// Context-agnostic unit class identifier. Default: 0 (generic).
   ///
   /// Used by `InteractionRule` to apply class-specific combat rules.
   /// When `UnitClassId` is absent or 0, all rules with `source_class: None`
   /// and `target_class: None` apply (backward compatible).
   #[derive(Component, Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
   pub struct UnitClassId(pub u32);
   
   impl Default for UnitClassId {
       fn default() -> Self { Self(0) }
   }
   
   impl std::fmt::Display for UnitClassId {
       fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
           write!(f, "class_{}", self.0)
       }
   }
   ```

2. **Add tests** following AAA pattern (default, display, serde roundtrip).

3. **Modify `micro-core/src/components/mod.rs`:**
   - Add `pub mod unit_class;`
   - Add `pub use unit_class::UnitClassId;`

### Verification_Strategy

```yaml
Test_Type: unit
Test_Stack: cargo test (Rust)
Acceptance_Criteria:
  - "UnitClassId::default() returns UnitClassId(0)"
  - "UnitClassId(5).to_string() returns 'class_5'"
  - "Serde roundtrip preserves value"
Suggested_Test_Commands:
  - "cd micro-core && cargo test components::unit_class"
```

---

## Task 02: InteractionRule Expansion + CooldownTracker

**Task_ID:** `task_02_interaction_rule_expansion`
**Execution_Phase:** 1 (Parallel)
**Model_Tier:** `standard`
**Target_Files:**
- `micro-core/src/rules/interaction.rs` [MODIFY]
- `micro-core/src/config/cooldown.rs` [NEW]
- `micro-core/src/config/mod.rs` [MODIFY]

**Context_Bindings:**
- `context/engine-mechanics`
- `skills/rust-code-standards`

**Dependencies:** None

### Strict Instructions

1. **Expand `micro-core/src/rules/interaction.rs`:**
   
   Add these new types and fields to `InteractionRule`:
   
   ```rust
   /// Stat-driven damage mitigation applied to the TARGET entity.
   #[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
   pub struct MitigationRule {
       /// Stat index on the TARGET providing mitigation value.
       pub stat_index: usize,
       /// How mitigation is applied.
       pub mode: MitigationMode,
   }
   
   #[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
   pub enum MitigationMode {
       /// damage = base_damage * (1.0 - target_stat.clamp(0.0, 1.0))
       PercentReduction,
       /// damage = (base_damage - target_stat).max(0.0)
       FlatReduction,
   }
   ```

   Add to `InteractionRule`:
   ```rust
   #[serde(default)]
   pub source_class: Option<u32>,
   #[serde(default)]
   pub target_class: Option<u32>,
   #[serde(default)]
   pub range_stat_index: Option<usize>,
   #[serde(default)]
   pub mitigation: Option<MitigationRule>,
   #[serde(default)]
   pub cooldown_ticks: Option<u32>,
   ```

   **CRITICAL: Preserve existing field order** (`source_faction`, `target_faction`, `range`, `effects`) for backward compatibility. New fields must have `#[serde(default)]`.

2. **Update existing tests** to include the new fields (set to `None`/default) to ensure they compile.

3. **Create `micro-core/src/config/cooldown.rs`:**
   ```rust
   //! # Cooldown Tracker
   //!
   //! Per-entity, per-rule cooldown tracking for interaction rules with cooldown_ticks.
   
   use bevy::prelude::*;
   use std::collections::HashMap;
   
   /// Tracks interaction cooldowns per entity per rule.
   ///
   /// Key: (entity_id: u32, rule_index: usize)
   /// Value: ticks remaining before this entity can fire this rule again.
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

4. **Modify `micro-core/src/config/mod.rs`:**
   - Add `pub mod cooldown;`
   - Add `pub use cooldown::CooldownTracker;`

### Anti-Patterns

- ❌ Do NOT make `MitigationMode` use strings — use proper Rust enum with serde.
- ❌ Do NOT add `UnitClassId` to this task — that's T01's responsibility.

### Verification_Strategy

```yaml
Test_Type: unit
Test_Stack: cargo test (Rust)
Acceptance_Criteria:
  - "InteractionRule with all new fields set to None deserializes identically to legacy format"
  - "MitigationRule serde roundtrip works for both PercentReduction and FlatReduction"
  - "CooldownTracker.tick() decrements and removes expired"
  - "CooldownTracker.can_fire() returns true when not on cooldown"
  - "CooldownTracker.start_cooldown() prevents firing for N ticks"
  - "CooldownTracker.remove_entity() clears entity-specific cooldowns"
Suggested_Test_Commands:
  - "cd micro-core && cargo test rules::interaction"
  - "cd micro-core && cargo test config::cooldown"
```

---

## Task 03: Interaction System Upgrade

**Task_ID:** `task_03_interaction_system_upgrade`
**Execution_Phase:** 2 (Sequential)
**Model_Tier:** `advanced`
**Target_Files:**
- `micro-core/src/systems/interaction.rs` [MODIFY]

**Context_Bindings:**
- `context/engine-mechanics`
- `context/conventions`
- `skills/rust-code-standards`

**Dependencies:** T01 (UnitClassId component), T02 (expanded InteractionRule, CooldownTracker)

### Strict Instructions

The `interaction_system` must be upgraded to handle:

1. **Unit class filtering:**
   ```rust
   // After faction check, before computing damage:
   if let Some(src_class) = rule.source_class {
       // Need to query source entity's UnitClassId
       // If source doesn't match, skip
   }
   if let Some(tgt_class) = rule.target_class {
       // Need to query neighbor's UnitClassId
       // If target doesn't match, skip
   }
   ```
   
   **CRITICAL:** The `q_ro` query must be expanded to include `&UnitClassId`:
   ```rust
   q_ro: Query<(Entity, &Position, &FactionId, &EntityId, &UnitClassId)>,
   ```

2. **Dynamic range from stat:**
   ```rust
   let effective_range = if let Some(stat_idx) = rule.range_stat_index {
       // Read from source entity's StatBlock
       if let Ok(source_stats) = q_rw.get(source_entity) {
           source_stats.0.get(stat_idx).copied().unwrap_or(rule.range)
       } else {
           rule.range
       }
   } else {
       rule.range
   };
   ```
   
   **PROBLEM:** `q_rw` is `Query<&mut StatBlock>` — reading from it while iterating would cause borrow issues. **Solution:** Add a third query `q_stats_ro: Query<&StatBlock>` that is read-only for stat lookups. The `q_rw` query is ONLY used for target mutation.
   
   **REVISED query architecture:**
   ```rust
   q_ro: Query<(Entity, &Position, &FactionId, &EntityId, &UnitClassId)>,
   q_stats_ro: Query<&StatBlock>,      // NEW: read-only for source stat lookup
   mut q_rw: Query<&mut StatBlock>,     // write-only for target mutation
   ```
   
   Wait — this won't work. Bevy doesn't allow two queries on the same component (`&StatBlock` and `&mut StatBlock`). 
   
   **ACTUAL SOLUTION:** We read the source stat BEFORE running the inner loop. Use `q_rw.get(source_entity)` OUTSIDE the neighbor loop to read source stats, then release the borrow before entering the neighbor loop.
   
   ```rust
   // Before neighbor loop:
   let source_stat_range = rule.range_stat_index.and_then(|idx| {
       q_rw.get(source_entity).ok().and_then(|sb| sb.0.get(idx).copied())
   });
   let effective_range = source_stat_range.unwrap_or(rule.range);
   
   // Then use effective_range in grid.query_radius()
   ```
   
   This works because `q_rw.get()` (immutable view of `&mut StatBlock`) doesn't hold a mutable borrow — only `get_mut()` does.

3. **Stat-driven mitigation:**
   ```rust
   // Inside the neighbor effect application loop:
   if let Some(ref mit) = rule.mitigation {
       if let Ok(target_stats) = q_rw.get(neighbor_entity) {
           let mit_value = target_stats.0.get(mit.stat_index).copied().unwrap_or(0.0);
           // Apply mitigation to delta
       }
   }
   ```
   
   But again we can't mix `get()` and `get_mut()` on the same entity. 
   
   **SOLUTION:** Read mitigation stat from `q_rw.get()` (read-only borrow) first, compute the mitigated delta, then call `q_rw.get_mut()` to write:
   
   ```rust
   let mitigated_delta = if let Some(ref mit) = rule.mitigation {
       let mit_value = q_rw.get(neighbor_entity)
           .ok()
           .and_then(|sb| sb.0.get(mit.stat_index).copied())
           .unwrap_or(0.0);
       match mit.mode {
           MitigationMode::PercentReduction => {
               effect.delta_per_second * (1.0 - mit_value.clamp(0.0, 1.0))
           }
           MitigationMode::FlatReduction => {
               (effect.delta_per_second.abs() - mit_value).max(0.0) * effect.delta_per_second.signum()
           }
       }
   } else {
       effect.delta_per_second
   };
   ```

4. **Cooldown handling:**
   - Add `mut cooldowns: ResMut<CooldownTracker>` to system params
   - At start of system: `cooldowns.tick()` to decrement all cooldowns
   - Before applying effects: check `cooldowns.can_fire(source_id.id, rule_index)`
   - After applying effects: `cooldowns.start_cooldown(source_id.id, rule_index, cd_ticks)`
   - Need to enumerate rules: change `for rule in &rules.rules` to `for (rule_idx, rule) in rules.rules.iter().enumerate()`

5. **Update existing tests** to spawn entities with `UnitClassId::default()`.

6. **Add new tests:**
   - `test_class_filtering_source` — rule with `source_class: Some(1)` only fires from class 1 units
   - `test_class_filtering_target` — rule with `target_class: Some(2)` only hits class 2 units
   - `test_dynamic_range` — rule with `range_stat_index: Some(3)` uses stat[3] as range
   - `test_mitigation_percent` — target with stat[4]=0.5 reduces damage by 50%
   - `test_mitigation_flat` — target with stat[4]=10.0 reduces damage by 10 flat
   - `test_cooldown` — entity fires once, then blocked for N ticks, then fires again

### Anti-Patterns

- ❌ Do NOT use `unsafe` for query conflicts. Use Bevy's disjoint query pattern.
- ❌ Do NOT allocate inside the hot loop (HashMap, Vec). Pre-compute outside.
- ❌ Do NOT break the O(N×R×K) performance. Cooldown lookup is O(1) HashMap.

### Verification_Strategy

```yaml
Test_Type: unit + integration
Test_Stack: cargo test (Rust)
Acceptance_Criteria:
  - "All existing interaction tests pass unchanged"
  - "Class filtering correctly skips non-matching entities"
  - "Dynamic range reads from StatBlock correctly"
  - "Mitigation reduces damage correctly for both modes"
  - "Cooldown prevents rapid-fire and expires correctly"
  - "Backward compat: rules with no new fields behave identically"
Suggested_Test_Commands:
  - "cd micro-core && cargo test systems::interaction -- --nocapture"
```

---

## Task 04: Spawn & Reset Wiring

**Task_ID:** `task_04_spawn_reset_wiring`
**Execution_Phase:** 2 (Parallel with T03)
**Model_Tier:** `standard`
**Target_Files:**
- `micro-core/src/bridges/zmq_protocol/payloads.rs` [MODIFY]
- `micro-core/src/bridges/zmq_bridge/reset.rs` [MODIFY]

**Context_Bindings:**
- `context/ipc-protocol`
- `skills/rust-code-standards`

**Dependencies:** T01 (UnitClassId component)

### Strict Instructions

1. **Expand `SpawnConfig` in `payloads.rs`:**
   ```rust
   pub struct SpawnConfig {
       // ... existing fields ...
       
       /// Optional unit class ID for spawned entities. Default: 0 (generic).
       #[serde(default)]
       pub unit_class_id: u32,
   }
   ```

2. **Expand `CombatRulePayload` in `payloads.rs`:**
   ```rust
   pub struct CombatRulePayload {
       // ... existing fields ...
       
       #[serde(default)]
       pub source_class: Option<u32>,
       #[serde(default)]
       pub target_class: Option<u32>,
       #[serde(default)]
       pub range_stat_index: Option<usize>,
       #[serde(default)]
       pub mitigation: Option<MitigationPayload>,
       #[serde(default)]
       pub cooldown_ticks: Option<u32>,
   }
   
   #[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
   pub struct MitigationPayload {
       pub stat_index: usize,
       pub mode: String,  // "PercentReduction" or "FlatReduction"
   }
   ```

3. **Modify `reset_environment_system` in `reset.rs`:**
   - In the spawn loop, attach `UnitClassId(spawn.unit_class_id)` to each spawned entity
   - In the combat rules application (step 5), map the new CombatRulePayload fields to InteractionRule:
     ```rust
     rules.interaction.rules.push(crate::rules::InteractionRule {
         source_faction: r.source_faction,
         target_faction: r.target_faction,
         range: r.range,
         effects: /* ... existing ... */,
         source_class: r.source_class,
         target_class: r.target_class,
         range_stat_index: r.range_stat_index,
         mitigation: r.mitigation.as_ref().map(|m| crate::rules::MitigationRule {
             stat_index: m.stat_index,
             mode: match m.mode.as_str() {
                 "FlatReduction" => crate::rules::MitigationMode::FlatReduction,
                 _ => crate::rules::MitigationMode::PercentReduction,
             },
         }),
         cooldown_ticks: r.cooldown_ticks,
     });
     ```
   - Reset `CooldownTracker` on environment reset: add `mut cooldowns: ResMut<CooldownTracker>` and `cooldowns.cooldowns.clear()`

4. **Update existing tests** in payloads.rs to include new default fields.

### Anti-Patterns

- ❌ `UnitClassId` import must come from `crate::components::UnitClassId` (T01 dependency)
- ❌ Do NOT modify the `SplitFaction` logic — sub-factions inherit their parent's `UnitClassId` automatically (entity already has it)

### Verification_Strategy

```yaml
Test_Type: unit
Test_Stack: cargo test (Rust)
Acceptance_Criteria:
  - "SpawnConfig without unit_class_id deserializes with default 0"
  - "SpawnConfig with unit_class_id=3 spawns entities with UnitClassId(3)"
  - "CombatRulePayload with no new fields deserializes identically (backward compat)"
  - "CombatRulePayload with mitigation maps correctly to InteractionRule"
  - "Environment reset clears CooldownTracker"
Suggested_Test_Commands:
  - "cd micro-core && cargo test bridges::zmq_protocol"
  - "cd micro-core && cargo test bridges::zmq_bridge"
```

---

## Task 05: Python Profile Schema Update

**Task_ID:** `task_05_python_profile_schema`
**Execution_Phase:** 3 (Sequential)
**Model_Tier:** `standard`
**Target_Files:**
- `macro-brain/src/config/definitions.py` [MODIFY]
- `macro-brain/src/config/parser.py` [MODIFY]
- `macro-brain/src/config/game_profile.py` [MODIFY]

**Context_Bindings:**
- `context/ipc-protocol`
- `context/conventions`

**Dependencies:** T03 (interaction system is live, so profile must match)

### Strict Instructions

1. **Add to `definitions.py`:**
   ```python
   @dataclass(frozen=True)
   class UnitClassConfig:
       """Single unit class definition from game profile."""
       class_id: int
       name: str  # For human readability only — engine ignores this
       stats: FactionStats  # Default stats for this class
       default_count: int = 0
   
   @dataclass(frozen=True)
   class MitigationConfig:
       stat_index: int
       mode: str  # "PercentReduction" or "FlatReduction"
   ```
   
   Expand `CombatRuleConfig`:
   ```python
   @dataclass(frozen=True)
   class CombatRuleConfig:
       source_faction: int
       target_faction: int
       range: float
       effects: list[StatEffectConfig]
       source_class: int | None = None
       target_class: int | None = None
       range_stat_index: int | None = None
       mitigation: MitigationConfig | None = None
       cooldown_ticks: int | None = None
   ```

2. **Update `parser.py`** to parse `unit_registry` from profile JSON (optional field). If absent, no unit classes defined (backward compat).

3. **Update `game_profile.py`** to:
   - Include `unit_class_id` in spawn payloads when unit classes are defined
   - Include new combat rule fields in the ZMQ reset payload

4. **Do NOT modify `tactical_curriculum.json`** — this profile has no unit classes and must continue to work as-is.

### Verification_Strategy

```yaml
Test_Type: unit
Test_Stack: pytest (Python)
Acceptance_Criteria:
  - "Existing tactical_curriculum.json loads without errors"
  - "Profile with unit_registry section parses correctly"
  - "CombatRuleConfig with mitigation serializes to correct ZMQ format"
  - "Spawn payload includes unit_class_id when unit_registry is defined"
Suggested_Test_Commands:
  - "cd macro-brain && .venv/bin/python -m pytest tests/test_profile*.py -v"
```

---

## Task 07: Context Documentation Update

**Task_ID:** `task_07_context_docs_update`
**Execution_Phase:** 3 (Sequential)
**Model_Tier:** `basic`
**Target_Files:**
- `.agents/context/engine-mechanics.md` [MODIFY]
- `.agents/context/ipc-protocol.md` [MODIFY]

**Context_Bindings:** None (docs task)

**Dependencies:** T03 (interaction system), T04 (spawn/reset)

### Strict Instructions

1. **Update `engine-mechanics.md`:**
   - Add new Section 1b: "Unit Classes" documenting `UnitClassId(u32)`, default behavior, and how interaction rules use it
   - Update Section 2 (Combat System) to document: dynamic range, mitigation modes, cooldown behavior
   - Add combat math example for heterogeneous units (Sniper vs Tank)

2. **Update `ipc-protocol.md`:**
   - Add `unit_class_id` to spawn config documentation
   - Add new combat rule fields (source_class, target_class, range_stat_index, mitigation, cooldown_ticks) to interaction rules documentation
   - Add `MitigationPayload` format

### Verification_Strategy

```yaml
Test_Type: manual_steps
Acceptance_Criteria:
  - "engine-mechanics.md documents UnitClassId, dynamic range, mitigation, cooldowns"
  - "ipc-protocol.md documents expanded spawn and combat rule payloads"
  - "No stale references to old-format-only rules"
```
