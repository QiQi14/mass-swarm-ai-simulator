# Task 05: Python Profile Schema Update

**Task_ID:** `task_05_python_profile_schema`
**Feature:** Heterogeneous Swarm Mechanics
**Execution_Phase:** 3 (Sequential — after T03)
**Model_Tier:** `standard`

## Target_Files
- `macro-brain/src/config/definitions.py` [MODIFY]
- `macro-brain/src/config/parser.py` [MODIFY]
- `macro-brain/src/config/game_profile.py` [MODIFY]

## Dependencies
- T03: Interaction system is live with expanded InteractionRule
- T04: ZMQ payloads accept `unit_class_id` in SpawnConfig and expanded CombatRulePayload

## Context_Bindings
- `context/ipc-protocol`
- `context/conventions`

## Strict_Instructions

### 1. Add New Definitions to `definitions.py`

Add after the existing `FactionConfig` class:

```python
@dataclass(frozen=True)
class UnitClassConfig:
    """Single unit class definition from game profile.
    
    The class_id is context-agnostic — the engine doesn't know
    what 'Sniper' or 'Tank' means. The name is for humans only.
    """
    class_id: int
    name: str  # For human readability only — engine ignores this
    stats: FactionStats  # Default stats for this class
    default_count: int = 0
```

Add after the existing `StatEffectConfig` class:

```python
@dataclass(frozen=True)
class MitigationConfig:
    """Stat-driven damage mitigation configuration."""
    stat_index: int
    mode: str  # "PercentReduction" or "FlatReduction"
```

Expand `CombatRuleConfig` with optional fields:

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

### 2. Update `parser.py`

Add parsing for the optional `unit_registry` section in game profiles:

```python
def _parse_unit_registry(raw: dict) -> list[UnitClassConfig]:
    """Parse optional unit_registry from game profile. Returns [] if absent."""
    registry = raw.get("unit_registry", [])
    return [
        UnitClassConfig(
            class_id=entry["class_id"],
            name=entry["name"],
            stats=FactionStats(hp=entry["stats"]["hp"]),
            default_count=entry.get("default_count", 0),
        )
        for entry in registry
    ]
```

Update `_parse_combat_rules` to handle the new optional fields:

```python
def _parse_combat_rule(raw: dict) -> CombatRuleConfig:
    mitigation_raw = raw.get("mitigation")
    mitigation = MitigationConfig(
        stat_index=mitigation_raw["stat_index"],
        mode=mitigation_raw["mode"],
    ) if mitigation_raw else None
    
    return CombatRuleConfig(
        source_faction=raw["source_faction"],
        target_faction=raw["target_faction"],
        range=raw["range"],
        effects=[StatEffectConfig(**e) for e in raw["effects"]],
        source_class=raw.get("source_class"),
        target_class=raw.get("target_class"),
        range_stat_index=raw.get("range_stat_index"),
        mitigation=mitigation,
        cooldown_ticks=raw.get("cooldown_ticks"),
    )
```

### 3. Update `game_profile.py`

Update the spawn payload builder to include `unit_class_id`:

```python
def _build_spawn_config(self, faction: FactionConfig, unit_class_id: int = 0) -> dict:
    return {
        "faction_id": faction.id,
        "count": faction.default_count,
        # ... existing fields ...
        "unit_class_id": unit_class_id,  # NEW
    }
```

Update the combat rules payload builder to include new fields:

```python
def _build_combat_rule(self, rule: CombatRuleConfig) -> dict:
    payload = {
        "source_faction": rule.source_faction,
        "target_faction": rule.target_faction,
        "range": rule.range,
        "effects": [{"stat_index": e.stat_index, "delta_per_second": e.delta_per_second} for e in rule.effects],
    }
    # Only include optional fields if set (reduces JSON size)
    if rule.source_class is not None:
        payload["source_class"] = rule.source_class
    if rule.target_class is not None:
        payload["target_class"] = rule.target_class
    if rule.range_stat_index is not None:
        payload["range_stat_index"] = rule.range_stat_index
    if rule.mitigation is not None:
        payload["mitigation"] = {
            "stat_index": rule.mitigation.stat_index,
            "mode": rule.mitigation.mode,
        }
    if rule.cooldown_ticks is not None:
        payload["cooldown_ticks"] = rule.cooldown_ticks
    return payload
```

### 4. Do NOT Modify Existing Profiles

**CRITICAL:** Do NOT modify `macro-brain/profiles/tactical_curriculum.json`. This profile has no unit classes and must continue to work exactly as-is. The new fields are all optional with sane defaults.

## Anti-Patterns
- ❌ Do NOT make `unit_registry` required — it's optional (backward compat)
- ❌ Do NOT modify `tactical_curriculum.json` — existing profiles must work unchanged
- ❌ Do NOT add unit class observation channels — the RL model doesn't see unit classes

## Verification_Strategy

```yaml
Test_Type: unit
Test_Stack: pytest (Python)
Acceptance_Criteria:
  - "Existing tactical_curriculum.json loads without errors"
  - "Profile with unit_registry section parses correctly"
  - "CombatRuleConfig with mitigation serializes to correct ZMQ format"
  - "CombatRuleConfig without new fields serializes identically to legacy format"
  - "Spawn payload includes unit_class_id when present"
  - "All existing tests pass unchanged"
Suggested_Test_Commands:
  - "cd macro-brain && .venv/bin/python -m pytest tests/test_profile*.py -v"
  - "cd macro-brain && .venv/bin/python -m pytest tests/ -v"
```
