import pytest
import numpy as np
from gymnasium import spaces

from src.env.spaces import (
    make_action_space,
    make_observation_space,
    decode_spatial,
    grid_to_world,
    make_coordinate_mask,
    SPATIAL_ACTIONS,
    ACTION_NAMES,
)

def test_make_action_space():
    space = make_action_space()
    assert isinstance(space, spaces.MultiDiscrete)
    assert list(space.nvec) == [8, 2500]

def test_make_observation_space():
    space = make_observation_space()
    assert isinstance(space, spaces.Dict)
    # Check for 8 boxes + 1 summary box
    for ch in range(8):
        ch_space = space[f"ch{ch}"]
        assert isinstance(ch_space, spaces.Box)
        assert ch_space.shape == (50, 50)
    
    summary_space = space["summary"]
    assert isinstance(summary_space, spaces.Box)
    assert summary_space.shape == (12,)

def test_decode_spatial():
    assert decode_spatial(125) == (25, 2)
    assert decode_spatial(0) == (0, 0)
    assert decode_spatial(2499) == (49, 49)

def test_make_coordinate_mask():
    mask = make_coordinate_mask(25, 25)
    # the mask should have 625 True entries
    assert mask.sum() == 625

def test_grid_to_world():
    # default grid_world should be cell size 20, center is 10,10 for 0,0
    assert grid_to_world(0, 0, cell_size=20) == (10.0, 10.0)

def test_spatial_actions():
    assert SPATIAL_ACTIONS == {1, 2, 3, 4, 6, 7}
    
def test_action_names():
    assert len(ACTION_NAMES) == 8
