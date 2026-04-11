import pytest
import numpy as np
from src.training.curriculum import (
    get_spawns_for_stage,
    get_map_config,
    generate_terrain_for_stage
)

def test_get_spawns_for_stage_1():
    # Stage 1: Target Selection — 3 factions (brain, trap, target)
    spawns, meta = get_spawns_for_stage(1)
    assert len(spawns) == 3
    assert "trap_faction" in meta
    assert "target_faction" in meta
    counts = {s["faction_id"]: s["count"] for s in spawns}
    assert counts[0] == 50  # brain

def test_get_spawns_for_stage_2():
    # Stage 2: Pheromone Path — 3 factions (brain, trap on fast path, target)
    rng = np.random.default_rng(42)
    spawns, meta = get_spawns_for_stage(2, rng=rng)
    assert len(spawns) == 3
    assert meta["trap_faction"] != 0
    assert meta["target_faction"] != 0
    # Trap has 200HP
    trap_spawn = next(s for s in spawns if s["faction_id"] == meta["trap_faction"])
    assert trap_spawn["stats"][0]["value"] == 200.0
    assert trap_spawn["count"] == 40

def test_get_spawns_for_stage_3():
    # Stage 3: Repellent Field — brain + 2-3 trap groups + target
    rng = np.random.default_rng(42)
    spawns, meta = get_spawns_for_stage(3, rng=rng)
    assert len(spawns) >= 4  # brain + 2 traps + target minimum
    assert len(spawns) <= 5  # brain + 3 traps + target maximum

def test_get_spawns_for_stage_4():
    # Stage 4: Fog Scouting — brain at center, target at edge
    rng = np.random.default_rng(42)
    spawns, meta = get_spawns_for_stage(4, rng=rng)
    assert len(spawns) == 2  # brain + target only
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

def test_generate_terrain_stage_2_two_path():
    # Stage 2 terrain has walls (permanent wall band) and mud zones
    terrain = generate_terrain_for_stage(2, seed=0)
    hard_costs = terrain["hard_costs"]
    soft_costs = terrain["soft_costs"]
    # Should have permanent walls (65535)
    assert any(c == 65535 for c in hard_costs), "Stage 2 should have permanent walls"
    # Should have mud zones (soft_cost < 100)
    assert any(c < 100 for c in soft_costs), "Stage 2 should have mud zones"

def test_generate_terrain_stage_3_danger_zones():
    # Stage 3 terrain has high-cost danger zones (300)
    terrain = generate_terrain_for_stage(3, seed=0)
    hard_costs = terrain["hard_costs"]
    assert any(c == 300 for c in hard_costs), "Stage 3 should have danger zones"
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
