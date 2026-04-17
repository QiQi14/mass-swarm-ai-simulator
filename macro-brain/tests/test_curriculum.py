import pytest
import numpy as np
from src.training.curriculum import (
    get_spawns_for_stage,
    get_map_config,
    generate_terrain_for_stage
)
from src.training.stage_combat_rules import get_stage_combat_rules

def test_get_spawns_for_stage_1():
    # Stage 1: Target Selection — 3 factions (brain, trap, target)
    spawns, meta = get_spawns_for_stage(1)
    assert len(spawns) == 3
    assert "trap_faction" in meta
    assert "target_faction" in meta
    counts = {s["faction_id"]: s["count"] for s in spawns}
    assert counts[0] == 50  # brain

def test_get_spawns_for_stage_2():
    # Stage 2: Pheromone Fortress — 3 factions (brain, tanks, rangers)
    rng = np.random.default_rng(42)
    spawns, meta = get_spawns_for_stage(2, rng=rng)
    assert len(spawns) == 3
    assert meta["trap_faction"] != 0
    assert meta["target_faction"] != 0
    # Tanks (trap) have 200HP, 20 count (reduced for ×1.2 pheromone margin)
    trap_spawn = next(s for s in spawns if s["faction_id"] == meta["trap_faction"])
    assert trap_spawn["stats"][0]["value"] == 200.0
    assert trap_spawn["count"] == 20
    # Rangers (target) have 60HP, 20 count
    target_spawn = next(s for s in spawns if s["faction_id"] == meta["target_faction"])
    assert target_spawn["stats"][0]["value"] == 60.0
    assert target_spawn["count"] == 20

def test_get_spawns_for_stage_3():
    # Stage 3: Repellent Field — brain + 2-3 trap groups + target
    rng = np.random.default_rng(42)
    spawns, meta = get_spawns_for_stage(3, rng=rng)
    assert len(spawns) >= 4  # brain + 2 traps + target minimum
    assert len(spawns) <= 5  # brain + 3 traps + target maximum

def test_get_spawns_for_stage_4():
    # Stage 4: Fog Scouting — brain at center, targets at opposite edges
    rng = np.random.default_rng(42)
    spawns, meta = get_spawns_for_stage(4, rng=rng)
    assert len(spawns) == 3  # brain + 2 targets
    target_spawn = next(s for s in spawns if s["faction_id"] == meta["target_faction"])
    pos = (target_spawn["x"], target_spawn["y"])
    assert pos in [(100.0, 400.0), (700.0, 400.0), (400.0, 100.0), (400.0, 700.0)]

def test_get_map_config_w():
    assert get_map_config(1).active_grid_w == 25
    assert get_map_config(6).active_grid_w == 50

def test_get_map_config_fog():
    # Stages 0-3: fog OFF, Stages 4+: fog ON
    assert get_map_config(0).fog_enabled is False
    assert get_map_config(1).fog_enabled is False
    assert get_map_config(2).fog_enabled is False
    assert get_map_config(3).fog_enabled is False
    assert get_map_config(4).fog_enabled is True
    assert get_map_config(5).fog_enabled is True
    assert get_map_config(7).fog_enabled is True

def test_generate_terrain_stage_2_fortress():
    # Stage 2 terrain: fortress walls with 2 openings + mud on one path
    terrain = generate_terrain_for_stage(2, seed=0)
    hard_costs = terrain["hard_costs"]
    soft_costs = terrain["soft_costs"]
    w = terrain["width"]
    # Should have permanent walls (65535) forming the fortress
    wall_count = sum(1 for c in hard_costs if c == 65535)
    assert wall_count > 0, "Stage 2 fortress should have permanent walls"
    # Should have mud zones (soft_cost < 100) near one opening
    mud_count = sum(1 for c in soft_costs if c < 100)
    assert mud_count > 0, "Stage 2 should have mud corridors"
    # Fortress walls should form an enclosure — check top and bottom edges exist
    fort_y_min, fort_y_max = 9, 21
    fort_x_min, fort_x_max = 16, 26
    # Top wall has walls at y=fort_y_min for x in range
    top_wall = [hard_costs[fort_y_min * w + x] for x in range(fort_x_min, fort_x_max + 1)]
    assert all(c == 65535 for c in top_wall), "Top fortress wall should be solid"
    # Left wall has openings — not all cells should be walls
    left_wall = [hard_costs[y * w + fort_x_min] for y in range(fort_y_min, fort_y_max + 1)]
    wall_cells = sum(1 for c in left_wall if c == 65535)
    opening_cells = len(left_wall) - wall_cells
    assert opening_cells == 4, f"Left wall should have exactly 4 opening cells (2 openings × 2 cells), got {opening_cells}"

def test_generate_terrain_stage_2_seed_randomization():
    # Different seeds should produce different mud path orientations
    terrain_even = generate_terrain_for_stage(2, seed=0)
    terrain_odd = generate_terrain_for_stage(2, seed=1)
    # Even seed: top is clean, bottom is mud
    # Odd seed: top is mud, bottom is clean
    # Check mud at a bottom-path cell vs top-path cell
    w = terrain_even["width"]
    # Bottom opening Y=19, mud corridor at Y=18-21, X=10-16
    bottom_mud_idx = 18 * w + 12
    top_mud_idx = 9 * w + 12
    # For even seed, bottom should have mud
    assert terrain_even["soft_costs"][bottom_mud_idx] < 100, "Even seed: bottom path should have mud"
    # For odd seed, top should have mud
    assert terrain_odd["soft_costs"][top_mud_idx] < 100, "Odd seed: top path should have mud"

def test_stage_2_combat_rules():
    # Stage 2 should return extended-range combat rule for rangers
    rules = get_stage_combat_rules(stage=2, enemy_faction=1, brain_faction=0, target_faction=2)
    assert len(rules) == 1, "Stage 2 should add exactly 1 combat rule"
    rule = rules[0]
    assert rule["source_faction"] == 2, "Rule source should be ranger/target faction"
    assert rule["target_faction"] == 0, "Rule target should be brain faction"
    assert rule["range"] == 150.0, "Ranger range should be 150"
    assert rule["effects"][0]["delta_per_second"] == -12.0, "Ranger DPS should be -12"

def test_generate_terrain_stage_3_danger_zones():
    # Stage 3 terrain has high-cost danger zones (400)
    terrain = generate_terrain_for_stage(3, seed=0)
    hard_costs = terrain["hard_costs"]
    assert any(c == 400 for c in hard_costs), "Stage 3 should have danger zones"
    # No permanent walls in stage 3
    assert all(c < 65535 for c in hard_costs), "Stage 3 should have no permanent walls"

def test_generate_terrain_stage_1_flat():
    # Stage 1: flat terrain (all costs = 100)
    terrain = generate_terrain_for_stage(1)
    assert all(c == 100 for c in terrain["hard_costs"])
    assert all(c == 100 for c in terrain["soft_costs"])

def test_stage_8_randomized():
    # Stage 8 randomly selects from pool
    rng = np.random.default_rng(42)
    spawns, meta = get_spawns_for_stage(8, rng=rng)
    assert type(spawns) is list
    assert len(spawns) in [2, 3, 4, 5]  # variousconfigs
    assert "trap_faction" in meta

def test_bounds_for_all_stages():
    # All spawn coordinates are within world bounds
    for stage in range(0, 9):
        rng = np.random.default_rng(stage)
        spawns, meta = get_spawns_for_stage(stage, rng=rng)
        config = get_map_config(stage)
        for s in spawns:
            assert 0 <= s["x"] <= config.world_width, f"Stage {stage}: x={s['x']} out of bounds"
            assert 0 <= s["y"] <= config.world_height, f"Stage {stage}: y={s['y']} out of bounds"

def test_negative_path_invalid_stage():
    # Invalid stage should gracefully fallback to stage 0
    spawns, meta = get_spawns_for_stage(999)
    assert len(spawns) == 2  # Same as stage 0
