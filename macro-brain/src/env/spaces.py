"""
Observation and Action space definitions for SwarmEnv.

Observation:
  4-channel density heatmaps (brain, enemy, sub-faction ×2)
  + terrain + summary stats

Action: Discrete(8) → MacroDirective mapping
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np

GRID_WIDTH = 50
GRID_HEIGHT = 50
NUM_DENSITY_CHANNELS = 4

# Action indices
ACTION_HOLD = 0
ACTION_UPDATE_NAV = 1
ACTION_FRENZY = 2
ACTION_RETREAT = 3
ACTION_ZONE_MODIFIER = 4
ACTION_SPLIT_FACTION = 5
ACTION_MERGE_FACTION = 6
ACTION_SET_AGGRO_MASK = 7

ACTION_NAMES = {
    ACTION_HOLD: "Hold",
    ACTION_UPDATE_NAV: "UpdateNavigation",
    ACTION_FRENZY: "TriggerFrenzy",
    ACTION_RETREAT: "Retreat",
    ACTION_ZONE_MODIFIER: "SetZoneModifier",
    ACTION_SPLIT_FACTION: "SplitFaction",
    ACTION_MERGE_FACTION: "MergeFaction",
    ACTION_SET_AGGRO_MASK: "SetAggroMask",
}

def make_observation_space() -> spaces.Dict:
    return spaces.Dict({
        "density_ch0": spaces.Box(0.0, 1.0, shape=(GRID_HEIGHT, GRID_WIDTH), dtype=np.float32),
        "density_ch1": spaces.Box(0.0, 1.0, shape=(GRID_HEIGHT, GRID_WIDTH), dtype=np.float32),
        "density_ch2": spaces.Box(0.0, 1.0, shape=(GRID_HEIGHT, GRID_WIDTH), dtype=np.float32),
        "density_ch3": spaces.Box(0.0, 1.0, shape=(GRID_HEIGHT, GRID_WIDTH), dtype=np.float32),
        "terrain": spaces.Box(0.0, 1.0, shape=(GRID_HEIGHT, GRID_WIDTH), dtype=np.float32),
        "summary": spaces.Box(0.0, 1.0, shape=(6,), dtype=np.float32),
    })

def make_action_space() -> spaces.Discrete:
    return spaces.Discrete(8)
