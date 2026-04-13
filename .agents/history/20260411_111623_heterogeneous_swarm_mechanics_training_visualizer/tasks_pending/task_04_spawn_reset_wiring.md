# Task 04: Spawn & Reset Wiring

**Task_ID:** `task_04_spawn_reset_wiring`
**Feature:** Heterogeneous Swarm Mechanics
**Execution_Phase:** 2 (Parallel with T03)
**Model_Tier:** `standard`

## Target_Files
- `micro-core/src/bridges/zmq_protocol/payloads.rs` [MODIFY]
- `micro-core/src/bridges/zmq_bridge/reset.rs` [MODIFY]

## Dependencies
- T01: `UnitClassId` component exists in `crate::components::UnitClassId`
- T02: `CooldownTracker` exists in `crate::config::CooldownTracker`, `MitigationRule`, `MitigationMode` exist in `crate::rules`

## Context_Bindings
- `context/ipc-protocol`
- `skills/rust-code-standards`

## Contract Reference
See `implementation_plan.md` → Contracts C4 and C5.

## Strict_Instructions

### 1. Expand `SpawnConfig` in `payloads.rs`

Add a new field to the existing `SpawnConfig` struct:

```rust
/// Optional unit class ID for spawned entities. Default: 0 (generic).
/// When absent in JSON, entities spawn as class 0 (backward compatible).
#[serde(default)]
pub unit_class_id: u32,
```

### 2. Expand `CombatRulePayload` in `payloads.rs`

Add new fields to the existing `CombatRulePayload` struct:

```rust
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
```

Add a new struct:

```rust
/// Mitigation configuration from game profile.
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct MitigationPayload {
    pub stat_index: usize,
    /// "PercentReduction" or "FlatReduction"
    pub mode: String,
}
```

### 3. Modify `reset_environment_system` in `reset.rs`

#### 3a. Add Imports

Add at the top:
```rust
use crate::components::UnitClassId;
```

#### 3b. Add CooldownTracker to System Parameters

Add parameter: `mut cooldowns: ResMut<crate::config::CooldownTracker>`

#### 3c. Wire UnitClassId into Spawn Loop

In the spawn loop (step 4 of reset), add `UnitClassId(spawn.unit_class_id)` to the entity bundle:

```rust
commands.spawn((
    entity_id,
    Position { x, y },
    Velocity { dx: 0.0, dy: 0.0 },
    FactionId(spawn.faction_id),
    StatBlock::with_defaults(&stat_defaults),
    VisionRadius::default(),
    UnitClassId(spawn.unit_class_id),  // NEW
    if let Some(ref mc) = reset.movement_config {
        // ... existing movement config ...
    } else {
        MovementConfig::default()
    },
));
```

#### 3d. Wire New Combat Rule Fields

In step 5 (combat rules application), expand the `InteractionRule` construction to include the new fields:

```rust
rules.interaction.rules.push(crate::rules::InteractionRule {
    source_faction: r.source_faction,
    target_faction: r.target_faction,
    range: r.range,
    effects: r.effects.iter().map(|e| crate::rules::StatEffect {
        stat_index: e.stat_index,
        delta_per_second: e.delta_per_second,
    }).collect(),
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

#### 3e. Clear CooldownTracker on Reset

In step 3 (reset game state), add:
```rust
cooldowns.cooldowns.clear();
```

### 4. Update Existing Tests

If `payloads.rs` has existing tests that construct `SpawnConfig` or `CombatRulePayload`, update them to include the new fields (set to defaults/None).

## Anti-Patterns
- ❌ Do NOT modify the `SplitFaction` directive logic — sub-faction entities already carry `UnitClassId` from their initial spawn
- ❌ Do NOT modify the state snapshot (`EntitySnapshot`) — UnitClassId is NOT sent to Python in the observation tensor. The RL model sees ECP density, not unit classes.
- ❌ Do NOT modify `state_vectorizer.rs` — observation space is unchanged in this cycle

## Verification_Strategy

```yaml
Test_Type: unit
Test_Stack: cargo test (Rust)
Acceptance_Criteria:
  - "SpawnConfig without unit_class_id deserializes with default 0"
  - "SpawnConfig with unit_class_id=3 is accepted"
  - "CombatRulePayload without new fields deserializes identically (backward compat)"
  - "CombatRulePayload with mitigation maps correctly"
  - "Environment reset clears CooldownTracker"
  - "Spawned entities have correct UnitClassId"
  - "cargo test (full suite) passes — no regressions"
Suggested_Test_Commands:
  - "cd micro-core && cargo test bridges::zmq_protocol"
  - "cd micro-core && cargo test bridges::zmq_bridge"
  - "cd micro-core && cargo test"
```
