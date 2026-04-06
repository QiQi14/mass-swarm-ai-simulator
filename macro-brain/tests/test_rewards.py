import pytest
import numpy as np
from src.env.rewards import flanking_bonus, compute_shaped_reward

def create_density(cy: int, cx: int, shape=(50, 50)) -> np.ndarray:
    env = np.zeros(shape, dtype=np.float32)
    if 0 <= cy < shape[0] and 0 <= cx < shape[1]:
        env[cy, cx] = 1.0
    return env

def test_patch5_pacifist_flank_exploit_blocked():
    # main at (25, 25), enemy at (25, 30), sub at (49, 49)
    own = create_density(25, 25)
    enemy = create_density(25, 30)
    sub = create_density(49, 49)
    
    # max_engage_radius is 15.0
    # sub to enemy distance = sqrt((49-30)^2 + (49-25)^2) = sqrt(19^2 + 24^2) = ~30.6 > 15
    bonus = flanking_bonus(own, sub, enemy, max_engage_radius=15.0)
    assert bonus == 0.0

def test_patch5_genuine_flank_rewarded():
    # main at (20, 25), enemy at (25, 25), sub at (30, 25)
    own = create_density(20, 25)
    enemy = create_density(25, 25)
    sub = create_density(30, 25)
    
    bonus = flanking_bonus(own, sub, enemy, max_engage_radius=15.0)
    assert bonus > 0.0

def test_patch5_distance_attenuation():
    own = create_density(20, 25)
    enemy = create_density(22, 25)
    
    # We move sub further away from enemy along the y-axis (cy is increasing)
    sub1 = create_density(25, 25) # dist_to_enemy=3, proj_ratio=2.5 -> raw_bonus=1.0
    sub2 = create_density(30, 25) # dist_to_enemy=8, proj_ratio>2 -> raw_bonus=1.0
    sub3 = create_density(35, 25) # dist_to_enemy=13, proj_ratio>2 -> raw_bonus=1.0
    
    bonus1 = flanking_bonus(own, sub1, enemy, max_engage_radius=15.0)
    bonus2 = flanking_bonus(own, sub2, enemy, max_engage_radius=15.0)
    bonus3 = flanking_bonus(own, sub3, enemy, max_engage_radius=15.0)
    
    assert bonus1 > bonus2 > bonus3 > 0.0

def test_patch5_no_sub_faction_zero_bonus():
    own = create_density(20, 25)
    enemy = create_density(25, 25)
    sub = np.zeros((50, 50), dtype=np.float32)
    
    bonus = flanking_bonus(own, sub, enemy, max_engage_radius=15.0)
    assert bonus == 0.0

def test_shaped_reward_composition():
    # Dummy snapshot dicts
    prev_snapshot = {
        "summary": {
            "faction_counts": {"0": 100, "1": 50},
            "faction_avg_stats": {"0": [50.0], "1": [50.0]}
        }
    }
    
    # Gained health, killed 5 enemies, survived
    snapshot = {
        "summary": {
            "faction_counts": {"0": 100, "1": 45},
            "faction_avg_stats": {"0": [55.0], "1": [50.0]}
        },
        "density_maps": {
            "0": create_density(20, 25).flatten().tolist(),
            "1": create_density(25, 25).flatten().tolist(),
            "101": create_density(30, 25).flatten().tolist()
        },
        "active_sub_factions": [101]
    }
    
    rewards = compute_shaped_reward(snapshot, prev_snapshot, brain_faction=0, enemy_faction=1)
    
    # Base composition should be positive
    assert rewards > 0.0
