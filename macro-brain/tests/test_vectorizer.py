import pytest
import numpy as np
from gymnasium import spaces

from src.env.spaces import (
    make_observation_space,
    make_action_space,
    MAX_GRID_WIDTH,
    MAX_GRID_HEIGHT,
    NUM_CHANNELS,
    SUMMARY_DIM,
)
from src.utils.vectorizer import vectorize_snapshot
from src.utils.lkp_buffer import LKPBuffer


def test_imports():
    """Verify package imports work."""
    assert make_observation_space is not None
    assert make_action_space is not None


def test_observation_space_shape():
    """Verify observation space: 8 channels (50x50) + summary (12,)."""
    obs_space = make_observation_space()
    assert isinstance(obs_space, spaces.Dict)
    for i in range(NUM_CHANNELS):
        ch_space = obs_space[f"ch{i}"]
        assert isinstance(ch_space, spaces.Box)
        assert ch_space.shape == (MAX_GRID_HEIGHT, MAX_GRID_WIDTH)

    summary_space = obs_space["summary"]
    assert summary_space.shape == (SUMMARY_DIM,)


def test_action_space_is_multidiscrete():
    """Verify action space is MultiDiscrete([8, 2500])."""
    action_space = make_action_space()
    assert isinstance(action_space, spaces.MultiDiscrete)
    assert list(action_space.nvec) == [8, 2500]


def test_vectorizer_basic():
    """Verify vectorizer produces correct numpy arrays from mock snapshot."""
    grid_size = 50 * 50
    snapshot = {
        "density_maps": {
            "0": [0.5] * grid_size,     # Brain faction
            "1": [0.8] * grid_size,     # Enemy faction
        },
        "ecp_density_maps": {
            "1": [0.4] * grid_size,     # ECP for enemy
        },
        "terrain_hard": [32767] * grid_size,
        "summary": {
            "faction_counts": {"0": 1000, "1": 500},
            "faction_avg_stats": {"0": [10.0], "1": [8.0]},
        },
        "active_sub_factions": [100, 101],
        "active_zones": [{"target_faction": 0}],
    }

    result = vectorize_snapshot(snapshot, brain_faction=0, enemy_factions=1)

    # ch0: brain density
    assert "ch0" in result
    assert np.allclose(result["ch0"], 0.5)
    assert result["ch0"].shape == (50, 50)

    # ch1: unified enemy density
    assert "ch1" in result
    assert np.allclose(result["ch1"], 0.8)

    # ch2: reserved (zeroed)
    assert "ch2" in result
    assert np.allclose(result["ch2"], 0.0), "ch2 must be zeroed (reserved for future ally)"

    # ch4: terrain
    assert "ch4" in result
    assert np.allclose(result["ch4"], 32767 / 65535.0, atol=1e-4)

    # ch7: ECP density
    assert np.allclose(result["ch7"], 0.4)

    # summary
    assert "summary" in result
    assert result["summary"].shape == (SUMMARY_DIM,)


def test_unified_enemy_merges_all_factions():
    """Two enemy factions must be merged into a single ch1 heatmap."""
    grid_size = 50 * 50
    snapshot = {
        "density_maps": {
            "0": [0.1] * grid_size,     # Brain
            "1": [0.3] * grid_size,     # Enemy 1 (Trap)
            "2": [0.2] * grid_size,     # Enemy 2 (Target)
        },
        "summary": {
            "faction_counts": {"0": 50, "1": 50, "2": 20},
            "faction_avg_stats": {"0": [100.0], "1": [100.0], "2": [100.0]},
        },
    }

    result = vectorize_snapshot(
        snapshot, brain_faction=0, enemy_factions=[1, 2]
    )

    # ch1 should be 0.3 + 0.2 = 0.5 (merged)
    assert np.allclose(result["ch1"], 0.5), (
        f"ch1 should merge enemies: expected 0.5, got {result['ch1'].mean():.3f}"
    )

    # ch2 must remain zeroed
    assert np.allclose(result["ch2"], 0.0), "ch2 must be zeroed even with 2 enemy factions"


def test_ch2_always_zero_regardless_of_factions():
    """ch2 must be zero no matter how many enemy factions exist."""
    grid_size = 50 * 50
    snapshot = {
        "density_maps": {
            "0": [0.1] * grid_size,
            "1": [0.4] * grid_size,
            "2": [0.3] * grid_size,
            "3": [0.2] * grid_size,  # Sub-faction
        },
        "summary": {
            "faction_counts": {"0": 50, "1": 30, "2": 20},
            "faction_avg_stats": {},
        },
    }

    result = vectorize_snapshot(
        snapshot, brain_faction=0, enemy_factions=[1, 2]
    )

    # ch2 must be zero
    assert np.allclose(result["ch2"], 0.0)

    # ch3 should capture sub-faction 3 (not brain, not enemy)
    assert np.allclose(result["ch3"], 0.2)


def test_lkp_with_two_channels():
    """LKP buffer processes both raw density (ch1) and ECP (ch7) under fog."""
    grid_size = 50 * 50
    lkp = LKPBuffer(grid_h=50, grid_w=50, num_enemy_channels=2)

    # Fully visible fog
    snapshot = {
        "density_maps": {
            "0": [0.1] * grid_size,
            "1": [0.5] * grid_size,
        },
        "ecp_density_maps": {
            "1": [1.0] * grid_size,
        },
        "fog_explored": [1.0] * grid_size,
        "fog_visible": [1.0] * grid_size,
        "summary": {
            "faction_counts": {"0": 50, "1": 50},
            "faction_avg_stats": {},
        },
    }

    result = vectorize_snapshot(
        snapshot, brain_faction=0, enemy_factions=[1],
        fog_enabled=True, lkp_buffer=lkp,
    )

    # ch1 should have the ground truth density
    assert np.allclose(result["ch1"], 0.5)
    assert np.allclose(result["ch7"], 1.0)

    # Now simulate fog hiding everything
    snapshot2 = {
        "density_maps": {
            "0": [0.1] * grid_size,
            "1": [0.0] * grid_size,  # Enemy hidden by fog
        },
        "ecp_density_maps": {
            "1": [0.0] * grid_size,
        },
        "fog_explored": [1.0] * grid_size,
        "fog_visible": [0.0] * grid_size,  # All hidden
        "summary": {
            "faction_counts": {"0": 50, "1": 50},
            "faction_avg_stats": {},
        },
    }

    result2 = vectorize_snapshot(
        snapshot2, brain_faction=0, enemy_factions=[1],
        fog_enabled=True, lkp_buffer=lkp,
    )

    # LKP should retain decayed density, not zero
    assert result2["ch1"].max() > 0.0, "LKP should retain ghost trail for raw density"
    assert result2["ch7"].max() > 0.0, "LKP should retain ghost trail for ECP"


def test_ch7_ecp_density():
    """ch7 reflects ECP (HP × damage_mult)."""
    grid_size = 50 * 50
    snapshot = {
        "ecp_density_maps": {
            "1": [4000.0 / (50.0 * 100.0)] * grid_size,  # High ECP
        },
        "summary": {
            "faction_counts": {"1": 10},
            "faction_avg_stats": {"1": [100.0]},
        },
    }
    result = vectorize_snapshot(snapshot, enemy_factions=1)
    assert np.allclose(result["ch7"], 0.8)


def test_summary_no_faction_cheats():
    """Summary[6] and [7] are generalized HP metrics, not faction ID counts."""
    grid_size = 50 * 50
    snapshot = {
        "summary": {
            "faction_counts": {"0": 50, "1": 50, "2": 20},
            "faction_avg_stats": {
                "0": [100.0],
                "1": [100.0],
                "2": [50.0],
            },
        },
    }
    result = vectorize_snapshot(snapshot, brain_faction=0, enemy_factions=[1, 2], max_entities=100.0)
    
    # 50 own * 100 HP = 5000 HP. Max HP = 100 * 100 = 10000.
    assert np.allclose(result["summary"][6], 0.5)
    
    # Enemies: (50 * 100) + (20 * 50) = 6000 HP. Max HP = 100 * 100 = 10000.
    assert np.allclose(result["summary"][7], 0.6)


def test_center_padding():
    """Smaller active grid must be center-padded in 50x50 tensor."""
    active_w, active_h = 20, 20
    grid_size = active_w * active_h
    snapshot = {
        "density_maps": {
            "0": [1.0] * grid_size,
            "1": [0.5] * grid_size,
        },
        "summary": {
            "faction_counts": {"0": 40, "1": 20},
            "faction_avg_stats": {},
        },
    }

    result = vectorize_snapshot(
        snapshot, brain_faction=0, enemy_factions=[1],
        active_grid_w=active_w, active_grid_h=active_h,
    )

    pad_x = (50 - active_w) // 2   # 15
    pad_y = (50 - active_h) // 2   # 15

    # Active zone should have density
    active_slice = result["ch1"][pad_y:pad_y+active_h, pad_x:pad_x+active_w]
    assert np.allclose(active_slice, 0.5)

    # Padding should be zero for density
    assert result["ch1"][0, 0] == 0.0
    assert result["ch1"][49, 49] == 0.0
