import pytest
import zmq
import json
from unittest.mock import MagicMock, patch
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from src.env.swarm_env import SwarmEnv

def _make_snapshot(tick=0, own=100, enemy=100):
    """Helper to create a valid mock snapshot."""
    return json.dumps({
        "type": "state_snapshot",
        "tick": tick,
        "density_maps": {"0": [0.0]*2500, "1": [0.0]*2500},
        "summary": {"faction_counts": {"0": own, "1": enemy}},
        "active_sub_factions": [],
    })

@pytest.fixture
def mock_zmq_context():
    with patch("zmq.Context") as mock_ctx:
        mock_socket = MagicMock()
        mock_ctx.return_value.socket.return_value = mock_socket

        # Use a function side_effect for infinite responses
        call_count = [0]
        def recv_side_effect():
            call_count[0] += 1
            return _make_snapshot(tick=call_count[0])

        mock_socket.recv_string.side_effect = recv_side_effect
        yield mock_ctx

def test_swarm_env_action_masks(mock_zmq_context):
    env = SwarmEnv(config={"curriculum_stage": 1})
    masks = env.action_masks()
    assert masks.shape == (2512,)
    assert all(masks[0:2])
    assert not any(masks[2:8])

    env.curriculum_stage = 2
    masks = env.action_masks()
    assert all(masks[0:3])
    assert not any(masks[3:8])

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
