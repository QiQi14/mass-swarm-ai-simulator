"""Observation and Action space definitions for SwarmEnv.

All dimensions are derived from the GameProfile contract.
No hardcoded constants — grid size, channel count, and action count
come from the profile.

Observation:
  N-channel density heatmaps (configurable)
  + terrain + summary stats

Action: Discrete(N) → MacroDirective mapping (N from profile)
"""

from __future__ import annotations

import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.config.game_profile import GameProfile


def make_observation_space(
    grid_width: int = 50,
    grid_height: int = 50,
    num_density_channels: int = 4,
) -> spaces.Dict:
    """Create observation space from profile dimensions.

    Args:
        grid_width: Grid width from profile.world.grid_width.
        grid_height: Grid height from profile.world.grid_height.
        num_density_channels: Number of density channels (brain, enemy, sub-factions).
    """
    obs = {}
    for ch in range(num_density_channels):
        obs[f"density_ch{ch}"] = spaces.Box(
            0.0, 1.0, shape=(grid_height, grid_width), dtype=np.float32
        )
    obs["terrain"] = spaces.Box(
        0.0, 1.0, shape=(grid_height, grid_width), dtype=np.float32
    )
    obs["summary"] = spaces.Box(0.0, 1.0, shape=(6,), dtype=np.float32)
    return spaces.Dict(obs)


def make_action_space(num_actions: int = 8) -> spaces.Discrete:
    """Create action space from profile action count."""
    return spaces.Discrete(num_actions)


def make_action_names(profile: GameProfile | None = None) -> dict[int, str]:
    """Build action index → name mapping from profile.

    Falls back to default names if no profile provided.
    """
    if profile is not None:
        return {a.index: a.name for a in profile.actions}
    return _DEFAULT_ACTION_NAMES.copy()


# Action index constants (stable across profiles — these are protocol indices)
ACTION_HOLD = 0
ACTION_UPDATE_NAV = 1
ACTION_ACTIVATE_BUFF = 2
ACTION_RETREAT = 3
ACTION_ZONE_MODIFIER = 4
ACTION_SPLIT_FACTION = 5
ACTION_MERGE_FACTION = 6
ACTION_SET_AGGRO_MASK = 7

# Grid defaults (overridden by profile)
GRID_WIDTH = 50
GRID_HEIGHT = 50
NUM_DENSITY_CHANNELS = 4

_DEFAULT_ACTION_NAMES = {
    ACTION_HOLD: "Hold",
    ACTION_UPDATE_NAV: "UpdateNavigation",
    ACTION_ACTIVATE_BUFF: "ActivateBuff",
    ACTION_RETREAT: "Retreat",
    ACTION_ZONE_MODIFIER: "SetZoneModifier",
    ACTION_SPLIT_FACTION: "SplitFaction",
    ACTION_MERGE_FACTION: "MergeFaction",
    ACTION_SET_AGGRO_MASK: "SetAggroMask",
}
