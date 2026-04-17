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
ACTION_ZONE_MODIFIER = 2      # merged Pheromone + Repellent
ACTION_SPLIT_TO_COORD = 3
ACTION_MERGE_BACK = 4
ACTION_SET_PLAYSTYLE = 5      # NEW
ACTION_ACTIVATE_SKILL = 6
ACTION_RETREAT = 7

NUM_ACTIONS = 8
MODIFIER_DIM = 4              # modifier values 0-3

ACTION_NAMES = [
    "Hold", "AttackCoord", "ZoneModifier", "SplitToCoord",
    "MergeBack", "SetPlaystyle", "ActivateSkill", "Retreat"
]

# Which actions use spatial coordinates (component 1)
SPATIAL_ACTIONS = {
    ACTION_ATTACK_COORD, ACTION_ZONE_MODIFIER, ACTION_SPLIT_TO_COORD, 
    ACTION_RETREAT, ACTION_ACTIVATE_SKILL,
}

MODIFIER_MASKS = {
    ACTION_HOLD: [True, False, False, False],          # only mod=0
    ACTION_ATTACK_COORD: [True, False, False, False],  # only mod=0
    ACTION_ZONE_MODIFIER: [True, True, False, False],  # 0=attract, 1=repel
    ACTION_SPLIT_TO_COORD: [True, True, True, True],   # 0=all, 1/2/3=class
    ACTION_MERGE_BACK: [True, False, False, False],
    ACTION_SET_PLAYSTYLE: [True, True, True, True],    # 0=aggro, 1=passive, 2=kite, 3=clear
    ACTION_ACTIVATE_SKILL: [True, True, True, True],   # skill index 0-3
    ACTION_RETREAT: [True, False, False, False],
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
    
    Channels (v4.0 — 3 logical blocks):
      🟦 Force Picture:
        ch0: all friendly count density (brain + sub-factions merged)
        ch1: all enemy count density (ALL enemies merged, fog-gated + LKP)
        ch2: all friendly ECP density (brain + sub-factions merged)
        ch3: all enemy ECP density (ALL enemies merged, fog-gated + LKP)
      🟩 Environment:
        ch4: terrain cost (base + zone modifiers, 0=pass, 1=wall; padding=1.0)
        ch5: fog awareness (merged: 0.0=unknown, 0.5=explored, 1.0=visible)
      🟨 Tactical (plumbed as zeros):
        ch6: interactable terrain overlay (future)
        ch7: system objective signal (future)
    """
    obs = {}
    for ch in range(8):
        obs[f"ch{ch}"] = spaces.Box(
            0.0, 1.0, shape=(grid_height, grid_width), dtype=np.float32
        )
    obs["summary"] = spaces.Box(0.0, 1.0, shape=(12,), dtype=np.float32)
    return spaces.Dict(obs)


def make_action_space(num_actions: int = 8, max_grid_cells: int = 2500, modifier_dim: int = 4) -> spaces.MultiDiscrete:
    """Create MultiDiscrete action space: [action_type, flat_spatial_coord, modifier].
    
    Component 0: Action type (8 discrete actions)
    Component 1: Flattened grid coordinate (50×50 = 2500 cells)
        Decode: grid_x = val % 50, grid_y = val // 50
    Component 2: Modifier value (e.g. class filter, polarity)
    """
    return spaces.MultiDiscrete([num_actions, max_grid_cells, modifier_dim])


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
