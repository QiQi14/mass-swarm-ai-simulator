"""Stage-specific combat rule construction for curriculum v5.0.

Stages 0-1: No extra rules (basic melee from profile)
Stage 2:    Extended-range rule on target/ranger faction (forced pheromone routing)
Stage 3-4:  No extra rules
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
    target_faction: int | None = None,
) -> list[dict[str, Any]]:
    """Return ADDITIONAL combat rules for the given curriculum stage.

    These are MERGED with the base melee rules from the profile.
    Returns an empty list for stages without special weapons.

    Args:
        stage: Current curriculum stage (0-9).
        enemy_faction: Faction ID of the enemy trap (varies per episode).
        brain_faction: Faction ID of the brain swarm.
        target_faction: Faction ID of the target group (Stage 2 rangers).
            Only needed for stages where the ranged unit is the target,
            not the trap.
    """
    if stage == 2:
        return _stage2_ranger_rules(
            target_faction if target_faction is not None else enemy_faction,
            brain_faction,
        )
    elif stage == 5:
        return _stage5_aoe_cone_rules(enemy_faction, brain_faction)
    elif stage == 6:
        return []  # Speed Chase: standard melee, reinforcements
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


# ── Stage 2: Extended-Range Rangers (Forced Pheromone) ───────────────

def _stage2_ranger_rules(
    ranger_fid: int, brain_fid: int
) -> list[dict[str, Any]]:
    """Rangers (target faction) get extended-range combat rule.

    Combat math:
      - Range 150 (world units), -12 DPS per source entity
      - Rangers sit inside fortress with HoldPosition
      - Any brain unit within 150 units takes chip damage
      - Combined with tanks' melee (-25/s), fighting tanks first
        means taking -37/s combined → brain overwhelmed
      - Killing rangers first via pheromone mud path removes the
        crossfire → tanks alone at -25/s is manageable

    NOTE: The base profile melee rules (range 25, -25/s) still apply
    to the ranger faction. This rule ADDS long-range fire support.
    """
    return [{
        "source_faction": ranger_fid,
        "target_faction": brain_fid,
        "range": 150.0,
        "effects": [{"stat_index": 0, "delta_per_second": -12.0}],
    }]


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
      - Left edge:  (80, 46.0) — 80 × tan(30°) ≈ 46.2
      - Right edge: (80, -46.0)
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


def get_stage_ecp_formula(stage: int) -> dict | None:
    """Return the ECP (Effective Combat Power) formula for the given stage.

    Stages 0-4: None (uses default HP-only calculation `stat[0]`).
    Stages 5+: Multi-stat product `{"stat_indices": [0]}` (extendable).
    """
    if stage >= 5:
        return {"stat_indices": [0]}
    return None


# ── Stage 8: Kinetic Penetration (Forced Screening) ─────────────────

def _stage8_penetration_rules(
    enemy_fid: int, brain_fid: int
) -> list[dict[str, Any]]:
    """Enemy turrets get Kinetic penetration weapon.

    Combat math (from strategy_brief.md):
      - Ray: width 3.0, base_energy 200, absorption on stat[4]
      - Cooldown: 60 ticks (1 shot/sec)
      - Without tanks: 200 energy ÷ 80 HP = 2.5 infantry killed per shot
      - With tanks screening: 300 HP × 0.8 absorption = 240 → ray exhausted
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
