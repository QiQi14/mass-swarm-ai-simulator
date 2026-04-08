"""Stage 1 Tactical Curriculum — 3-Faction Spawn Configuration.

Spawns Brain, Patrol Group, and Target Group for the tactical
decision training scenario.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.config.game_profile import GameProfile


# Action names for Stage 1 Tactical (3-action space)
ACTION_NAMES = ["Hold", "AttackA", "AttackB"]


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


def get_stage1_spawns(profile: GameProfile | None = None):
    """Stage 1 Tactical: 3-faction spawn layout.

    Brain (faction 0): 50 units at far left.
    Patrol (faction 1): 20 units at center, will patrol vertically.
    Target (faction 2): 50 units at center-right, stationary.

    Layout creates a gauntlet: the patrol crosses the path between
    the brain and the target. The brain must time its approach to
    bypass the patrol and reach the target while it's debuffed.
    """
    brain_count = _faction_count(profile, 0)
    patrol_count = _faction_count(profile, 1)
    target_count = _faction_count(profile, 2)

    return [
        {"faction_id": 0, "count": brain_count, "x": 150.0, "y": 500.0, "spread": 60.0,
         "stats": _faction_stats(profile, 0)},
        {"faction_id": 1, "count": patrol_count, "x": 500.0, "y": 500.0, "spread": 40.0,
         "stats": _faction_stats(profile, 1)},
        {"faction_id": 2, "count": target_count, "x": 800.0, "y": 500.0, "spread": 80.0,
         "stats": _faction_stats(profile, 2)},
    ]


def get_spawns_for_stage(
    stage: int,
    rng=None,
    profile: GameProfile | None = None,
):
    """Dispatch to the correct spawn generator based on curriculum stage."""
    # Stage 1 only for now
    return get_stage1_spawns(profile=profile)
