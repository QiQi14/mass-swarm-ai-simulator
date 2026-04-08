"""
Tests for SwarmEnv and its action mappings.
"""
from unittest.mock import MagicMock, patch
import pytest
import numpy as np
import json

from src.env.swarm_env import SwarmEnv
from src.env.spaces import (
    ACTION_HOLD, ACTION_UPDATE_NAV, ACTION_ACTIVATE_BUFF, ACTION_RETREAT,
    ACTION_ZONE_MODIFIER, ACTION_SPLIT_FACTION, ACTION_MERGE_FACTION,
    ACTION_SET_AGGRO_MASK, GRID_WIDTH, GRID_HEIGHT
)

@pytest.fixture
def mock_env():
    with patch("zmq.Context"):
        env = SwarmEnv()
        env._socket = MagicMock()
        return env

def test_action_to_directive_hold(mock_env):
    directive = mock_env._action_to_directive(ACTION_HOLD)
    assert directive == {"type": "macro_directive", "directive": "Hold"}

def test_action_to_directive_update_nav(mock_env):
    directive = mock_env._action_to_directive(ACTION_UPDATE_NAV)
    assert directive == {
        "type": "macro_directive",
        "directive": "UpdateNavigation",
        "follower_faction": mock_env.brain_faction,
        "target": {"type": "Faction", "faction_id": mock_env.enemy_faction},
    }

def test_action_to_directive_activate_buff(mock_env):
    directive = mock_env._action_to_directive(ACTION_ACTIVATE_BUFF)
    assert directive == {
        "type": "macro_directive",
        "directive": "ActivateBuff",
        "faction": mock_env.brain_faction,
        "modifiers": [
            {"stat_index": 1, "modifier_type": "Multiplier", "value": 1.5},
            {"stat_index": 2, "modifier_type": "Multiplier", "value": 1.5}
        ],
        "duration_ticks": 60,
        "targets": []
    }

def test_action_to_directive_retreat(mock_env):
    # With no snapshot, both centroids = (500,500) → overlap fallback: dx=1, dy=0
    # retreat_x = clamp(500 + 200, 50, 950) = 700.0
    # retreat_y = clamp(500 + 0, 50, 950)   = 500.0
    directive = mock_env._action_to_directive(ACTION_RETREAT)
    assert directive == {
        "type": "macro_directive",
        "directive": "Retreat",
        "faction": mock_env.brain_faction,
        "retreat_x": 700.0,
        "retreat_y": 500.0,
    }

@patch.object(SwarmEnv, "_get_density_centroid")
def test_action_to_directive_zone_modifier(mock_centroid, mock_env):
    mock_centroid.return_value = (300.0, 400.0)
    directive = mock_env._action_to_directive(ACTION_ZONE_MODIFIER)
    assert directive == {
        "type": "macro_directive",
        "directive": "SetZoneModifier",
        "target_faction": mock_env.brain_faction,
        "x": 300.0,
        "y": 400.0,
        "radius": 100.0,
        "cost_modifier": -50.0,
    }

@patch.object(SwarmEnv, "_get_density_centroid")
def test_action_to_directive_split_faction(mock_centroid, mock_env):
    mock_centroid.return_value = (300.0, 400.0)
    mock_env._active_sub_factions = [101, 102]
    directive = mock_env._action_to_directive(ACTION_SPLIT_FACTION)
    assert directive == {
        "type": "macro_directive",
        "directive": "SplitFaction",
        "source_faction": mock_env.brain_faction,
        "new_sub_faction": 103,
        "percentage": 0.3,
        "epicenter": [400.0, 500.0],
    }

def test_action_to_directive_merge_faction_no_sub(mock_env):
    mock_env._active_sub_factions = []
    directive = mock_env._action_to_directive(ACTION_MERGE_FACTION)
    assert directive == {"type": "macro_directive", "directive": "Hold"}

def test_action_to_directive_merge_faction_with_sub(mock_env):
    mock_env._active_sub_factions = [101, 102]
    directive = mock_env._action_to_directive(ACTION_MERGE_FACTION)
    assert directive == {
        "type": "macro_directive",
        "directive": "MergeFaction",
        "source_faction": 102,
        "target_faction": mock_env.brain_faction,
    }

def test_action_to_directive_aggro_mask_toggle(mock_env):
    mock_env._active_sub_factions = [101]
    mock_env._last_aggro_state = True
    directive = mock_env._action_to_directive(ACTION_SET_AGGRO_MASK)
    assert not mock_env._last_aggro_state
    assert directive == {
        "type": "macro_directive",
        "directive": "SetAggroMask",
        "source_faction": 101,
        "target_faction": mock_env.enemy_faction,
        "allow_combat": False,
    }

def test_patch6_dynamic_epicenter_uses_centroid(mock_env):
    """Regression test for P6: dynamic epicenter"""
    density = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.float32)
    density[10, 10] = 1.0
    
    mock_env._last_snapshot = {
        "density_maps": {
            str(mock_env.brain_faction): density.flatten().tolist()
        }
    }
    
    mock_env._active_sub_factions = []
    directive = mock_env._action_to_directive(ACTION_SPLIT_FACTION)
    assert directive["epicenter"] == [300.0, 300.0]

def test_patch7_sub_factions_from_snapshot(mock_env):
    """Regression test for P7: sub-factions from ground truth"""
    mock_env._last_snapshot = {"active_sub_factions": [101, 105]}
    mock_env._socket.recv_string.return_value = json.dumps({"type": "state_snapshot", "active_sub_factions": [101, 105], "summary": {}, "density_maps": {}})
    mock_env.step(ACTION_HOLD)
    assert mock_env._active_sub_factions == [101, 105]

def test_patch7_split_id_from_ground_truth(mock_env):
    """Regression test for P7: dynamically split id"""
    mock_env._active_sub_factions = [101, 102]
    directive = mock_env._action_to_directive(ACTION_SPLIT_FACTION)
    assert directive["new_sub_faction"] == 103

def test_density_centroid_empty_map(mock_env):
    """Density centroid without specific data should return center"""
    mock_env._last_snapshot = {}
    cx, cy = mock_env._get_density_centroid(mock_env.brain_faction)
    assert cx == 500.0
    assert cy == 500.0

def test_density_centroid_concentration(mock_env):
    """Density centroid calculates correctly"""
    density = np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.float32)
    density[40, 20] = 1.0
    mock_env._last_snapshot = {
         "density_maps": {str(mock_env.brain_faction): density.flatten().tolist()}
    }
    cx, cy = mock_env._get_density_centroid(mock_env.brain_faction)
    assert cx == 400.0
    assert cy == 800.0

def test_patch8_intervention_swallowing(mock_env):
    """Test that intervention ticks are swallowed correctly."""
    mock_env._active_sub_factions = []
    
    # Mock recv_string to return intervention first, then normal tick
    mock_env._socket.recv_string.side_effect = [
        json.dumps({"type": "state_snapshot", "tick": 0, "summary": {}, "density_maps": {}}),
        json.dumps({"tick": 1, "type": "intervention", "intervention_active": True}),
        json.dumps({"tick": 2, "type": "state_snapshot", "intervention_active": False, "summary": {}, "density_maps": {}})
    ]
    
    mock_env.step(ACTION_HOLD)
    
    assert mock_env._socket.send_string.call_count == 2
    args1, _ = mock_env._socket.send_string.call_args_list[0]
    batch1 = json.loads(args1[0])
    assert batch1["type"] == "macro_directives"
    assert batch1["directives"][0] == {"type": "macro_directive", "directive": "Hold"}
    
    args2, _ = mock_env._socket.send_string.call_args_list[1]
    batch2 = json.loads(args2[0])
    assert batch2["type"] == "macro_directives"
    assert batch2["directives"][0] == {"directive": "Hold"}
    assert batch2["directives"][1] == {"directive": "Hold"}

def test_patch8_zmq_timeout_truncates(mock_env):
    """Test that zmq timeout raises error and truncates."""
    import zmq
    mock_env._socket.recv_string.side_effect = zmq.error.Again()
    mock_env.observation_space.sample = MagicMock(return_value={})
    
    obs, reward, terminated, truncated, info = mock_env.step(ACTION_HOLD)
    
    assert truncated is True
    assert terminated is False
    assert info == {"zmq_timeout": True}
