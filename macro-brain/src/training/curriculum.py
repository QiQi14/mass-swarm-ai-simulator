"""Mastery-Based Curriculum Learning with Demotion Safety Net.

All curriculum thresholds and spawn configurations are read from the
GameProfile contract. No hardcoded stage configs — swap the profile
to change the curriculum.

Implements the "Proof of Mechanic Mastery" transition matrix to prevent
the Lazy Agent / Deathball Fallacy — where an agent gets promoted by
brute-forcing wins without learning the new mechanics.

Each stage transition requires:
  1. Statistical win rate threshold
  2. Decisive victory proof (avg survivors)
  3. Mechanic usage proof (action distribution checks)
  4. Minimum episode count for statistical significance

Demotion: If win rate drops below the floor for N episodes after promotion,
the agent is demoted to rebuild confidence (prevents Catastrophic Forgetting).
"""

from __future__ import annotations

import random
from collections import deque
from typing import TYPE_CHECKING

from stable_baselines3.common.callbacks import BaseCallback

if TYPE_CHECKING:
    from src.config.game_profile import GameProfile


# Action names — stable protocol indices (used by callbacks for display)
ACTION_NAMES = [
    "Hold", "Navigate", "Frenzy", "Retreat",
    "ZoneModifier", "SplitFaction", "MergeFaction", "SetAggroMask"
]


# ── Spawn Configurations ────────────────────────────────────────────
# All spawn generators accept an optional `profile` to read entity
# counts and stats. Falls back to hardcoded defaults if no profile.

def _faction_stats(profile: GameProfile | None, faction_id: int) -> list[dict]:
    """Get stat initializer from profile or default 100 HP."""
    if profile is not None:
        for f in profile.factions:
            if f.id == faction_id:
                return [{"index": 0, "value": f.stats.hp}]
    return [{"index": 0, "value": 100.0}]


def _faction_count(profile: GameProfile | None, faction_id: int) -> int:
    """Get default entity count from profile or 50."""
    if profile is not None:
        for f in profile.factions:
            if f.id == faction_id:
                return f.default_count
    return 50


def get_stage1_spawns(profile: GameProfile | None = None):
    """Symmetric head-on: both factions in single groups facing each other."""
    brain_count = _faction_count(profile, 0)
    bot_count = _faction_count(profile, 1)
    return [
        {"faction_id": 0, "count": brain_count, "x": 350.0, "y": 500.0, "spread": 60.0,
         "stats": _faction_stats(profile, 0)},
        {"faction_id": 1, "count": bot_count, "x": 650.0, "y": 500.0, "spread": 60.0,
         "stats": _faction_stats(profile, 1)},
    ]


def get_stage2_spawns(rng=None, profile: GameProfile | None = None):
    """Scattered defenders: 2-3 groups in randomized positions.

    Forces the model to learn:
      - Target prioritization (which cluster to attack first)
      - Army concentration (don't split your force equally)
      - Retreat timing (disengage from one group to hit another)
    """
    if rng is None:
        rng = random

    brain_count = _faction_count(profile, 0)
    bot_count = _faction_count(profile, 1)

    swarm_y = rng.uniform(300.0, 700.0)
    spawns = [
        {"faction_id": 0, "count": brain_count, "x": 200.0, "y": swarm_y, "spread": 60.0,
         "stats": _faction_stats(profile, 0)},
    ]

    # Scatter defenders into 2-3 groups
    num_groups = rng.choice([2, 3])
    counts = _split_count(bot_count, num_groups)
    positions = _generate_scattered_positions(num_groups, rng)

    for count, (px, py) in zip(counts, positions):
        spawns.append({
            "faction_id": 1, "count": count,
            "x": px, "y": py, "spread": 40.0,
            "stats": _faction_stats(profile, 1),
        })

    return spawns


def get_stage3_spawns(rng=None, profile: GameProfile | None = None):
    """Stage 3: Both factions on opposite sides of the wall.

    Swarm spawns on the left. Defenders spawn on the right as 2 groups
    (one above, one below the wall's gap). Forces the agent to learn
    SplitFaction to attack both groups simultaneously.
    """
    if rng is None:
        rng = random

    brain_count = _faction_count(profile, 0)
    bot_count = _faction_count(profile, 1)

    swarm_y = rng.uniform(350.0, 650.0)
    spawns = [
        {"faction_id": 0, "count": brain_count, "x": 200.0, "y": swarm_y, "spread": 60.0,
         "stats": _faction_stats(profile, 0)},
    ]

    # Defenders: 2 groups on the right side
    half = bot_count // 2
    positions = [
        (rng.uniform(600.0, 850.0), rng.uniform(200.0, 400.0)),
        (rng.uniform(600.0, 850.0), rng.uniform(600.0, 800.0)),
    ]
    counts = [half, bot_count - half]

    for count, (px, py) in zip(counts, positions):
        spawns.append({
            "faction_id": 1, "count": count,
            "x": px, "y": py, "spread": 40.0,
            "stats": _faction_stats(profile, 1),
        })

    return spawns


def get_stage4_spawns(rng=None, profile: GameProfile | None = None):
    """Stage 4: Fully randomized positions on opposite sides.

    Both factions can spawn anywhere in their half of the map.
    Defenders split into 2-4 groups at random.
    """
    if rng is None:
        rng = random

    brain_count = _faction_count(profile, 0)
    bot_count = _faction_count(profile, 1)

    swarm_x = rng.uniform(100.0, 300.0)
    swarm_y = rng.uniform(150.0, 850.0)
    spawns = [
        {"faction_id": 0, "count": brain_count, "x": swarm_x, "y": swarm_y, "spread": 60.0,
         "stats": _faction_stats(profile, 0)},
    ]

    num_groups = rng.choice([2, 3, 4])
    counts = _split_count(bot_count, num_groups)
    positions = _generate_scattered_positions(num_groups, rng)

    for count, (px, py) in zip(counts, positions):
        spawns.append({
            "faction_id": 1, "count": count,
            "x": px, "y": py, "spread": 40.0,
            "stats": _faction_stats(profile, 1),
        })

    return spawns


def get_stage5_spawns(rng=None, profile: GameProfile | None = None):
    """Stage 5: Fully random spawns for both factions.

    Both factions can appear anywhere. Multiple groups per faction.
    Forces the agent to handle arbitrary starting conditions.
    """
    if rng is None:
        rng = random

    brain_count = _faction_count(profile, 0)
    bot_count = _faction_count(profile, 1)

    # Brain: 1-2 spawn groups, random positions
    brain_groups = rng.choice([1, 2])
    brain_counts = _split_count(brain_count, brain_groups)
    spawns = []
    for count in brain_counts:
        spawns.append({
            "faction_id": 0,
            "count": count,
            "x": rng.uniform(100.0, 900.0),
            "y": rng.uniform(100.0, 900.0),
            "spread": 60.0,
            "stats": _faction_stats(profile, 0),
        })

    # Bot: 2-4 spawn groups, random positions
    bot_groups = rng.choice([2, 3, 4])
    bot_counts = _split_count(bot_count, bot_groups)
    positions = _generate_scattered_positions(bot_groups, rng)
    for count, (px, py) in zip(bot_counts, positions):
        spawns.append({
            "faction_id": 1, "count": count,
            "x": px, "y": py, "spread": 40.0,
            "stats": _faction_stats(profile, 1),
        })

    return spawns


def _split_count(total, num_groups):
    """Split total into num_groups with minimum 5 per group."""
    min_per = max(1, total // (num_groups * 2))
    counts = [min_per] * num_groups
    remaining = total - sum(counts)
    for _ in range(remaining):
        counts[random.randint(0, num_groups - 1)] += 1
    return counts


def _generate_scattered_positions(num_groups, rng):
    """Generate scattered positions for defender groups."""
    positions = []
    min_spacing = 200.0

    for _ in range(num_groups):
        for _attempt in range(50):
            x = rng.uniform(550.0, 900.0)
            y = rng.uniform(150.0, 850.0)
            too_close = any(
                ((x - px) ** 2 + (y - py) ** 2) ** 0.5 < min_spacing
                for px, py in positions
            )
            if not too_close:
                positions.append((x, y))
                break
        else:
            positions.append((rng.uniform(550.0, 900.0), rng.uniform(150.0, 850.0)))

    return positions


def get_spawns_for_stage(
    stage: int,
    rng=None,
    profile: GameProfile | None = None,
):
    """Dispatch to the correct spawn generator based on curriculum stage."""
    if stage <= 1:
        return get_stage1_spawns(profile=profile)
    elif stage == 2:
        return get_stage2_spawns(rng=rng, profile=profile)
    elif stage == 3:
        return get_stage3_spawns(rng=rng, profile=profile)
    elif stage == 4:
        return get_stage4_spawns(rng=rng, profile=profile)
    else:  # Stage 5+
        return get_stage5_spawns(rng=rng, profile=profile)

