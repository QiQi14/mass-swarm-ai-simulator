"""
Tests for SwarmEnv and its action mappings.
"""
from unittest.mock import MagicMock, patch
import pytest
import numpy as np
import json

from src.env.swarm_env import SwarmEnv
from src.env.spaces import MAX_GRID_WIDTH, MAX_GRID_HEIGHT, MAX_GRID_CELLS

def make_dummy_snapshot():
    return {
        "type": "state_snapshot",
        "tick": 1,
        "active_sub_factions": [],
        "density_maps": {
            "0": np.zeros(2500).tolist()
        },
        "summary": {
            "faction_counts": {"0": 10},
            "faction_avg_stats": {}
        }
    }

class DummyMapConfig:
    active_grid_w = 40
    active_grid_h = 40
    cell_size = 20.0
    fog_enabled = True

@pytest.fixture
def mock_env():
    with patch("zmq.Context"):
        env = SwarmEnv()
        env._socket = MagicMock()
        return env

def test_action_masks_length_and_merge_block(mock_env):
    # Length should be 8 + 2500 = 2508
    mask = mock_env.action_masks()
    assert len(mask) == 2508
    # No sub_factions, so MergeBack (5) blocked
    assert mask[5] == False
    
def test_action_masks_split_scout_blocked(mock_env):
    mock_env._active_sub_factions = [101, 102]
    mask = mock_env.action_masks()
    assert mask[4] == False # SplitToCoord
    assert mask[7] == False # Scout
    
def test_action_masks_stage_locked(mock_env):
    mock_env.curriculum_stage = 1
    mask = mock_env.action_masks()
    assert mask[0] == True # Hold
    assert mask[1] == True # AttackCoord
    assert mask[2] == False # DropPheromone
    
    # Coordinate mask active cells
    active_cells = sum(mask[8:])
    assert active_cells == mock_env._active_grid_w * mock_env._active_grid_h

def test_step_accepts_multidiscrete_without_crash(mock_env):
    mock_env._active_sub_factions = []
    mock_env._last_snapshot = make_dummy_snapshot()
    mock_env._socket.recv_string.return_value = json.dumps(make_dummy_snapshot())
    
    action = np.array([0, 1500]) # Hold, center
    obs, reward, terminated, truncated, info = mock_env.step(action)
    
    assert "summary" in obs
    assert "ch0" in obs
    assert isinstance(reward, float)

def test_observation_dict_keys(mock_env):
    obs_space = mock_env.observation_space
    assert "summary" in obs_space.spaces
    for i in range(8):
        assert f"ch{i}" in obs_space.spaces
        assert obs_space.spaces[f"ch{i}"].shape == (MAX_GRID_HEIGHT, MAX_GRID_WIDTH)
    assert obs_space.spaces["summary"].shape == (12,)

@patch('src.utils.terrain_generator.generate_terrain_for_stage')
@patch('src.training.curriculum.get_spawns_for_stage')
@patch('src.training.curriculum.get_map_config')
def test_reset_clears_state_and_lkp(mock_map_config, mock_spawns, mock_terrain, mock_env):
    mock_env._prev_fog_explored = np.ones((50,50))
    
    mock_map_config.return_value = DummyMapConfig()
    mock_spawns.return_value = ([{"faction_id": 2, "x": 100, "y": 100, "count": 1}], {"target_faction": 2, "trap_faction": 1})
    mock_terrain.return_value = []
    
    mock_env._socket.recv_string.return_value = json.dumps(make_dummy_snapshot())
    
    with patch.object(mock_env._lkp_buffer, 'reset') as mock_lkp_reset:
        obs, _ = mock_env.reset()
        mock_lkp_reset.assert_called_once()
        
    assert mock_env._prev_fog_explored is None
    assert mock_env._active_grid_w == 40
    assert mock_env._fog_enabled == True



@patch('src.env.swarm_env.vectorize_snapshot')
def test_fog_enabled_stages_produce_lkp(mock_vectorize, mock_env):
    mock_env._fog_enabled = True
    mock_env._last_snapshot = make_dummy_snapshot()
    mock_env._socket.recv_string.return_value = json.dumps(make_dummy_snapshot())
    
    mock_vectorize.return_value = {"ch0": np.zeros((50,50)), "summary": np.zeros(12)}
    
    action = np.array([0, 1500])
    mock_env.step(action)
    
    # Assert vectorize_snapshot was called with fog_enabled=True and lkp_buffer
    kwargs = mock_vectorize.call_args.kwargs
    assert kwargs["fog_enabled"] == True
    assert kwargs["lkp_buffer"] == mock_env._lkp_buffer
