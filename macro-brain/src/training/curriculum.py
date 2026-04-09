"""Stage 1 Curriculum — Target Selection Training.

3 sub-stages that progressively teach the model to read the density grid:

  Stage 1: Target at NEAR, Trap at FAR → AttackNearest is always correct
  Stage 2: Target at FAR, Trap at NEAR → AttackFurthest is always correct
  Stage 3: Randomized positions → model must read density to decide

Graduation: 80% win rate over rolling 100 episodes per sub-stage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from numpy.random import Generator
    from src.config.game_profile import GameProfile


# Action names for Stage 1 (3-action space)
ACTION_NAMES = ["Hold", "AttackNearest", "AttackFurthest"]

# Two candidate spawn positions (distances differ from center)
# Brain spawns at center (500, 500).
# "Near" position: 200 units from center
# "Far" position: 350 units from center
POSITION_NEAR = (700.0, 500.0)   # right of center, 200 units away
POSITION_FAR  = (500.0, 150.0)   # above center, 350 units away

# Maximum sub-stage (stage 3 = randomized, final)
MAX_SUBSTAGE = 3


def _faction_stats(profile: GameProfile | None, faction_id: int) -> list[dict]:
    """Get stat initializer from profile or default 100 HP."""
    if profile is not None:
        for f in profile.factions:
            if f.id == faction_id:
                return [{"index": 0, "value": f.stats.hp}]
    return [{"index": 0, "value": 100.0}]


def _faction_count(profile: GameProfile | None, faction_id: int) -> int:
    """Get default entity count from profile or defaults."""
    if profile is not None:
        for f in profile.factions:
            if f.id == faction_id:
                return f.default_count
    return 50


def get_stage1_spawns(
    profile: GameProfile | None = None,
    rng: Generator | None = None,
    substage: int = 1,
):
    """Stage 1 Target Selection: 3-faction spawn layout with sub-stages.

    Brain (faction 0): center, always at (500, 500).
    Trap  (faction 1): 50 units — the large, dangerous group.
    Target(faction 2): 20 units — the small, correct-to-kill-first group.

    Sub-stage layouts:
      1: Target at NEAR, Trap at FAR → AttackNearest always correct
      2: Target at FAR, Trap at NEAR → AttackFurthest always correct
      3: Randomized 50/50 → model must read density grid to decide
    """
    brain_count = _faction_count(profile, 0)
    trap_count = _faction_count(profile, 1)
    target_count = _faction_count(profile, 2)

    # Determine positions based on sub-stage
    if substage == 1:
        # Target always NEAR → AttackNearest is correct
        trap_pos = POSITION_FAR
        target_pos = POSITION_NEAR
    elif substage == 2:
        # Target always FAR → AttackFurthest is correct
        trap_pos = POSITION_NEAR
        target_pos = POSITION_FAR
    else:
        # Randomized — model must read density to decide
        if rng is not None and rng.random() < 0.5:
            trap_pos = POSITION_NEAR
            target_pos = POSITION_FAR
        else:
            trap_pos = POSITION_FAR
            target_pos = POSITION_NEAR

    return [
        {"faction_id": 0, "count": brain_count,
         "x": 500.0, "y": 500.0, "spread": 60.0,
         "stats": _faction_stats(profile, 0)},
        {"faction_id": 1, "count": trap_count,
         "x": trap_pos[0], "y": trap_pos[1], "spread": 60.0,
         "stats": _faction_stats(profile, 1)},
        {"faction_id": 2, "count": target_count,
         "x": target_pos[0], "y": target_pos[1], "spread": 40.0,
         "stats": _faction_stats(profile, 2)},
    ]


def get_spawns_for_stage(
    stage: int,
    rng=None,
    profile: GameProfile | None = None,
):
    """Dispatch to the correct spawn generator based on curriculum stage.

    Stages 1-3 are all Stage 1 sub-stages (target selection).
    """
    return get_stage1_spawns(profile=profile, rng=rng, substage=stage)
