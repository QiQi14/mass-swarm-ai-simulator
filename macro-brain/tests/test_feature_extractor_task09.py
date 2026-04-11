import pytest
import torch
import gymnasium as gym
import numpy as np
from src.models import TacticalExtractor

def test_tactical_extractor_output():
    # 8 channels, 50x50 grids + 12-dim summary
    obs_space = gym.spaces.Dict({
        "ch0": gym.spaces.Box(low=0, high=1, shape=(50, 50), dtype=np.float32),
        "ch1": gym.spaces.Box(low=0, high=1, shape=(50, 50), dtype=np.float32),
        "ch2": gym.spaces.Box(low=0, high=1, shape=(50, 50), dtype=np.float32),
        "ch3": gym.spaces.Box(low=0, high=1, shape=(50, 50), dtype=np.float32),
        "ch4": gym.spaces.Box(low=0, high=1, shape=(50, 50), dtype=np.float32),
        "ch5": gym.spaces.Box(low=0, high=1, shape=(50, 50), dtype=np.float32),
        "ch6": gym.spaces.Box(low=0, high=1, shape=(50, 50), dtype=np.float32),
        "ch7": gym.spaces.Box(low=0, high=1, shape=(50, 50), dtype=np.float32),
        "summary": gym.spaces.Box(low=-np.inf, high=np.inf, shape=(12,), dtype=np.float32)
    })
    
    extractor = TacticalExtractor(observation_space=obs_space, features_dim=256)
    assert extractor.features_dim == 256
    
    # Dummy batch of 2
    dummy_obs = {
        "ch0": torch.zeros((2, 50, 50)),
        "ch1": torch.zeros((2, 50, 50)),
        "ch2": torch.zeros((2, 50, 50)),
        "ch3": torch.zeros((2, 50, 50)),
        "ch4": torch.zeros((2, 50, 50)),
        "ch5": torch.zeros((2, 50, 50)),
        "ch6": torch.zeros((2, 50, 50)),
        "ch7": torch.zeros((2, 50, 50)),
        "summary": torch.zeros((2, 12))
    }
    
    out = extractor(dummy_obs)
    
    assert out.shape == (2, 256)
