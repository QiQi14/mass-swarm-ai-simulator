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
