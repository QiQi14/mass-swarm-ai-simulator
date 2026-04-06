import pytest
from src.utils.terrain_generator import generate_random_terrain, TIER0_PASSABLE, TIER1_DESTRUCTIBLE, TIER2_PERMANENT

def test_terrain_generator_dimensions():
    terrain = generate_random_terrain(width=50, height=50)
    assert terrain["width"] == 50
    assert terrain["height"] == 50
    assert len(terrain["hard_costs"]) == 2500
    assert len(terrain["soft_costs"]) == 2500
    assert terrain["cell_size"] == 20.0

def test_terrain_generator_spawn_zones_clear():
    terrain = generate_random_terrain(width=50, height=50)
    hard = terrain["hard_costs"]
    soft = terrain["soft_costs"]
    # Check left spawn (10, 25)
    idx_left = 25 * 50 + 10
    assert hard[idx_left] == TIER0_PASSABLE
    assert soft[idx_left] == TIER0_PASSABLE
    # Check right spawn (40, 25)
    idx_right = 25 * 50 + 40
    assert hard[idx_right] == TIER0_PASSABLE
    assert soft[idx_right] == TIER0_PASSABLE

def test_terrain_generator_deterministic():
    t1 = generate_random_terrain(seed=42)
    t2 = generate_random_terrain(seed=42)
    assert t1["hard_costs"] == t2["hard_costs"]
    assert t1["soft_costs"] == t2["soft_costs"]

def test_terrain_generator_has_destructible_and_permanent():
    terrain = generate_random_terrain(width=50, height=50, wall_density=0.5, destructible_ratio=0.5)
    hard = terrain["hard_costs"]
    assert TIER1_DESTRUCTIBLE in hard
    assert TIER2_PERMANENT in hard

def test_terrain_generator_payload_matches_rust():
    """Ensure return dict has all keys expected by Rust TerrainPayload."""
    terrain = generate_random_terrain(seed=1)
    expected_keys = {"hard_costs", "soft_costs", "width", "height", "cell_size"}
    assert set(terrain.keys()) == expected_keys, f"Keys mismatch: {set(terrain.keys())} vs {expected_keys}"
