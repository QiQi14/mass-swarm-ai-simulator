"""Last Known Position (LKP) memory buffer for fog-of-war.

Fixes the 'Goldfish Memory' problem: feed-forward PPO has zero temporal memory.
When enemies disappear into fog, their density drops to 0.0 and the model
instantly forgets they exist.

Solution: externalize memory. When visible → overwrite with ground truth.
When hidden → decay stored density toward 0 at a configurable rate.
The decaying 'ghost trail' gives PPO something to track.
"""

import numpy as np


class LKPBuffer:
    """Manages last-known-position memory for enemy density channels."""
    
    def __init__(
        self,
        grid_h: int = 50,
        grid_w: int = 50,
        num_enemy_channels: int = 2,
        decay_rate: float = 0.02,
    ):
        """
        Args:
            grid_h: Grid height (always 50 — max tensor size).
            grid_w: Grid width (always 50 — max tensor size).
            num_enemy_channels: Number of enemy faction channels to track.
            decay_rate: Density decay per evaluation tick when hidden.
        """
        self.grid_h = grid_h
        self.grid_w = grid_w
        self.decay_rate = decay_rate
        self.num_channels = num_enemy_channels
        self.memory: list[np.ndarray] = [
            np.zeros((grid_h, grid_w), dtype=np.float32)
            for _ in range(num_enemy_channels)
        ]
    
    def update(
        self,
        channel_idx: int,
        live_density: np.ndarray,
        visible_mask: np.ndarray,
    ) -> np.ndarray:
        """Update LKP memory for one enemy channel and return the result.
        
        - Where visible: overwrite with live density (ground truth)
        - Where NOT visible: decay stored density toward 0
        
        Args:
            channel_idx: Enemy channel index (0 or 1).
            live_density: Raw density from Rust (50×50, may be zero-padded).
            visible_mask: Current visibility grid (50×50, 1=visible, 0=hidden).
        
        Returns:
            LKP-processed density grid (50×50).
        """
        mem = self.memory[channel_idx]
        visible = visible_mask > 0.5
        hidden = ~visible
        
        # Visible cells: ground truth
        mem[visible] = live_density[visible]
        
        # Hidden cells: decay
        mem[hidden] = np.maximum(0.0, mem[hidden] - self.decay_rate)
        
        self.memory[channel_idx] = mem
        return mem.copy()
    
    def get(self, channel_idx: int) -> np.ndarray:
        """Get current LKP memory for a channel."""
        return self.memory[channel_idx].copy()
    
    def reset(self):
        """Clear all memory (call on episode reset)."""
        for i in range(self.num_channels):
            self.memory[i].fill(0.0)
