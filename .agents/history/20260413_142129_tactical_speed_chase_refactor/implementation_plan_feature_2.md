# Feature 2: Stage-Specific Combat Rule Builder (Task 02)

## Purpose

Create a factory module that constructs stage-specific `InteractionRule` payloads (AoE cones, AoE circles, kinetic penetration) as raw dicts ready for ZMQ transmission. These rules are **additive** — they are merged with the base melee rules from the profile.

---

## Target Files

- `macro-brain/src/training/stage_combat_rules.py` [NEW]

## Dependencies

- **Task 01** (AoE/Penetration dataclasses must exist in `definitions.py`)

## Context Bindings

- `context/engine` (AoE shapes, penetration energy models, InteractionRule contract)
- `context/training`

---

## Strict Instructions

### Create `macro-brain/src/training/stage_combat_rules.py`

This module provides `get_stage_combat_rules(stage)` and `get_stage_unit_types(stage)`.

```python
"""Stage-specific combat rule construction for curriculum v5.0.

Stages 0-4: No extra rules (basic melee from profile)
Stage 5:    AoE ConvexPolygon cone on enemy faction (forced flanking)
Stage 6:    AoE Circle on enemy faction (forced spread)
Stage 7:    No extra rules (combined arms intro — standard melee only)
Stage 8:    Kinetic Penetration on enemy turrets (forced screening)
Stage 9:    Inherits rules from the randomly chosen sub-stage
"""

from __future__ import annotations
from typing import Any


def get_stage_combat_rules(
    stage: int,
    enemy_faction: int = 1,
    brain_faction: int = 0,
) -> list[dict[str, Any]]:
    """Return ADDITIONAL combat rules for the given curriculum stage.
    
    These are MERGED with the base melee rules from the profile.
    Returns an empty list for stages without special weapons.
    
    Args:
        stage: Current curriculum stage (0-9).
        enemy_faction: Faction ID of the enemy (varies per episode).
        brain_faction: Faction ID of the brain swarm.
    """
    if stage == 5:
        return _stage5_aoe_cone_rules(enemy_faction, brain_faction)
    elif stage == 6:
        return _stage6_aoe_circle_rules(enemy_faction, brain_faction)
    elif stage == 7:
        return []  # Combined Arms Intro: no special weapons, just basic melee
    elif stage == 8:
        return _stage8_penetration_rules(enemy_faction, brain_faction)
    return []


def get_stage_unit_types(stage: int) -> list[dict[str, Any]] | None:
    """Return unit type definitions for stages with heterogeneous armies.
    
    Returns None for stages using homogeneous units (the default).
    Stage 7+ uses heterogeneous brain composition (Infantry + Tank).
    """
    if stage >= 7:
        return _heterogeneous_unit_types()
    return None


# ── Stage 5: AoE Cone (Forced Flanking) ─────────────────────────────

def _stage5_aoe_cone_rules(
    enemy_fid: int, brain_fid: int
) -> list[dict[str, Any]]:
    """Enemy faction gets a 60° forward AoE cone weapon.
    
    Combat math (from strategy_brief.md):
      - Cone: 60° forward, range 80, -15 DPS per source, Linear falloff
      - Frontal charge: all 60 brain units in cone → massive splash → brain dies
      - Flanking (30/30 split, 90°+ angle): only 30 in cone → brain wins
    
    Cone geometry (ConvexPolygon, CCW wound):
      60° cone pointing along +X (source→target aligned):
      - Near apex at (5, 0) — pushed forward so polygon has area
      - Left edge:  (80, 46.2) — 80 × tan(30°) ≈ 46.2
      - Right edge: (80, -46.2)
    """
    return [{
        "source_faction": enemy_fid,
        "target_faction": brain_fid,
        "range": 80.0,
        "effects": [{"stat_index": 0, "delta_per_second": -15.0}],
        "aoe": {
            "shape": {
                "type": "ConvexPolygon",
                "vertices": [
                    [5.0, 0.0],      # Near apex
                    [80.0, 46.0],    # Left edge at max range
                    [80.0, -46.0],   # Right edge at max range
                ],
                "rotation_mode": "TargetAligned",
            },
            "falloff": "Linear",
        },
    }]


# ── Stage 6: AoE Circle (Forced Spread) ─────────────────────────────

def _stage6_aoe_circle_rules(
    enemy_fid: int, brain_fid: int
) -> list[dict[str, Any]]:
    """Enemy faction gets AoE Circle splash weapon.
    
    Combat math (from strategy_brief.md):
      - Circle: radius 30, -10 DPS per source, Quadratic falloff
      - Clumped brain: 40 × 10 × ~60 targets = catastrophic DPS → wipe
      - Spread brain: 40 × 10 × ~3 targets = manageable DPS → survivable
    """
    return [{
        "source_faction": enemy_fid,
        "target_faction": brain_fid,
        "range": 30.0,
        "effects": [{"stat_index": 0, "delta_per_second": -10.0}],
        "aoe": {
            "shape": {
                "type": "Circle",
                "radius": 30.0,
            },
            "falloff": "Quadratic",
        },
    }]


# ── Stage 8: Kinetic Penetration (Forced Screening) ─────────────────

def _stage8_penetration_rules(
    enemy_fid: int, brain_fid: int
) -> list[dict[str, Any]]:
    """Enemy turrets get Kinetic penetration weapon.
    
    Combat math (from strategy_brief.md):
      - Ray: width 3.0, base_energy 200, absorption on stat[4]
      - Cooldown: 60 ticks (1 shot/sec)
      - Without tanks: 200 energy ÷ 80 HP = 2.5 infantry killed per shot
      - With tanks screening: 300 HP × 0.8 absorption = 240 → ray exhausted on 1 tank
    """
    return [{
        "source_faction": enemy_fid,
        "target_faction": brain_fid,
        "range": 200.0,
        "effects": [{"stat_index": 0, "delta_per_second": -30.0}],
        "cooldown_ticks": 60,
        "penetration": {
            "ray_width": 3.0,
            "energy_model": {"Kinetic": {"base_energy": 200.0}},
            "absorption_stat_index": 4,
            "absorption_ignores_mitigation": True,
        },
    }]


# ── Heterogeneous Unit Types (Stage 7+) ────────────────────────────

def _heterogeneous_unit_types() -> list[dict[str, Any]]:
    """Brain unit type definitions for Stages 7+.
    
    Class 0 (Infantry): 80 HP, standard speed, no absorption
    Class 1 (Tank): 300 HP, slower speed (40 vs 60), stat[4]=0.8 absorption
    
    Used for BOTH Stage 7 (combined arms intro) and Stage 8 (screening).
    """
    return [
        {
            "class_id": 0,
            "stats": [{"index": 0, "value": 80.0}],
            "engagement_range": 0.0,
        },
        {
            "class_id": 1,
            "stats": [
                {"index": 0, "value": 300.0},
                {"index": 4, "value": 0.8},
            ],
            "engagement_range": 0.0,
            "movement": {"max_speed": 40.0},
        },
    ]
```

> [!IMPORTANT]
> **Stage 7 uses heterogeneous units but NO special combat rules.** The model has basic melee rules only — it just needs to learn that it has 2 unit classes with different speeds/HP. Stage 8 then adds the kinetic penetration mechanic on top.

> [!IMPORTANT]
> **ConvexPolygon winding:** Rust requires CCW (counter-clockwise) wound vertices. The 60° cone triangle has apex at the near end, fanning out toward max range.

> [!WARNING]
> **Stage 9 inheritance:** Stage 9 calls `_spawns_stage9()` which randomly picks a stage and delegates. The combat rules must also be delegated via `get_last_stage9_choice()` in `curriculum.py`.

---

## Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: unit
  Test_Stack: Python / pytest
  Acceptance_Criteria:
    - "get_stage_combat_rules(0) returns []"
    - "get_stage_combat_rules(5) returns 1 rule with aoe.shape.type == 'ConvexPolygon'"
    - "get_stage_combat_rules(6) returns 1 rule with aoe.shape.type == 'Circle'"
    - "get_stage_combat_rules(7) returns [] (no special weapons)"
    - "get_stage_combat_rules(8) returns 1 rule with penetration.energy_model.Kinetic"
    - "get_stage_unit_types(7) returns 2 unit types (class 0 and 1)"
    - "get_stage_unit_types(6) returns None (homogeneous)"
    - "All returned dicts are JSON-serializable"
    - "ConvexPolygon vertices are CCW wound (cross product check)"
  Suggested_Test_Commands:
    - "cd macro-brain && .venv/bin/python -m pytest tests/test_stage_combat_rules.py -v"
```
