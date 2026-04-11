import torch
import numpy as np
import gymnasium as gym
from gymnasium.spaces import Box, Dict
from src.models.feature_extractor import TacticalExtractor

observation_space = gym.spaces.Dict({
    "ch0": Box(low=-1.0, high=1.0, shape=(50, 50), dtype=np.float32),
    "ch1": Box(low=-1.0, high=1.0, shape=(50, 50), dtype=np.float32),
    "ch2": Box(low=-1.0, high=1.0, shape=(50, 50), dtype=np.float32),
    "ch3": Box(low=-1.0, high=1.0, shape=(50, 50), dtype=np.float32),
    "ch4": Box(low=-1.0, high=1.0, shape=(50, 50), dtype=np.float32),
    "ch5": Box(low=-1.0, high=1.0, shape=(50, 50), dtype=np.float32),
    "ch6": Box(low=-1.0, high=1.0, shape=(50, 50), dtype=np.float32),
    "ch7": Box(low=-1.0, high=1.0, shape=(50, 50), dtype=np.float32),
    "summary": Box(low=-1.0, high=1.0, shape=(12,), dtype=np.float32),
})

extractor = TacticalExtractor(observation_space, features_dim=256)

B = 2
observations = {
    "ch0": torch.randn(B, 50, 50),
    "ch1": torch.randn(B, 50, 50),
    "ch2": torch.randn(B, 50, 50),
    "ch3": torch.randn(B, 50, 50),
    "ch4": torch.randn(B, 50, 50),
    "ch5": torch.randn(B, 50, 50),
    "ch6": torch.randn(B, 50, 50),
    "ch7": torch.randn(B, 50, 50),
    "summary": torch.randn(B, 12),
}

out = extractor(observations)
assert out.shape == (B, 256), f"Expected shape (B, 256), got {out.shape}"
print("All assertions passed!")
