# AGENT ROLE: EXECUTION SPECIALIST

You are an **Execution Specialist** in a multi-agent DAG workflow.
You have been assigned ONE specific task. You implement it with surgical precision.

---

## Your Assignment

| Field   | Value |
|---------|-------|
| Task ID | `task_04_python_profile_extension` |
| Feature | Decouple Game Mechanics |
| Tier    | standard |

---

## ⛔ MANDATORY PROCESS — ALL TIERS (DO NOT SKIP)

> **These rules apply to EVERY executor, regardless of tier. Violating them
> causes an automatic QA FAIL and project BLOCK.**

### Rule 1: Scope Isolation
- You may ONLY create or modify files listed in `Target_Files` in your Task Brief.
- If a file must be changed but is NOT in `Target_Files`, **STOP and report the gap** — do NOT modify it.
- NEVER edit `task_state.json`, `implementation_plan.md`, or any file outside your scope.

### Rule 2: Changelog (Handoff Documentation)
After ALL code is written and BEFORE calling `./task_tool.sh done`, you MUST:

1. **Create** `tasks_pending/task_04_python_profile_extension_changelog.md`
2. **Include in the changelog:**
   - **Touched Files:** A bulleted list of every file you created or modified.
   - **Contract Fulfillment:** Brief confirmation of the interfaces/DTOs you implemented.
   - **Deviations/Notes:** Any edge cases you handled or deviations from the brief the QA agent should verify.
3. **Then and only then** run:
   ```bash
   ./task_tool.sh done task_04_python_profile_extension
   ```

> **⚠️ Calling `./task_tool.sh done` without creating the changelog file is FORBIDDEN.**

### Rule 3: No Placeholders
- Do not use `// TODO`, `/* FIXME */`, or stub implementations.
- Output fully functional, production-ready code.

### Rule 4: Human Intervention Protocol
During execution, a human may intercept your work and propose changes, provide code snippets, or redirect your approach. When this happens:

1. **ADOPT the concept, VERIFY the details.** Humans are exceptional at architectural vision but make detail mistakes (wrong API, typos, outdated syntax). Independently verify all human-provided code against the actual framework version and project contracts.
2. **TRACK every human intervention in the changelog.** Add a dedicated `## Human Interventions` section to your changelog documenting:
   - What the human proposed (1-2 sentence summary)
   - What you adopted vs. what you corrected
   - Any deviations from the original task brief caused by the intervention
3. **DO NOT silently incorporate changes.** The QA agent and Architect must be able to trace exactly what came from the spec vs. what came from a human mid-flight. Untracked changes are invisible to the verification pipeline.

---

## Context Loading (Tier-Dependent)

**If your tier is `basic`:**
- Skip all external file reading. Your Task Brief below IS your complete instruction.
- Implement the code exactly as specified in the Task Brief.
- Follow the MANDATORY PROCESS rules above (changelog + scope), then halt.

**If your tier is `standard` or `advanced`:**
1. Read `.agents/context.md` — Thin index pointing to context sub-files
2. Load ONLY the `context/*` sub-files listed in your `Context_Bindings` below
3. Scan `.agents/knowledge/` — Lessons from previous sessions relevant to your task
4. Read `.agents/workflows/execution-lifecycle.md` — Your 4-step execution loop
5. Read `.agents/rules/execution-boundary.md` — Scope and contract constraints

_No additional context bindings specified._

---

## Task Brief

# Task 04: Python Profile + Env Extension

- **Task_ID:** task_04_python_profile_extension
- **Execution_Phase:** 3 (sequential — after Task 03)
- **Model_Tier:** standard
- **Feature:** Decoupling Game Mechanics

## Target_Files
- `macro-brain/profiles/default_swarm_combat.json`
- `macro-brain/src/config/game_profile.py`
- `macro-brain/src/env/swarm_env.py`
- `macro-brain/src/env/spaces.py`
- `macro-brain/tests/test_training.py`
- `macro-brain/tests/test_vectorizer.py`
- `macro-brain/tests/test_swarm_env.py`

## Dependencies
- Task 03 (ZMQ protocol contracts finalized)

## Context_Bindings
- `context/architecture`
- `context/ipc-protocol`

## Strict_Instructions

### Goal
Update the Python game profile, loader, and environment to send ALL injectable parameters to Rust via ZMQ. The profile now defines movement config, terrain thresholds, abstract buff definitions, removal rules, and max_density.

---

### Step 1: Update `default_swarm_combat.json` (Contract I)

#### Add `movement` section:
```json
"movement": {
    "max_speed": 60.0,
    "steering_factor": 5.0,
    "separation_radius": 6.0,
    "separation_weight": 1.5,
    "flow_weight": 1.0
}
```

#### Add `terrain_thresholds` section:
```json
"terrain_thresholds": {
    "impassable_threshold": 65535,
    "destructible_min": 60001
}
```

#### Add `removal_rules` section:
```json
"removal_rules": [
    { "stat_index": 0, "threshold": 0.0, "condition": "LessOrEqual" }
]
```

#### Update `abilities` section — abstract buff system:
```json
"abilities": {
    "buff_cooldown_ticks": 180,
    "movement_speed_stat": 1,
    "combat_damage_stat": 2,
    "activate_buff": {
        "modifiers": [
            { "stat_index": 1, "modifier_type": "Multiplier", "value": 1.5 },
            { "stat_index": 2, "modifier_type": "Multiplier", "value": 1.5 }
        ],
        "duration_ticks": 60
    }
}
```

> **NOTE:** `stat_index: 1` = speed modifier, `stat_index: 2` = damage modifier. These are just numbers to the engine. The profile defines the semantics.

#### Add `max_density` to `training`:
```json
"training": {
    "max_density": 50.0,
    ...existing fields...
}
```

#### Rename action from `"Frenzy"` to `"ActivateBuff"`:
```json
{ "index": 2, "name": "ActivateBuff", "unlock_stage": 1 }
```

---

### Step 2: Update `game_profile.py`

#### 2a. Add new dataclasses:

```python
@dataclass(frozen=True)
class MovementConfigDef:
    max_speed: float
    steering_factor: float
    separation_radius: float
    separation_weight: float
    flow_weight: float

@dataclass(frozen=True)
class TerrainThresholdsDef:
    impassable_threshold: int
    destructible_min: int

@dataclass(frozen=True)
class StatModifierDef:
    stat_index: int
    modifier_type: str   # "Multiplier" or "FlatAdd"
    value: float

@dataclass(frozen=True)
class ActivateBuffDef:
    modifiers: list  # List of StatModifierDef
    duration_ticks: int

@dataclass(frozen=True)
class AbilitiesDef:
    buff_cooldown_ticks: int
    movement_speed_stat: int | None
    combat_damage_stat: int | None
    activate_buff: ActivateBuffDef

@dataclass(frozen=True)
class RemovalRuleDef:
    stat_index: int
    threshold: float
    condition: str   # "LessOrEqual" or "GreaterOrEqual"
```

#### 2b. Update `GameProfile`:

```python
movement: MovementConfigDef
terrain_thresholds: TerrainThresholdsDef
abilities: AbilitiesDef
removal_rules: list  # List of RemovalRuleDef
# In training: max_density: float
```

#### 2c. Add payload serializers:

```python
def movement_config_payload(self) -> dict:
    return asdict(self.movement)

def terrain_thresholds_payload(self) -> dict:
    return asdict(self.terrain_thresholds)

def ability_config_payload(self) -> dict:
    return {
        "buff_cooldown_ticks": self.abilities.buff_cooldown_ticks,
        "movement_speed_stat": self.abilities.movement_speed_stat,
        "combat_damage_stat": self.abilities.combat_damage_stat,
    }

def removal_rules_payload(self) -> list:
    return [asdict(r) for r in self.removal_rules]
```

#### 2d. Update JSON loader to parse all new sections.

---

### Step 3: Update `swarm_env.py`

#### 3a. Update reset payload:

```python
self._socket.send_string(json.dumps({
    "type": "reset_environment",
    "terrain": terrain,
    "spawns": spawns,
    "combat_rules": self.profile.combat_rules_payload(),
    "ability_config": self.profile.ability_config_payload(),
    "movement_config": self.profile.movement_config_payload(),
    "max_density": self.profile.training.max_density,
    "terrain_thresholds": self.profile.terrain_thresholds_payload(),
    "removal_rules": self.profile.removal_rules_payload(),
}))
```

#### 3b. Update `_action_to_directive()` — ActivateBuff with modifiers:

```python
"directive": "ActivateBuff",
"faction": 0,
"modifiers": [asdict(m) for m in self.profile.abilities.activate_buff.modifiers],
"duration_ticks": self.profile.abilities.activate_buff.duration_ticks,
"targets": [],  # Empty = all units in faction. Python ML decides targeting.
```

---

### Step 4: Update `spaces.py`

Rename `ACTION_FRENZY` → `ACTION_ACTIVATE_BUFF` (or just update the string mapping):
- `"TriggerFrenzy"` → `"ActivateBuff"`

---

### Step 5: Update Tests

- `test_swarm_env.py`: `"TriggerFrenzy"` → `"ActivateBuff"` in mock data
- `test_training.py`: Update assertions if they reference Frenzy
- All tests must continue to pass

---

### Step 6: Verify

```bash
cd macro-brain && source venv/bin/activate
python -m pytest tests/ -v --ignore=tests/test_terrain_generator.py --ignore=tests/test_swarm_env.py
```

## Verification_Strategy
  Test_Type: unit
  Test_Stack: Python (pytest)
  Acceptance_Criteria:
    - "JSON profile includes movement, terrain_thresholds, removal_rules, abstract abilities"
    - "GameProfile parses all new sections"
    - "SwarmEnv.reset() sends all new fields in ZMQ payload"
    - "ActivateBuff carries modifiers list not speed_multiplier/damage_multiplier"
    - "All Python tests pass"
    - "Zero references to TriggerFrenzy"
  Suggested_Test_Commands:
    - "cd macro-brain && source venv/bin/activate && python -m pytest tests/ -v --ignore=tests/test_terrain_generator.py --ignore=tests/test_swarm_env.py"

---

## Shared Contracts

# Decoupling Hardcoded Game Mechanics from Micro-Core

**Principle:** The Micro-Core is a **pure computation engine**. It processes physics, pathfinding, and combat math based on externally injected rules. It has zero knowledge of "what game this is."

**Who owns game design:**
- **Training mode:** Python Macro-Brain injects the profile via ZMQ `ResetEnvironment`.
- **Demo/Lab mode:** Debug Visualizer acts as the game engine — it sends the profile via WS on Start.

---

## Shared Contracts

These contracts are referenced by multiple tasks. All tasks MUST implement against these exact definitions.

### Contract A: `ActivateBuff` Directive — Fully Abstract

The engine knows nothing about "speed" or "damage." A buff is a list of stat modifiers applied to targeted entities within a faction for a duration.

```rust
// In zmq_protocol.rs — MacroDirective enum
ActivateBuff {
    faction: u32,
    /// Stat modifiers to apply for the duration of the buff.
    modifiers: Vec<StatModifierPayload>,
    duration_ticks: u32,
    /// Entity-level targeting within the faction:
    /// - None → buff registered but no units affected
    /// - Some([]) → all units in the faction get buff
    /// - Some([1, 5, 12]) → only those entity IDs get buff
    #[serde(default)]
    targets: Option<Vec<u32>>,
},

#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct StatModifierPayload {
    /// Which stat index to modify (game profile defines meaning).
    pub stat_index: usize,
    /// How to apply the modifier.
    pub modifier_type: ModifierType,
    /// The modifier value.
    pub value: f32,
}

#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub enum ModifierType {
    /// stat_effective = stat_base × value
    Multiplier,
    /// stat_effective = stat_base + value
    FlatAdd,
}
```

### Contract B: `BuffConfig` Resource — Stat-to-System Mapping

The engine HAS movement and combat systems — those are engine mechanics. But WHICH stat index drives speed vs damage is game design. `BuffConfig` is the mapping table.

```rust
// In config.rs
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

### Contract C: `FactionBuffs` Resource — Abstract Active Buffs

```rust
// In config.rs
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

#[derive(Debug, Clone)]
pub struct ActiveModifier {
    pub stat_index: usize,
    pub modifier_type: ModifierType,
    pub value: f32,
}

#[derive(Debug, Clone, PartialEq)]
pub enum ModifierType {
    Multiplier,
    FlatAdd,
}
```

Helper methods for systems — entity-level targeting aware:
```rust
impl FactionBuffs {
    /// Get the cumulative multiplier for a specific stat, respecting entity targeting.
    /// `entity_id`: the EntityId.id of the entity being queried.
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

impl ActiveBuffGroup {
    /// Check if this buff group targets a specific entity.
    fn targets_entity(&self, entity_id: u32) -> bool {
        match &self.targets {
            None => false,                          // Dormant — no units
            Some(ids) if ids.is_empty() => true,    // All units in faction
            Some(ids) => ids.contains(&entity_id),  // Specific units
        }
    }
}
```

### Contract D: `DensityConfig` Resource

```rust
#[derive(Resource, Debug, Clone)]
pub struct DensityConfig {
    pub max_density: f32,
}
impl Default for DensityConfig {
    fn default() -> Self { Self { max_density: 0.0 } }
}
```

### Contract E: `MovementConfigPayload` (ZMQ)

```rust
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct MovementConfigPayload {
    pub max_speed: f32,
    pub steering_factor: f32,
    pub separation_radius: f32,
    pub separation_weight: f32,
    pub flow_weight: f32,
}
```

### Contract F: `AbilityConfigPayload` — Generic

```rust
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct AbilityConfigPayload {
    pub buff_cooldown_ticks: u32,
    /// Which stat_index controls movement speed multiplier (None = disabled).
    pub movement_speed_stat: Option<usize>,
    /// Which stat_index controls combat damage multiplier (None = disabled).
    pub combat_damage_stat: Option<usize>,
}
```

### Contract G: Extended `ResetEnvironment`

```rust
ResetEnvironment {
    terrain: Option<TerrainPayload>,
    spawns: Vec<SpawnConfig>,
    #[serde(default)]
    combat_rules: Option<Vec<CombatRulePayload>>,
    #[serde(default)]
    ability_config: Option<AbilityConfigPayload>,
    #[serde(default)]
    movement_config: Option<MovementConfigPayload>,
    #[serde(default)]
    max_density: Option<f32>,
    #[serde(default)]
    terrain_thresholds: Option<TerrainThresholdsPayload>,
    #[serde(default)]
    removal_rules: Option<Vec<RemovalRulePayload>>,
},
```

### Contract H: `TerrainThresholdsPayload` + `RemovalRulePayload`

```rust
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct TerrainThresholdsPayload {
    pub impassable_threshold: u16,
    pub destructible_min: u16,
}

#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct RemovalRulePayload {
    pub stat_index: usize,
    pub threshold: f32,
    /// "LessOrEqual" or "GreaterOrEqual"
    pub condition: String,
}
```

### Contract I: Python Profile Schema

```json
{
  "movement": {
    "max_speed": 60.0,
    "steering_factor": 5.0,
    "separation_radius": 6.0,
    "separation_weight": 1.5,
    "flow_weight": 1.0
  },
  "terrain_thresholds": {
    "impassable_threshold": 65535,
    "destructible_min": 60001
  },
  "abilities": {
    "buff_cooldown_ticks": 180,
    "movement_speed_stat": 1,
    "combat_damage_stat": 2,
    "activate_buff": {
      "modifiers": [
        { "stat_index": 1, "modifier_type": "Multiplier", "value": 1.5 },
        { "stat_index": 2, "modifier_type": "Multiplier", "value": 1.5 }
      ],
      "duration_ticks": 60
    }
  },
  "removal_rules": [
    { "stat_index": 0, "threshold": 0.0, "condition": "LessOrEqual" }
  ],
  "training": {
    "max_density": 50.0,
    ...
  }
}
```

---

## Audit: All Violations & Resolutions

| # | Violation | File | Resolution |
|---|-----------|------|------------|
| V1 | `InteractionRuleSet::default()` hardcodes 2 combat rules | `rules/interaction.rs` | Default → empty `vec![]` |
| V2 | `MovementConfig::default()` hardcodes Boids params | `components/movement_config.rs` | Default → all zeros |
| V3 | `FrenzyConfig` — game-specific ability | `config.rs` | Replace with abstract `BuffConfig` |
| V4 | `SimulationConfig::default()` hardcodes wave spawn | `config.rs` | Remove wave spawn fields |
| V5 | `DEFAULT_MAX_DENSITY = 50.0` hardcoded | `state_vectorizer.rs` | Inject via `DensityConfig` resource |
| V6 | `reset_environment_system` spawns with `MovementConfig::default()` | `zmq_bridge/systems.rs` | Inject from ZMQ payload |
| V7 | Spawn fallback `vec![(0, 100.0)]` if stats empty | `zmq_bridge/systems.rs` | Remove fallback |
| V8 | `wave_spawn_system` is game-mode-specific | `systems/spawning.rs` | Remove entirely |
| V9 | Terrain tier constants hardcoded | `terrain.rs` | Eject to `TerrainGrid` fields |
| V10 | `RemovalRuleSet::default()` hardcodes "HP <= 0" | `rules/removal.rs` | Default → empty, inject via ZMQ |

---

## Execution DAG

```mermaid
graph TB
    T1["Task 01<br/>Terrain Tier Ejection<br/>(Phase 1)"] --> T3
    T2["Task 02<br/>Neutralize All Defaults<br/>(Phase 1)"] --> T3
    T3["Task 03<br/>Abstract Buff + ZMQ Extension<br/>(Phase 2)"] --> T4
    T4["Task 04<br/>Python Profile + Env<br/>(Phase 3)"] --> T5
    T5["Task 05<br/>Integration Verify<br/>(Phase 4)"]
```

| Phase | Task | Model Tier | Parallel? |
|-------|------|------------|-----------|
| 1 | Task 01: Terrain Tier Ejection | `standard` | ✅ parallel with T02 |
| 1 | Task 02: Neutralize All Defaults (V1, V2, V8, V10) | `standard` | ✅ parallel with T01 |
| 2 | Task 03: Abstract Buff + ZMQ Extension + Reset Handler | `advanced` | sequential |
| 3 | Task 04: Python Profile + Env Extension | `standard` | sequential |
| 4 | Task 05: Integration Verify | `standard` | sequential |

## File Ownership Matrix (Zero Collision Guarantee)

| File | T01 | T02 | T03 | T04 | T05 |
|------|-----|-----|-----|-----|-----|
| `terrain.rs` | ✏️ | | | | |
| `rules/interaction.rs` | | ✏️ | | | |
| `rules/removal.rs` | | ✏️ | | | |
| `components/movement_config.rs` | | ✏️ | | | |
| `systems/spawning.rs` | | ✏️ | | | |
| `systems/mod.rs` | | ✏️ | | | |
| `config.rs` | | | ✏️ | | |
| `main.rs` | | | ✏️ | | |
| `systems/directive_executor.rs` | | | ✏️ | | |
| `systems/interaction.rs` | | | ✏️ | | |
| `systems/movement.rs` | | | ✏️ | | |
| `bridges/zmq_protocol.rs` | | | ✏️ | | |
| `bridges/zmq_bridge/systems.rs` | | | ✏️ | | |
| `systems/state_vectorizer.rs` | | | ✏️ | | |
| `macro-brain/src/config/game_profile.py` | | | | ✏️ | |
| `macro-brain/profiles/default_swarm_combat.json` | | | | ✏️ | |
| `macro-brain/src/env/swarm_env.py` | | | | ✏️ | |
| `macro-brain/src/env/spaces.py` | | | | ✏️ | |
| `macro-brain/tests/*.py` | | | | ✏️ | |

## Verification Plan

```bash
# After each Rust task:
cd micro-core && cargo test && cargo clippy

# After Task 04:
cd macro-brain && source venv/bin/activate && python -m pytest tests/ -v

# After Task 05 (integration):
# Zero grep hits for: FrenzyConfig, FactionSpeedBuffs, TriggerFrenzy,
#   wave_spawn, DEFAULT_MAX_DENSITY, TERRAIN_DESTRUCTIBLE_*, damage_multiplier_enabled
```

