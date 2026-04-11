import pytest
import numpy as np
from src.utils.lkp_buffer import LKPBuffer
from src.utils.vectorizer import vectorize_snapshot

def test_lkp_buffer():
    buf = LKPBuffer(grid_h=50, grid_w=50, num_enemy_channels=2, decay_rate=0.02)
    
    # 1. Update overwrites visible cells with ground truth
    live_density = np.zeros((50, 50))
    live_density[0, 0] = 1.0
    live_density[1, 1] = 0.5
    
    vis_mask = np.zeros((50, 50))
    vis_mask[0, 0] = 1.0 # visible
    # 1,1 is hidden
    
    buf.memory[0][1, 1] = 0.8 # previous memory
    
    out = buf.update(0, live_density, vis_mask)
    
    assert out[0, 0] == 1.0 # overwritten with live
    
    # 2. Decays hidden cells
    assert out[1, 1] == pytest.approx(0.8 - 0.02) # decayed
    
    # 3. Never produces negative density
    buf.memory[0][2, 2] = 0.01
    vis_mask_2 = np.zeros((50, 50))
    out2 = buf.update(0, live_density, vis_mask_2) # all hidden
    assert out2[2, 2] == 0.0
    
    # 4. Reset zeros all memory
    buf.reset()
    assert buf.memory[0].sum() == 0.0
    assert buf.memory[1].sum() == 0.0

def test_vectorize_snapshot():
    snapshot = {
        "density_maps": {"0": [1.0] * 625},
        "fog_explored": [1.0] * 625,
        "fog_visible": [1.0] * 625,
        "terrain_hard": [0] * 625,
        "summary": {
            "faction_counts": {"0": 10},
            "faction_avg_stats": {"0": [100.0]}
        }
    }
    
    obs = vectorize_snapshot(
        snapshot, brain_faction=0, enemy_factions=[1],
        active_grid_w=25, active_grid_h=25, fog_enabled=True,
        lkp_buffer=LKPBuffer()
    )
    
    # returns dict with 8 'ch*' keys + 'summary'
    assert "summary" in obs
    for i in range(8):
        assert f"ch{i}" in obs
        assert obs[f"ch{i}"].shape == (50, 50)
    
    assert obs["summary"].shape == (12,)
    
    pad_y, pad_x = (50 - 25) // 2, (50 - 25) // 2
    
    # padding zone of ch4 (terrain) is 1.0 (wall)
    assert obs["ch4"][0, 0] == 1.0
    # active zone:
    assert obs["ch4"][pad_y, pad_x] == 0.0
    
    # padding zone of ch5,ch6 (fog) is 1.0
    assert obs["ch5"][0, 0] == 1.0
    assert obs["ch6"][0, 0] == 1.0
    # active zone:
    assert obs["ch5"][pad_y, pad_x] == 1.0
    
    # density channels are 0.0 in padding
    assert obs["ch0"][0, 0] == 0.0
    assert obs["ch0"][pad_y, pad_x] == 1.0

def test_vectorize_fog_disabled():
    snapshot = {}
    obs = vectorize_snapshot(
        snapshot, fog_enabled=False
    )
    # Fog-disabled: ch5 and ch6 are all 1.0
    assert obs["ch5"].sum() == 2500
    assert obs["ch6"].sum() == 2500
