import pytest
import zmq
import json
from unittest.mock import MagicMock, patch
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from src.env.swarm_env import SwarmEnv

@pytest.fixture
def mock_zmq_context():
    with patch("zmq.Context") as mock_ctx:
        mock_socket = MagicMock()
        mock_ctx.return_value.socket.return_value = mock_socket
        
        # Mock reset responses (needs two recv_string calls)
        reset_snapshot_1 = json.dumps({
            "tick": 0,
            "density_maps": {"0": [0.0]*2500, "1": [0.0]*2500},
            "summary": {"faction_counts": {"0": 100, "1": 100}},
            "active_sub_factions": []
        })
        reset_snapshot_2 = json.dumps({
            "tick": 1,
            "density_maps": {"0": [0.0]*2500, "1": [0.0]*2500},
            "summary": {"faction_counts": {"0": 100, "1": 100}},
            "active_sub_factions": []
        })
        
        # Subsequent steps
        step_snapshot = json.dumps({
            "tick": 2,
            "density_maps": {"0": [0.0]*2500, "1": [0.0]*2500},
            "summary": {"faction_counts": {"0": 100, "1": 100}},
            "active_sub_factions": []
        })
        
        # We need a long list of side effects in case it learns multiple steps
        mock_socket.recv_string.side_effect = [reset_snapshot_1, reset_snapshot_2] + [step_snapshot]*500
        yield mock_ctx

def test_swarm_env_action_masks(mock_zmq_context):
    env = SwarmEnv(config={"curriculum_stage": 1})
    masks = env.action_masks()
    assert masks.shape == (8,)
    assert all(masks[0:4])
    assert not any(masks[4:8])
    
    env.curriculum_stage = 2
    masks = env.action_masks()
    assert masks[6] == False
    assert masks[7] == False

def test_maskable_ppo_initialization(mock_zmq_context):
    # Just checking it initializes and runs one step without crashing
    env = SwarmEnv()
    env = ActionMasker(env, lambda e: e.action_masks())
    
    model = MaskablePPO(
        "MultiInputPolicy",
        env,
        n_steps=16,
        batch_size=16
    )
    
    model.learn(total_timesteps=16)
    assert True
