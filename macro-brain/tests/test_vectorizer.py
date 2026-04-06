import pytest
import numpy as np
from gymnasium import spaces

from src.env.spaces import (
    make_observation_space,
    make_action_space,
    GRID_WIDTH,
    GRID_HEIGHT,
    NUM_DENSITY_CHANNELS,
)
from src.utils.vectorizer import vectorize_snapshot

def test_imports():
    """Verify package imports work."""
    assert make_observation_space is not None
    assert make_action_space is not None

def test_observation_space_shape():
    """Verify Observation space shape matches (50x50 per channel)."""
    obs_space = make_observation_space()
    assert isinstance(obs_space, spaces.Dict)
    for i in range(NUM_DENSITY_CHANNELS):
        ch_space = obs_space[f"density_ch{i}"]
        assert isinstance(ch_space, spaces.Box)
        assert ch_space.shape == (GRID_HEIGHT, GRID_WIDTH)
    
    terrain_space = obs_space["terrain"]
    assert terrain_space.shape == (GRID_HEIGHT, GRID_WIDTH)
    
    summary_space = obs_space["summary"]
    assert summary_space.shape == (6,)

def test_action_space_is_discrete_8():
    """Verify Action space is Discrete(8)."""
    action_space = make_action_space()
    assert isinstance(action_space, spaces.Discrete)
    assert action_space.n == 8

def test_vectorizer_produces_correct_numpy_arrays():
    """Verify Vectorizer produces correct numpy arrays from mock snapshot."""
    grid_size = GRID_HEIGHT * GRID_WIDTH
    snapshot = {
        "density_maps": {
            "0": [0.5] * grid_size,     # Brain faction
            "1": [0.8] * grid_size,     # Enemy faction
        },
        "terrain_hard": [32767] * grid_size, # ~0.5 normalized
        "summary": {
            "faction_counts": {"0": 1000, "1": 500},
            "faction_avg_stats": {"0": [10.0], "1": [8.0]}
        },
        "active_sub_factions": [100, 101],
        "active_zones": [{"target_faction": 0}],
    }
    
    result = vectorize_snapshot(snapshot, brain_faction=0, enemy_faction=1)
    
    assert "density_ch0" in result
    assert np.allclose(result["density_ch0"], 0.5)
    assert result["density_ch0"].shape == (GRID_HEIGHT, GRID_WIDTH)
    
    assert "density_ch1" in result
    assert np.allclose(result["density_ch1"], 0.8)
    
    assert "terrain" in result
    assert np.allclose(result["terrain"], 32767 / 65535.0, atol=1e-4)
    
    assert "summary" in result
    assert result["summary"].shape == (6,)
    assert np.allclose(result["summary"][0], 1000 / 10000.0) # own_count
    assert np.allclose(result["summary"][1], 500 / 10000.0)  # enemy_count
    assert np.allclose(result["summary"][2], 10.0)           # own_health
    assert np.allclose(result["summary"][3], 8.0)            # enemy_health
    assert np.allclose(result["summary"][4], 2 / 5.0)        # sub_faction_count
    assert np.allclose(result["summary"][5], 1 / 10.0)       # active_zones_count

def test_sub_faction_overflow():
    """Verify that Sub-faction overflow aggregates into ch3."""
    grid_size = GRID_HEIGHT * GRID_WIDTH
    # Brain: 0, Enemy: 1
    # Sub-factions: 2, 3, 4
    # 2 goes to ch2
    # 3 and 4 go to ch3 (overflow)
    snapshot = {
        "density_maps": {
            "0": [0.1] * grid_size,
            "1": [0.1] * grid_size,
            "2": [0.2] * grid_size,
            "3": [0.3] * grid_size,
            "4": [0.4] * grid_size,
        }
    }
    
    result = vectorize_snapshot(snapshot, brain_faction=0, enemy_faction=1)
    
    # Check ch2 is exactly sub-faction 2
    assert np.allclose(result["density_ch2"], 0.2)
    # Check ch3 is sub-faction 3 + sub-faction 4 (0.3 + 0.4 = 0.7)
    assert np.allclose(result["density_ch3"], 0.7)
