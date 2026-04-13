# Task 03: Vectorizer & LKP Memory Buffer

```yaml
Task_ID: task_03_vectorizer_lkp
Execution_Phase: 1
Model_Tier: standard
Dependencies: []
Target_Files:
  - macro-brain/src/utils/vectorizer.py
  - macro-brain/src/utils/lkp_buffer.py  # NEW FILE
Context_Bindings:
  - context/architecture
  - context/conventions
```

## Objective

Rewrite the state vectorizer to produce 8-channel (50×50) observations with fog-of-war support, Last Known Position (LKP) memory decay for non-recurrent PPO, and center-padding for variable map sizes. Create LKP buffer as a new module.

## Strict Instructions

### 1. Create `macro-brain/src/utils/lkp_buffer.py` (NEW FILE)

```python
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
```

### 2. Rewrite `macro-brain/src/utils/vectorizer.py`

Replace the entire `vectorize_snapshot` function. The new version:

**Key changes:**
- 8 channels instead of 4 (+ terrain)
- Center-padding for variable map sizes
- Fog-gated enemy density via LKP buffer
- Threat density channel
- 12-dim summary instead of 6

```python
"""State vectorization: JSON snapshot → numpy observation dict.

8-channel fixed 50×50 tensor + 12-dim summary vector.

Channel assignment:
  ch0: brain faction density
  ch1: enemy faction 1 density (LKP-processed under fog)
  ch2: enemy faction 2 density (LKP-processed under fog)  
  ch3: sub-factions aggregated
  ch4: terrain (0=passable, 1=wall; padding=1.0)
  ch5: fog explored (0=unexplored, 1=explored; padding=1.0)
  ch6: fog visible (0=hidden, 1=visible; padding=1.0)
  ch7: threat density (weighted enemy)

For maps smaller than 50×50, the active arena is centered in the tensor.
Padding zones have: density=0, terrain=1(wall), fog=1(explored/visible).
"""

import numpy as np
from typing import Any

# Always 50×50 — CNN requires fixed shape
MAX_GRID = 50
NUM_CHANNELS = 8
SUMMARY_DIM = 12


def vectorize_snapshot(
    snapshot: dict[str, Any],
    brain_faction: int = 0,
    enemy_factions: list[int] | int = 1,
    active_grid_w: int = 50,
    active_grid_h: int = 50,
    cell_size: float = 20.0,
    fog_enabled: bool = False,
    lkp_buffer=None,
    max_entities: float = 10000.0,
    max_steps: int = 500,
    step_count: int = 0,
) -> dict[str, np.ndarray]:
    """Convert Rust StateSnapshot → numpy observation dict.
    
    Args:
        snapshot: Raw JSON from Rust.
        brain_faction: Faction ID of the RL agent.
        enemy_factions: Enemy faction ID(s).
        active_grid_w: Active map grid width (may be < 50).
        active_grid_h: Active map grid height (may be < 50).
        cell_size: World units per grid cell.
        fog_enabled: Whether fog of war is active this stage.
        lkp_buffer: LKPBuffer instance (required when fog_enabled=True).
        max_entities: Normalization constant for entity counts.
        max_steps: Max steps per episode (for progress normalization).
        step_count: Current step in episode.
    """
    if isinstance(enemy_factions, int):
        enemy_factions = [enemy_factions]
    enemy_factions = sorted(enemy_factions)
    
    # Padding offset for center-aligned active arena
    pad_x = (MAX_GRID - active_grid_w) // 2
    pad_y = (MAX_GRID - active_grid_h) // 2
    
    # Initialize all channels
    channels = [np.zeros((MAX_GRID, MAX_GRID), dtype=np.float32) for _ in range(NUM_CHANNELS)]
    
    density_maps = snapshot.get("density_maps", {})
    active_size = active_grid_h * active_grid_w
    
    def _place_density(flat_data: list, channel_idx: int):
        """Place active-sized density data into center-padded channel."""
        if not flat_data or len(flat_data) != active_size:
            return
        arr = np.array(flat_data, dtype=np.float32).reshape(active_grid_h, active_grid_w)
        channels[channel_idx][pad_y:pad_y+active_grid_h, pad_x:pad_x+active_grid_w] = arr
    
    # ── ch0: Brain density ──────────────────────────────────
    key = str(brain_faction)
    if key in density_maps:
        _place_density(density_maps[key], 0)
    
    # ── ch5: Fog explored, ch6: Fog visible ─────────────────
    # Default: fully explored/visible (no fog) — padding also 1.0
    channels[5].fill(1.0)
    channels[6].fill(1.0)
    
    if fog_enabled:
        fog_explored_raw = snapshot.get("fog_explored", [])
        fog_visible_raw = snapshot.get("fog_visible", [])
        
        if fog_explored_raw and len(fog_explored_raw) == active_size:
            explored = np.array(fog_explored_raw, dtype=np.float32).reshape(active_grid_h, active_grid_w)
            # Reset active area then place
            channels[5][pad_y:pad_y+active_grid_h, pad_x:pad_x+active_grid_w] = explored
        
        if fog_visible_raw and len(fog_visible_raw) == active_size:
            visible = np.array(fog_visible_raw, dtype=np.float32).reshape(active_grid_h, active_grid_w)
            channels[6][pad_y:pad_y+active_grid_h, pad_x:pad_x+active_grid_w] = visible
    
    # ── ch1, ch2: Enemy densities (fog-gated via LKP) ──────
    for i, ef in enumerate(enemy_factions[:2]):
        ch_idx = 1 + i
        key = str(ef)
        if key in density_maps:
            _place_density(density_maps[key], ch_idx)
        
        if fog_enabled and lkp_buffer is not None:
            # LKP processes the full 50×50 padded channel using the padded visibility
            channels[ch_idx] = lkp_buffer.update(i, channels[ch_idx], channels[6])
    
    # ── ch3: Sub-factions aggregated ────────────────────────
    known = set([brain_faction] + enemy_factions)
    for sf_key in density_maps:
        sf_id = int(sf_key)
        if sf_id not in known:
            flat = density_maps[sf_key]
            if flat and len(flat) == active_size:
                arr = np.array(flat, dtype=np.float32).reshape(active_grid_h, active_grid_w)
                channels[3][pad_y:pad_y+active_grid_h, pad_x:pad_x+active_grid_w] += arr
    
    # ── ch4: Terrain ────────────────────────────────────────
    # Padding = 1.0 (wall) so CNN learns "edge of world"
    channels[4].fill(1.0)
    terrain_hard = snapshot.get("terrain_hard", [])
    if terrain_hard and len(terrain_hard) == active_size:
        raw = np.array(terrain_hard, dtype=np.float32)
        terrain = np.clip(raw / 65535.0, 0.0, 1.0).reshape(active_grid_h, active_grid_w)
        channels[4][pad_y:pad_y+active_grid_h, pad_x:pad_x+active_grid_w] = terrain
    
    # ── ch7: Threat density (sum of enemy densities weighted) ──
    channels[7] = channels[1] + channels[2]  # simple sum for now
    
    # ── Summary (12 dims) ──────────────────────────────────
    summary_data = snapshot.get("summary", {})
    faction_counts = summary_data.get("faction_counts", {})
    faction_avg = summary_data.get("faction_avg_stats", {})
    
    own_count = faction_counts.get(str(brain_faction), 0)
    total_enemy = sum(faction_counts.get(str(ef), 0) for ef in enemy_factions)
    
    own_hp = 0.0
    if str(brain_faction) in faction_avg:
        h = faction_avg[str(brain_faction)]
        own_hp = h[0] if h else 0.0
    
    enemy_hp = 0.0
    ecount = 0
    for ef in enemy_factions:
        if str(ef) in faction_avg:
            h = faction_avg[str(ef)]
            if h:
                enemy_hp += h[0]
                ecount += 1
    if ecount > 0:
        enemy_hp /= ecount
    
    sub_factions = len(snapshot.get("active_sub_factions", []))
    active_zones = len(snapshot.get("active_zones", []))
    
    # Per-faction counts for tactical awareness
    trap_count = faction_counts.get(str(enemy_factions[0]), 0) if enemy_factions else 0
    target_count = faction_counts.get(str(enemy_factions[1]), 0) if len(enemy_factions) > 1 else 0
    
    # Fog explored percentage (active area only)
    if fog_enabled:
        active_fog = channels[5][pad_y:pad_y+active_grid_h, pad_x:pad_x+active_grid_w]
        fog_explored_pct = float(active_fog.mean())
    else:
        fog_explored_pct = 1.0
    
    summary = np.array([
        min(own_count / max_entities, 1.0),          # 0
        min(total_enemy / max_entities, 1.0),         # 1
        own_hp / 100.0,                               # 2
        enemy_hp / 100.0,                             # 3
        min(sub_factions / 5.0, 1.0),                 # 4
        min(active_zones / 10.0, 1.0),                # 5
        min(trap_count / max_entities, 1.0),           # 6
        min(target_count / max_entities, 1.0),         # 7
        fog_explored_pct,                              # 8
        float(sub_factions > 0),                       # 9
        0.0,  # debuff_applied — set by env            # 10
        min(step_count / max(max_steps, 1), 1.0),      # 11
    ], dtype=np.float32)
    
    obs = {f"ch{i}": channels[i] for i in range(NUM_CHANNELS)}
    obs["summary"] = summary
    return obs
```

### 3. Update imports in `__init__.py`

Ensure `lkp_buffer` is importable:

```python
# macro-brain/src/utils/__init__.py
# No changes needed if using explicit imports
```

## Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: unit
  Test_Stack: pytest (macro-brain)
  Acceptance_Criteria:
    - "LKPBuffer.update() overwrites visible cells with ground truth"
    - "LKPBuffer.update() decays hidden cells by decay_rate per call"
    - "LKPBuffer.update() never produces negative density"
    - "LKPBuffer.reset() zeros all memory"
    - "vectorize_snapshot returns dict with 8 'ch*' keys + 'summary'"
    - "All ch* arrays are shape (50, 50)"
    - "summary is shape (12,)"
    - "For active_grid=25: padding zone of ch4 (terrain) is 1.0 (wall)"
    - "For active_grid=25: padding zone of ch5,ch6 (fog) is 1.0"
    - "For active_grid=25: density channels are 0.0 in padding"
    - "Fog-disabled: ch5 and ch6 are all 1.0"
    - "Fog-enabled: enemy density passes through LKP buffer"
  Suggested_Test_Commands:
    - "cd macro-brain && python -m pytest tests/test_vectorizer.py tests/test_lkp_buffer.py -v"
```
