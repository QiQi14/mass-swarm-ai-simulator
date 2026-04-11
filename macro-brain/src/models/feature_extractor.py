"""Custom CNN+MLP feature extractor for tactical observations.

SB3's default CombinedExtractor cannot efficiently route our mixed Dict
observation space (8 × 50×50 grids + 12-dim summary). This custom extractor:
  1. Stacks 8 grid channels into (B, 8, 50, 50) tensor → CNN → 128-dim
  2. Passes 12-dim summary → MLP → 64-dim
  3. Concatenates → linear → features_dim

The combined embedding feeds into MaskablePPO's Actor and Critic heads.
"""

import torch
import torch.nn as nn
import gymnasium as gym
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor


class TacticalExtractor(BaseFeaturesExtractor):
    """CNN branch for spatial grids + MLP branch for summary."""
    
    def __init__(self, observation_space: gym.spaces.Dict, features_dim: int = 256):
        # Must call super with the final features_dim
        super().__init__(observation_space, features_dim)
        
        n_channels = 8  # ch0..ch7
        grid_h, grid_w = 50, 50
        
        # CNN branch: (B, 8, 50, 50) → 128-dim
        self.cnn = nn.Sequential(
            nn.Conv2d(n_channels, 32, kernel_size=5, stride=2, padding=2),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.Flatten(),
        )
        
        # Calculate CNN output size by forward pass with dummy input
        with torch.no_grad():
            dummy = torch.zeros(1, n_channels, grid_h, grid_w)
            cnn_out_size = self.cnn(dummy).shape[1]
        
        self.cnn_linear = nn.Sequential(
            nn.Linear(cnn_out_size, 128),
            nn.ReLU(),
        )
        
        # MLP branch: 12-dim summary → 64-dim
        summary_dim = observation_space["summary"].shape[0]  # 12
        self.mlp = nn.Sequential(
            nn.Linear(summary_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
        )
        
        # Combiner: 128 + 64 = 192 → features_dim
        self.combiner = nn.Sequential(
            nn.Linear(128 + 64, features_dim),
            nn.ReLU(),
        )
    
    def forward(self, observations: dict[str, torch.Tensor]) -> torch.Tensor:
        # Stack grid channels: (B, 8, 50, 50)
        grids = torch.stack(
            [observations[f"ch{i}"] for i in range(8)], dim=1
        )
        
        cnn_out = self.cnn_linear(self.cnn(grids))
        mlp_out = self.mlp(observations["summary"])
        
        combined = torch.cat([cnn_out, mlp_out], dim=1)
        return self.combiner(combined)
