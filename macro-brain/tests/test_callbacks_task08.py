import pytest
import numpy as np
from collections import deque
from src.training.callbacks import ACTION_NAMES, EnvStatCallback, EpisodeLogCallback, CurriculumCallback

class DummyEnv:
    def __init__(self, stage=1):
        self.curriculum_stage = stage

class DummyTrainingEnv:
    def __init__(self, stage=1):
        self.envs = [DummyEnvWrapper(DummyEnv(stage))]

class DummyEnvWrapper:
    def __init__(self, unwrapped):
        self.unwrapped = unwrapped

class DummyModel:
    def __init__(self, stage=1):
        self.env = DummyTrainingEnv(stage)
    def get_env(self):
        return self.env

def test_action_names():
    assert len(ACTION_NAMES) == 8
    expected = ["Hold", "AttackCoord", "DropPheromone", "DropRepellent", "SplitToCoord", "MergeBack", "Retreat", "Scout"]
    assert ACTION_NAMES == expected

def test_episode_log_callback_headers(tmpdir):
    log_path = str(tmpdir.join("log.csv"))
    cb = EpisodeLogCallback(log_path=log_path, num_actions=8)
    cb.init_callback(DummyModel(stage=7))
    cb._on_training_start()
    
    stage_path = str(tmpdir.join("episode_log_stage7.csv"))
    with open(stage_path, "r") as f:
        header = f.readline().strip().split(",")
    
    assert "fog_explored_pct" in header
    assert "flanking_score" in header
    
def test_curriculum_graduation():
    cb_ep = EpisodeLogCallback()
    cb_curr = CurriculumCallback(episode_logger=cb_ep, win_rate_threshold=0.8, streak_required=20, max_substage=8)
    cb_curr.init_callback(DummyModel(stage=1))
    
    # Fill with 200 wins
    cb_ep._results.extend([1] * 200)
    cb_ep.episode_count = 200
    
    # Run step (should graduate sub-stage)
    cb_curr._on_step()
    
    # Should be 1 streak now because consecutive is per check. Wait, consecutive_above is incremented once.
    # It requires 20 steps to be consecutive? The test says: streak_required=20.
    assert cb_curr._consecutive_above == 1
    
    for _ in range(19):
        cb_ep.episode_count += 1
        cb_curr._on_step()
        
    assert cb_curr.training_env.envs[0].unwrapped.curriculum_stage == 2
    assert len(cb_ep._results) == 0  # Should be reset

def test_curriculum_stage_5():
    cb_ep = EpisodeLogCallback()
    cb_curr = CurriculumCallback(episode_logger=cb_ep, win_rate_threshold=0.8, streak_required=1, max_substage=8)
    cb_curr.init_callback(DummyModel(stage=5))
    
    cb_ep._results.extend([1] * 200)
    # Flanking score not high enough
    cb_ep._flanking_scores.extend([0.2] * 200)
    cb_ep.episode_count = 200
    cb_curr._on_step()
    assert cb_curr.training_env.envs[0].unwrapped.curriculum_stage == 5 # Didn't graduate
    
    # Flanking score high enough
    cb_ep._flanking_scores.extend([0.4] * 200)
    cb_ep.episode_count = 201
    cb_curr._on_step()
    assert cb_curr.training_env.envs[0].unwrapped.curriculum_stage == 6 # Graduated

def test_curriculum_stage_6():
    """Stage 6 graduates on win rate alone (no lure criteria, Scout is atomic)."""
    cb_ep = EpisodeLogCallback()
    cb_curr = CurriculumCallback(episode_logger=cb_ep, win_rate_threshold=0.8, streak_required=1, max_substage=8)
    cb_curr.init_callback(DummyModel(stage=6))
    
    cb_ep._results.extend([1] * 200)
    cb_ep.episode_count = 200
    cb_curr._on_step()
    assert cb_curr.training_env.envs[0].unwrapped.curriculum_stage == 7  # Graduated on win rate alone

