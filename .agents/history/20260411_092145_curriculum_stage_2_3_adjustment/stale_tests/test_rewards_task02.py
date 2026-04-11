import pytest
import numpy as np

from src.env.rewards import (
    exploration_reward,
    compute_flanking_score,
    compute_shaped_reward,
)
from src.config.definitions import RewardWeights

def test_reward_weights():
    # RewardWeights accepts all new fields with defaults
    rw = RewardWeights(
        time_penalty_per_step=-0.1,
        kill_reward=1.0,
        death_penalty=-0.5,
        win_terminal=100.0,
        loss_terminal=-100.0,
        survival_bonus_multiplier=1.2
    )
    assert rw.approach_scale == 0.02
    assert rw.exploration_reward == 0.005
    assert rw.exploration_decay_threshold == 0.8
    assert rw.threat_priority_bonus == 2.0
    assert rw.flanking_bonus_scale == 0.1
    assert rw.lure_success_bonus == 3.0
    assert rw.debuff_bonus == 2.0

def test_exploration_reward():
    fog_explored = np.zeros((50, 50))
    fog_explored[0:5, 0:5] = 1.0  # 25 cells explored
    prev_fog_explored = np.zeros((50, 50))
    
    # "exploration_reward returns 0.0 when prev is None"
    assert exploration_reward(fog_explored, None) == 0.0
    
    # "exploration_reward returns positive for newly explored cells"
    reward = exploration_reward(fog_explored, prev_fog_explored)
    assert reward == pytest.approx(25 * 0.005)
    
    # "exploration_reward returns 0.0 when explored_pct >= threshold"
    fog_explored_full = np.ones((50, 50))
    reward_full = exploration_reward(fog_explored_full, prev_fog_explored, decay_threshold=0.8)
    assert reward_full == 0.0

def test_compute_flanking_score():
    # "compute_flanking_score returns 0.0 when any centroid is None"
    assert compute_flanking_score(None, (0, 0), (1, 1)) == 0.0
    
    # "compute_flanking_score returns ~0.5 for 90° angle"
    # Enemy at (0, 0), Brain at (-1, 0), Sub at (0, 1) -> angle is 90
    assert compute_flanking_score((-1, 0), (0, 1), (0, 0)) == pytest.approx(0.5)
    
    # "compute_flanking_score returns ~1.0 for 180° angle"
    # Enemy at (0, 0), Brain at (-1, 0), Sub at (1, 0) -> angle is 180
    assert compute_flanking_score((-1, 0), (1, 0), (0, 0)) == pytest.approx(1.0)

def test_compute_shaped_reward_stages():
    rw = RewardWeights(
        time_penalty_per_step=-0.1,
        kill_reward=1.0,
        death_penalty=-0.5,
        win_terminal=100.0,
        loss_terminal=-100.0,
        survival_bonus_multiplier=1.2
    )
    snapshot = {"game_state": "playing"}
    fog_explored = np.zeros((50, 50))
    fog_explored[0, 0] = 1.0 # 1 cell
    prev_fog_explored = np.zeros((50, 50))
    
    # "compute_shaped_reward includes exploration only at stages 2,7,8"
    reward_stage1 = compute_shaped_reward(
        snapshot, None, 1, 2, rw, stage=1, fog_explored=fog_explored, prev_fog_explored=prev_fog_explored
    ) # no exploration reward
    
    reward_stage2 = compute_shaped_reward(
        snapshot, None, 1, 2, rw, stage=2, fog_explored=fog_explored, prev_fog_explored=prev_fog_explored
    ) # with exploration
    
    assert reward_stage2 > reward_stage1, "exploration reward not applied for stage 2"

    # "compute_shaped_reward includes flanking only at stage >= 5"
    reward_stage4 = compute_shaped_reward(
        snapshot, None, 1, 2, rw, stage=4, flanking_score=1.0
    )
    reward_stage5 = compute_shaped_reward(
        snapshot, None, 1, 2, rw, stage=5, flanking_score=1.0
    )
    # Check that stage 5 gets the 0.1 flanking bonus sum
    assert reward_stage5 == pytest.approx(reward_stage4 + 0.1)

