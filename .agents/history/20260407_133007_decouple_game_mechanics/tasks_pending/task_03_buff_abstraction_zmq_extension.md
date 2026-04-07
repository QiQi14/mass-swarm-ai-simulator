# Task 03: Abstract Buff System + ZMQ Extension + Reset Handler + Config Cleanup

- **Task_ID:** task_03_buff_abstraction_zmq_extension
- **Execution_Phase:** 2 (sequential — after Task 01 + Task 02)
- **Model_Tier:** advanced
- **Feature:** Decoupling Game Mechanics

## Target_Files
- `micro-core/src/config.rs`
- `micro-core/src/main.rs`
- `micro-core/src/systems/directive_executor.rs`
- `micro-core/src/systems/interaction.rs`
- `micro-core/src/systems/movement.rs`
- `micro-core/src/bridges/zmq_protocol.rs`
- `micro-core/src/bridges/zmq_bridge/systems.rs`
- `micro-core/src/systems/state_vectorizer.rs`

## Dependencies
- Task 01 (terrain.rs — new `TerrainGrid` fields for threshold injection)
- Task 02 (defaults neutralized, wave_spawn_system removed)

## Context_Bindings
- `context/architecture`
- `context/ipc-protocol`
- `skills/rust-code-standards`

## Strict_Instructions

### Goal
1. Replace `FrenzyConfig`/`FactionSpeedBuffs` with a fully abstract stat-index-based buff system
2. Rename `TriggerFrenzy` → `ActivateBuff` with generic stat modifiers
3. Extend ZMQ `ResetEnvironment` with all new injectable parameters
4. Update movement and combat systems to read buff modifiers by configurable stat index
5. Clean up `config.rs` and `main.rs`

> **CRITICAL DESIGN PRINCIPLE:** The engine's buff system must be 100% stat-index-based. It MUST NOT contain the words "speed", "damage", "hp" or any other game-specific stat name in the buff data structures. The `BuffConfig` resource maps stat indices to system behaviors — that mapping is the ONLY place the engine connects "stat X affects movement" and "stat Y affects damage."

---

### Part A: Config Cleanup + Abstract Buff Resources

#### A1. `config.rs` — Remove wave spawn fields (V4)

Remove `wave_spawn_interval`, `wave_spawn_count`, `wave_spawn_faction`, `wave_spawn_stat_defaults` from `SimulationConfig`.

Fix `test_simulation_config_defaults` — remove wave assertions.

#### A2. `config.rs` — Delete FrenzyConfig (V3)

Delete the entire `FrenzyConfig` struct and its `Default` impl.

#### A3. `config.rs` — Delete FactionSpeedBuffs

Delete the entire `FactionSpeedBuffs` struct.

#### A4. `config.rs` — Add BuffConfig (Contract B)

```rust
/// Buff system configuration from game profile.
///
/// Maps abstract stat indices to engine system behaviors.
/// The engine has movement and combat systems — those are engine mechanics.
/// But WHICH stat index drives speed vs damage is game design.
#[derive(Resource, Debug, Clone)]
pub struct BuffConfig {
    /// Cooldown ticks after any buff expires. Default: 0.
    pub cooldown_ticks: u32,
    /// Which stat_index in active buffs controls movement speed multiplier.
    /// None = buffs never affect movement speed.
    pub movement_speed_stat: Option<usize>,
    /// Which stat_index in active buffs controls combat damage multiplier.
    /// None = buffs never affect combat damage.
    pub combat_damage_stat: Option<usize>,
}

impl Default for BuffConfig {
    fn default() -> Self {
        Self {
            cooldown_ticks: 0,
            movement_speed_stat: None,
            combat_damage_stat: None,
        }
    }
}
```

#### A5. `config.rs` — Add FactionBuffs + ActiveBuffGroup + ActiveModifier + ModifierType (Contract C)

```rust
/// Active stat-multiplier buffs per faction — fully abstract.
///
/// Each buff group contains modifiers (stat_index + type + value), a duration,
/// and optional entity-level targeting. The engine doesn't know what
/// stat_index 0 means — the game profile defines that.
#[derive(Resource, Debug, Default)]
pub struct FactionBuffs {
    /// Active buff groups: faction → list of active buff groups.
    pub buffs: std::collections::HashMap<u32, Vec<ActiveBuffGroup>>,
    /// Cooldown: faction → ticks remaining before next buff activation.
    pub cooldowns: std::collections::HashMap<u32, u32>,
}

/// A group of stat modifiers applied together with shared duration and targeting.
#[derive(Debug, Clone)]
pub struct ActiveBuffGroup {
    pub modifiers: Vec<ActiveModifier>,
    pub remaining_ticks: u32,
    /// Entity-level targeting:
    /// - None → no units affected (buff is dormant)
    /// - Some(empty vec) → all units in faction
    /// - Some(vec of ids) → only matching entity IDs
    pub targets: Option<Vec<u32>>,
}

impl ActiveBuffGroup {
    /// Check if this buff group targets a specific entity.
    pub fn targets_entity(&self, entity_id: u32) -> bool {
        match &self.targets {
            None => false,                          // Dormant — no units
            Some(ids) if ids.is_empty() => true,    // All units in faction
            Some(ids) => ids.contains(&entity_id),  // Specific units
        }
    }
}

/// A single stat modifier within a buff group.
#[derive(Debug, Clone)]
pub struct ActiveModifier {
    pub stat_index: usize,
    pub modifier_type: ModifierType,
    pub value: f32,
}

/// How a modifier is applied to a stat.
#[derive(Debug, Clone, PartialEq)]
pub enum ModifierType {
    /// stat_effective = stat_base × value
    Multiplier,
    /// stat_effective = stat_base + value
    FlatAdd,
}
```

Add helper methods on `FactionBuffs` — entity-level targeting aware:
```rust
impl FactionBuffs {
    /// Get the cumulative multiplier for a specific stat, respecting entity targeting.
    /// Returns 1.0 if no active multiplier buff targets this entity.
    pub fn get_multiplier(&self, faction: u32, entity_id: u32, stat_index: usize) -> f32 {
        let Some(groups) = self.buffs.get(&faction) else { return 1.0 };
        let mut product = 1.0f32;
        for group in groups {
            if !group.targets_entity(entity_id) { continue; }
            for m in &group.modifiers {
                if m.stat_index == stat_index && m.modifier_type == ModifierType::Multiplier {
                    product *= m.value;
                }
            }
        }
        product
    }

    /// Get the cumulative flat add for a specific stat, respecting entity targeting.
    pub fn get_flat_add(&self, faction: u32, entity_id: u32, stat_index: usize) -> f32 {
        let Some(groups) = self.buffs.get(&faction) else { return 0.0 };
        let mut sum = 0.0f32;
        for group in groups {
            if !group.targets_entity(entity_id) { continue; }
            for m in &group.modifiers {
                if m.stat_index == stat_index && m.modifier_type == ModifierType::FlatAdd {
                    sum += m.value;
                }
            }
        }
        sum
    }
}
```

#### A6. `config.rs` — Add DensityConfig (Contract D)

```rust
#[derive(Resource, Debug, Clone)]
pub struct DensityConfig {
    pub max_density: f32,
}
impl Default for DensityConfig {
    fn default() -> Self { Self { max_density: 0.0 } }
}
```

#### A7. `config.rs` — Tests

- Update FrenzyConfig tests → BuffConfig tests
- Update FactionSpeedBuffs tests → FactionBuffs tests
- Add tests for `get_multiplier` and `get_flat_add` helpers

---

### Part B: Buff Abstraction in Systems

#### B1. `systems/directive_executor.rs`

1. **Update imports:** Replace `FactionSpeedBuffs` → `FactionBuffs`, remove `FrenzyConfig`
2. **Rename `TriggerFrenzy` → `ActivateBuff`** match arm:

```rust
MacroDirective::ActivateBuff { faction, modifiers, duration_ticks, targets } => {
    // Cooldown check
    if buffs.cooldowns.contains_key(&faction) {
        return;
    }
    let active_mods: Vec<ActiveModifier> = modifiers.iter().map(|m| {
        ActiveModifier {
            stat_index: m.stat_index,
            modifier_type: match m.modifier_type {
                crate::bridges::zmq_protocol::ModifierType::Multiplier => crate::config::ModifierType::Multiplier,
                crate::bridges::zmq_protocol::ModifierType::FlatAdd => crate::config::ModifierType::FlatAdd,
            },
            value: m.value,
        }
    }).collect();
    let group = ActiveBuffGroup {
        modifiers: active_mods,
        remaining_ticks: duration_ticks,
        targets,
    };
    // Append to existing groups (faction may have multiple active buff groups)
    buffs.buffs.entry(faction).or_default().push(group);
},
```

3. **Rename `speed_buff_tick_system` → `buff_tick_system`:**

```rust
pub fn buff_tick_system(
    mut buffs: ResMut<FactionBuffs>,
    buff_config: Res<BuffConfig>,
) {
    let mut expired_factions = Vec::new();

    // Tick down all active buff groups per faction
    for (faction, groups) in buffs.buffs.iter_mut() {
        groups.retain_mut(|group| {
            group.remaining_ticks = group.remaining_ticks.saturating_sub(1);
            group.remaining_ticks > 0
        });
        if groups.is_empty() {
            expired_factions.push(*faction);
        }
    }

    // Remove empty faction entries and start cooldowns
    for faction in expired_factions {
        buffs.buffs.remove(&faction);
        if buff_config.cooldown_ticks > 0 {
            buffs.cooldowns.insert(faction, buff_config.cooldown_ticks);
        }
    }

    // Tick cooldowns
    buffs.cooldowns.retain(|_, ticks| {
        *ticks = ticks.saturating_sub(1);
        *ticks > 0
    });
}
```

4. **Update `MergeFaction`** handler: `speed_buffs.buffs.remove(...)` → `buffs.buffs.remove(...)`
5. **Fix all tests** — update TriggerFrenzy → ActivateBuff, FactionSpeedBuffs → FactionBuffs, etc.

#### B2. `systems/interaction.rs`

1. Replace `FactionSpeedBuffs` → `FactionBuffs`, remove `FrenzyConfig`
2. Add `BuffConfig` as a system parameter
3. Add `EntityId` to the `q_ro` query so we can pass entity_id to `get_multiplier`
4. Replace hardcoded damage multiplier logic with abstract stat-index lookup:

```rust
// Abstract damage multiplier via configurable stat index + entity targeting
let damage_mult = buff_config.combat_damage_stat
    .map(|stat_idx| combat_buffs.get_multiplier(source_faction.0, source_entity_id.id, stat_idx))
    .unwrap_or(1.0);
```

This replaces the entire `if frenzy_config.damage_multiplier_enabled { ... }` block.
**Note:** `q_ro` query must include `&EntityId` to access `.id`.

5. **Fix all tests** — replace FrenzyConfig/FactionSpeedBuffs in `setup_app()`.

#### B3. `systems/movement.rs`

1. Replace `FactionSpeedBuffs` → `FactionBuffs`
2. Add `BuffConfig` as a system parameter
3. Add `EntityId` to the movement query to pass entity_id to `get_multiplier`
4. Replace hardcoded speed multiplier:

**Before:**
```rust
let speed_mult = speed_buffs.buffs.get(&faction.0).map(|(m, _)| *m).unwrap_or(1.0);
```

**After:**
```rust
let speed_mult = buff_config.movement_speed_stat
    .map(|stat_idx| faction_buffs.get_multiplier(faction.0, entity_id.id, stat_idx))
    .unwrap_or(1.0);
```
**Note:** Movement query must include `&EntityId`.

5. **Fix all tests** — add BuffConfig + FactionBuffs to test setup apps.

---

### Part C: ZMQ Protocol Extension

#### C1. `bridges/zmq_protocol.rs`

1. **Add `ModifierType` enum** (serde-compatible):
```rust
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub enum ModifierType {
    Multiplier,
    FlatAdd,
}
```

2. **Add `StatModifierPayload`:**
```rust
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct StatModifierPayload {
    pub stat_index: usize,
    pub modifier_type: ModifierType,
    pub value: f32,
}
```

3. **Rename `TriggerFrenzy` → `ActivateBuff`** in MacroDirective (Contract A):
```rust
ActivateBuff {
    faction: u32,
    modifiers: Vec<StatModifierPayload>,
    duration_ticks: u32,
    #[serde(default)]
    targets: Option<Vec<u32>>,
},
```

4. **Add `MovementConfigPayload`** (Contract E)
5. **Add `TerrainThresholdsPayload`** (Contract H)
6. **Add `RemovalRulePayload`** (Contract H)

7. **Update `AbilityConfigPayload`** (Contract F):
```rust
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct AbilityConfigPayload {
    pub buff_cooldown_ticks: u32,
    #[serde(default)]
    pub movement_speed_stat: Option<usize>,
    #[serde(default)]
    pub combat_damage_stat: Option<usize>,
}
```

8. **Extend `ResetEnvironment`** (Contract G):
Add `movement_config`, `max_density`, `terrain_thresholds`, `removal_rules` fields (all `#[serde(default)]`).

9. **Fix serde tests** — TriggerFrenzy roundtrip → ActivateBuff with modifiers.

---

### Part D: Reset Handler Update

#### D1. `bridges/zmq_bridge/systems.rs`

1. **Update `ResetRequest`** to include all new fields
2. **Update entity spawning (V6, V7):**
   - Replace `MovementConfig::default()` with injected config from `reset.movement_config`
   - Remove `vec![(0, 100.0)]` fallback (V7) — empty stats = empty StatBlock
3. **Apply new configs in reset handler:**
   - `ability_config` → `BuffConfig` (cooldown + stat mappings)
   - `movement_config` → `MovementConfig` per entity
   - `max_density` → `DensityConfig`
   - `terrain_thresholds` → `TerrainGrid` fields
   - `removal_rules` → `RemovalRuleSet`
4. **Replace `DEFAULT_MAX_DENSITY` import** with `DensityConfig` resource access
5. **Replace `FrenzyConfig`/`FactionSpeedBuffs`** imports with new types

#### D2. `systems/state_vectorizer.rs`

1. **Remove** `pub const DEFAULT_MAX_DENSITY: f32 = 50.0;`
2. All callers pass `max_density` from `DensityConfig` resource.

---

### Part E: Main.rs Cleanup

1. **Remove `wave_spawn_system`** from all system registrations
2. **Update resource registrations:**
   - `.init_resource::<FactionSpeedBuffs>()` → `.init_resource::<FactionBuffs>()`
   - `.init_resource::<FrenzyConfig>()` → `.init_resource::<BuffConfig>()`
   - ADD `.init_resource::<DensityConfig>()`
3. **Update `speed_buff_tick_system` → `buff_tick_system`** in system registrations
4. **Update imports** to match new type names

### Step Final: Verify

```bash
cd micro-core && cargo build
cd micro-core && cargo test
cd micro-core && cargo clippy
```

## Verification_Strategy
  Test_Type: unit + integration
  Test_Stack: Rust (cargo test)
  Acceptance_Criteria:
    - "`cargo build` succeeds"
    - "All tests pass — zero references to FrenzyConfig, FactionSpeedBuffs, TriggerFrenzy, wave_spawn, DEFAULT_MAX_DENSITY, damage_multiplier_enabled"
    - "ActivateBuff carries Vec<StatModifierPayload> not named speed/damage fields"
    - "Movement system reads multiplier via buff_config.movement_speed_stat"
    - "Interaction system reads multiplier via buff_config.combat_damage_stat"
    - "ResetEnvironment includes movement_config, max_density, terrain_thresholds, removal_rules"
    - "`cargo clippy` no new warnings"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test"
    - "cd micro-core && cargo clippy"
