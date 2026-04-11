"""Observation and Action space definitions for SwarmEnv.

Tactical curriculum spaces:
MultiDiscrete action space (8 actions + 2500 spatial coords).
Fixed 50x50 observation space with 8 channels + 12-dim summary.
"""

from __future__ import annotations

import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.config.game_profile import GameProfile


# 8-action vocabulary for tactical curriculum
ACTION_HOLD = 0
ACTION_ATTACK_COORD = 1
ACTION_DROP_PHEROMONE = 2
ACTION_DROP_REPELLENT = 3
ACTION_SPLIT_TO_COORD = 4
ACTION_MERGE_BACK = 5
ACTION_RETREAT = 6
ACTION_SCOUT = 7

ACTION_NAMES = [
    "Hold", "AttackCoord", "DropPheromone", "DropRepellent",
    "SplitToCoord", "MergeBack", "Retreat", "Scout",
]

# Which actions use spatial coordinates (component 1)
SPATIAL_ACTIONS = {
    ACTION_ATTACK_COORD, ACTION_DROP_PHEROMONE, ACTION_DROP_REPELLENT,
    ACTION_SPLIT_TO_COORD, ACTION_RETREAT, ACTION_SCOUT,
}

# Grid constants — observation always 50×50 regardless of map size
MAX_GRID_WIDTH = 50
MAX_GRID_HEIGHT = 50
MAX_GRID_CELLS = MAX_GRID_WIDTH * MAX_GRID_HEIGHT  # 2500
NUM_CHANNELS = 8
SUMMARY_DIM = 12


def make_observation_space(
    grid_width: int = 50,
    grid_height: int = 50,
) -> spaces.Dict:
    """Fixed 50×50 observation space. 8 grid channels + 12-dim summary.
    
    Channels:
      ch0: brain density
      ch1: unified enemy density (ALL enemies merged, fog-gated + LKP)
      ch2: reserved (zeroed) — future ally density for multiplayer
      ch3: sub-factions aggregated
      ch4: terrain (0=pass, 1=wall; padding=1.0)
      ch5: fog explored (0=unexplored, 1=explored; padding=1.0)
      ch6: fog visible (0=hidden, 1=visible; padding=1.0)
      ch7: threat density (Effective Combat Power)
    """
    obs = {}
    for ch in range(8):
        obs[f"ch{ch}"] = spaces.Box(
            0.0, 1.0, shape=(grid_height, grid_width), dtype=np.float32
        )
    obs["summary"] = spaces.Box(0.0, 1.0, shape=(12,), dtype=np.float32)
    return spaces.Dict(obs)


def make_action_space(num_actions: int = 8, max_grid_cells: int = 2500) -> spaces.MultiDiscrete:
    """Create MultiDiscrete action space: [action_type, flat_spatial_coord].
    
    Component 0: Action type (8 discrete actions)
    Component 1: Flattened grid coordinate (50×50 = 2500 cells)
        Decode: grid_x = val % 50, grid_y = val // 50
    """
    return spaces.MultiDiscrete([num_actions, max_grid_cells])


def make_action_names() -> dict[int, str]:
    return {i: name for i, name in enumerate(ACTION_NAMES)}


def decode_spatial(flat_index: int, grid_width: int = MAX_GRID_WIDTH) -> tuple[int, int]:
    """Decode flattened spatial coordinate to (grid_x, grid_y)."""
    grid_x = flat_index % grid_width
    grid_y = flat_index // grid_width
    return grid_x, grid_y

def grid_to_world(grid_x: int, grid_y: int, cell_size: float = 20.0,
                  offset_x: float = 0.0, offset_y: float = 0.0) -> tuple[float, float]:
    """Convert grid cell to world coordinates (cell center).
    
    offset_x/y: padding offset for center-padded maps.
    """
    world_x = (grid_x - offset_x) * cell_size + cell_size / 2.0
    world_y = (grid_y - offset_y) * cell_size + cell_size / 2.0
    return world_x, world_y

def make_coordinate_mask(
    active_grid_w: int, active_grid_h: int,
    max_grid_w: int = MAX_GRID_WIDTH, max_grid_h: int = MAX_GRID_HEIGHT,
) -> np.ndarray:
    """Create coordinate mask for the active arena within the padded tensor.
    
    Active arena is centered in the max grid. Only active cells are True.
    """
    mask = np.zeros(max_grid_w * max_grid_h, dtype=bool)
    pad_x = (max_grid_w - active_grid_w) // 2
    pad_y = (max_grid_h - active_grid_h) // 2
    for gy in range(active_grid_h):
        row = pad_y + gy
        start = row * max_grid_w + pad_x
        mask[start : start + active_grid_w] = True
    return mask
