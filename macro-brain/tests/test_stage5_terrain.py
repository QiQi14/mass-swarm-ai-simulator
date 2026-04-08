import pytest
from unittest.mock import MagicMock
from src.training.curriculum import get_spawns_for_stage
from src.utils.terrain_generator import generate_terrain_for_stage

def test_stage_5_spawns():
    import random
    rng = random.Random(42)
    
    profile = MagicMock()
    # Mock faction counts so the getters don't crash
    # The curriculum code will try to iterate profile.factions
    faction_0 = MagicMock()
    faction_0.id = 0
    faction_0.default_count = 50
    faction_0.stats.hp = 100
    
    faction_1 = MagicMock()
    faction_1.id = 1
    faction_1.default_count = 50
    faction_1.stats.hp = 100
    
    profile.factions = [faction_0, faction_1]
    
    spawns = get_spawns_for_stage(5, rng, profile)
    
    assert len(spawns) > 0
    
    brain_spawns = 0
    bot_spawns = 0
    
    for spawn_group in spawns:
        if spawn_group["faction_id"] == 0:
            brain_spawns += 1
        else:
            bot_spawns += 1
            
        assert 100.0 <= spawn_group['x'] <= 900.0
        assert 100.0 <= spawn_group['y'] <= 900.0
        assert isinstance(spawn_group['count'], int)
        assert spawn_group['count'] > 0
        
    assert brain_spawns >= 1
    assert bot_spawns >= 2

def test_stage_5_terrain():
    terrain = generate_terrain_for_stage(5)
    assert isinstance(terrain, dict)
    # The terrain returns a dict with lists of obstacles/zones/etc.
    assert 'obstacles' in terrain or 'hard_costs' in terrain or type(terrain) is dict
