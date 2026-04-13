"""Tactical Curriculum Stages.

9-stage curriculum (0-8) for training the swarm intelligence.
Stage 0: 1v1 navigation — learn to use coordinate commands.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from numpy.random import Generator
    from src.config.game_profile import GameProfile

# 8-action vocabulary for tactical curriculum
ACTION_NAMES = [
    "Hold", "AttackCoord", "DropPheromone", "DropRepellent",
    "SplitToCoord", "MergeBack", "Retreat", "Scout",
]

@dataclass
class StageMapConfig:
    """Map configuration for a curriculum stage."""
    world_width: float
    world_height: float
    active_grid_w: int
    active_grid_h: int
    cell_size: float
    fog_enabled: bool
    
    @property
    def pad_offset_x(self) -> int:
        return (50 - self.active_grid_w) // 2
    
    @property
    def pad_offset_y(self) -> int:
        return (50 - self.active_grid_h) // 2

STAGE_MAP_CONFIGS: dict[int, StageMapConfig] = {
    0: StageMapConfig(400, 400, 20, 20, 20.0, fog_enabled=False),
    1: StageMapConfig(500, 500, 25, 25, 20.0, fog_enabled=False),
    2: StageMapConfig(600, 600, 30, 30, 20.0, fog_enabled=False),  # Pheromone Path
    3: StageMapConfig(600, 600, 30, 30, 20.0, fog_enabled=False),  # Repellent Field
    4: StageMapConfig(800, 800, 40, 40, 20.0, fog_enabled=True),   # Fog Scouting
    5: StageMapConfig(800, 800, 40, 40, 20.0, fog_enabled=True),   # Flanking
    6: StageMapConfig(1000, 1000, 50, 50, 20.0, fog_enabled=True), # Full Tactics
    7: StageMapConfig(1000, 1000, 50, 50, 20.0, fog_enabled=True), # Protected Target
    8: StageMapConfig(1000, 1000, 50, 50, 20.0, fog_enabled=True), # Randomized
}

def get_map_config(stage: int) -> StageMapConfig:
    """Get map configuration for a curriculum stage."""
    return STAGE_MAP_CONFIGS.get(stage, STAGE_MAP_CONFIGS[0])

def _faction_stats(profile: GameProfile | None, faction_id: int) -> list[dict]:
    """Get stat initializer from profile or default 100 primary_stat."""
    if profile is not None:
        for f in profile.factions:
            if f.id == faction_id:
                return [{"index": 0, "value": f.stats.primary_stat}]
    return [{"index": 0, "value": 100.0}]

def _faction_count(profile: GameProfile | None, faction_id: int, default: int) -> int:
    """Get default entity count from profile or defaults."""
    if profile is not None:
        for f in profile.factions:
            if f.id == faction_id:
                return f.default_count
    return default

def _spawns_stage0(rng: Generator | None = None, profile: GameProfile | None = None) -> tuple[list[dict], dict]:
    """Stage 0: 1v1 Navigation (400×400 world).
    
    Brain(40) on the left, Enemy(20) at a random position on the right half.
    Brain has 2:1 numeric advantage — correct navigation = easy win.
    Only one enemy group — no target selection required.
    The model's only job: learn to aim AttackCoord at the enemy blob.
    """
    brain_count = 40
    enemy_count = 20
    
    # Brain always starts left-center
    brain_x, brain_y = 80.0, 200.0
    
    # Enemy at random position on right half
    if rng is not None:
        enemy_x = 250.0 + rng.random() * 100.0  # 250-350
        enemy_y = 80.0 + rng.random() * 240.0   # 80-320
    else:
        enemy_x, enemy_y = 300.0, 200.0
    
    enemy_faction = 1 if rng is None or rng.random() > 0.5 else 2
    
    spawns = [
        {"faction_id": 0, "count": brain_count, "x": brain_x, "y": brain_y, "spread": 40.0, "stats": _faction_stats(profile, 0)},
        {"faction_id": enemy_faction, "count": enemy_count, "x": enemy_x, "y": enemy_y, "spread": 40.0, "stats": _faction_stats(profile, enemy_faction)},
    ]
    return spawns, {"trap_faction": enemy_faction, "target_faction": enemy_faction}

def _spawns_stage1(rng: Generator | None = None, profile: GameProfile | None = None) -> tuple[list[dict], dict]:
    """Stage 1: Target Selection (500×500 world).

    Brain(50) at left-center.  Two enemy groups on the RIGHT side, well
    separated (≥300 world units apart) so the brain CAN reach the target
    without passing through the trap's combat range.

    Trap  = 50 × 200 HP (beefy decoy, HoldPosition)
    Target = 20 ×  60 HP (correct kill target, HoldPosition)

    The model must learn to read density/HP observations and
    AttackCoord the weaker faction — ignoring the tanky decoy.
    """
    brain_count = _faction_count(profile, 0, 50)

    # 50% chance to flip faction IDs
    flip_roles = rng is not None and rng.random() > 0.5
    trap_fid = 2 if flip_roles else 1
    target_fid = 1 if flip_roles else 2

    trap_count = 50
    target_count = 50

    # Positions: randomize Y so the model CANNOT memorize a fixed corner.
    # Both groups spawn on the right side (x ~ 350-450) but at random Y
    # coordinates, with a minimum 200-unit vertical separation to prevent
    # overlapping combat ranges.
    if rng is not None:
        trap_x = 350.0 + rng.random() * 100.0   # 350–450
        target_x = 350.0 + rng.random() * 100.0  # 350–450
        # Pick two Y values with ≥200 separation
        trap_y = 60.0 + rng.random() * 180.0  # 60–240 (top half)
        target_y = 300.0 + rng.random() * 140.0  # 300–440 (bottom half)
        if rng.random() > 0.5:
            trap_y, target_y = target_y, trap_y  # flip top/bottom
    else:
        trap_x, trap_y = 400.0, 100.0
        target_x, target_y = 400.0, 400.0

    # Brain also gets slight Y jitter to break spatial memorization
    brain_y = 200.0 + (rng.random() * 100.0 if rng is not None else 50.0)

    spawns = [
        {"faction_id": 0, "count": brain_count, "x": 80.0, "y": brain_y, "spread": 60.0, "stats": _faction_stats(profile, 0)},
        {"faction_id": trap_fid, "count": trap_count, "x": trap_x, "y": trap_y, "spread": 50.0, "stats": [{"index": 0, "value": 200.0}]},
        {"faction_id": target_fid, "count": target_count, "x": target_x, "y": target_y, "spread": 50.0, "stats": [{"index": 0, "value": 24.0}]},
    ]
    return spawns, {"trap_faction": trap_fid, "target_faction": target_fid}

def _spawns_stage2(rng: Generator | None = None, profile: GameProfile | None = None) -> tuple[list[dict], dict]:
    """Stage 2: Pheromone Path (600×600).

    Two-path terrain. Fast (top) path blocked by trap fleet (40×200HP).
    Model must drop pheromone on the safe (bottom) path to attract swarm
    around the trap and reach the target.
    """
    brain_count = _faction_count(profile, 0, 50)

    flip = rng is not None and rng.random() > 0.5
    trap_fid = 2 if flip else 1
    target_fid = 1 if flip else 2

    spawns = [
        {"faction_id": 0, "count": brain_count, "x": 80.0, "y": 200.0, "spread": 50.0, "stats": _faction_stats(profile, 0)},
        {"faction_id": trap_fid, "count": 40, "x": 350.0, "y": 160.0, "spread": 40.0, "stats": [{"index": 0, "value": 200.0}]},
        {"faction_id": target_fid, "count": 20, "x": 520.0, "y": 460.0, "spread": 40.0, "stats": [{"index": 0, "value": 60.0}]},
    ]
    return spawns, {"trap_faction": trap_fid, "target_faction": target_fid}

def _spawns_stage3(rng: Generator | None = None, profile: GameProfile | None = None) -> tuple[list[dict], dict]:
    """Stage 3: Repellent Field (600×600).

    Open field with 2-3 trap groups scattered across the direct path.
    Model must drop repellent on danger zones to push swarm around them.
    Trap count is randomized (2 or 3 groups) for generalization.
    """
    brain_count = _faction_count(profile, 0, 50)
    target_fid = 1 if rng is None or rng.random() > 0.5 else 2

    # Randomly 2 or 3 trap groups (the other faction is the trap)
    trap_fid = 2 if target_fid == 1 else 1
    num_traps = 2 if rng is None else (2 + int(rng.random() > 0.5))  # 2 or 3

    # Trap positions along the diagonal direct path
    trap_positions = [
        (250.0, 180.0),   # upper-center
        (200.0, 350.0),   # center-left
        (380.0, 280.0),   # center-right (only used if 3 traps)
    ]

    spawns = [
        {"faction_id": 0, "count": brain_count, "x": 80.0, "y": 80.0, "spread": 50.0, "stats": _faction_stats(profile, 0)},
    ]
    for i in range(num_traps):
        tx, ty = trap_positions[i]
        spawns.append({
            "faction_id": trap_fid, "count": 15, "x": tx, "y": ty,
            "spread": 30.0, "stats": [{"index": 0, "value": 200.0}],
        })
    spawns.append({
        "faction_id": target_fid, "count": 20, "x": 520.0, "y": 480.0,
        "spread": 40.0, "stats": [{"index": 0, "value": 60.0}],
    })
    return spawns, {"trap_faction": trap_fid, "target_faction": target_fid}

def _spawns_stage4(rng: Generator | None = None, profile: GameProfile | None = None) -> tuple[list[dict], dict]:
    """Stage 4: Fog Scouting (800×800).

    Fog ON. Enemy at one of 4 edges, brain at center.
    Model has Scout(7) unlocked — split 10% recon to find the hidden target.
    """
    brain_count = _faction_count(profile, 0, 50)
    fid_a, fid_b = 1, 2
    target_count = 15

    edges = [(100.0, 400.0), (700.0, 400.0), (400.0, 100.0), (400.0, 700.0)]
    if rng is not None:
        idx = rng.integers(0, 4)
    else:
        import random
        idx = random.randint(0, 3)

    spawns = [
        {"faction_id": 0, "count": brain_count, "x": 400.0, "y": 400.0, "spread": 60.0, "stats": _faction_stats(profile, 0)},
        {"faction_id": fid_a, "count": target_count, "x": edges[idx][0], "y": edges[idx][1], "spread": 40.0, "stats": [{"index": 0, "value": 60.0}]},
        {"faction_id": fid_b, "count": target_count, "x": edges[(idx+2)%4][0], "y": edges[(idx+2)%4][1], "spread": 40.0, "stats": [{"index": 0, "value": 60.0}]},
    ]
    return spawns, {"trap_faction": fid_a, "target_faction": fid_a}

def _spawns_stage5(rng: Generator | None = None, profile: GameProfile | None = None) -> tuple[list[dict], dict]:
    # Stage 5: Flanking (800×800)
    brain_count = _faction_count(profile, 0, 60)
    target_fid = 1 if rng is None or rng.random() > 0.5 else 2
    defender_count = 40
    spawns = [
        {"faction_id": 0, "count": brain_count, "x": 100.0, "y": 400.0, "spread": 60.0, "stats": _faction_stats(profile, 0)},
        {"faction_id": target_fid, "count": defender_count, "x": 400.0, "y": 400.0, "spread": 40.0, "stats": _faction_stats(profile, target_fid)},
    ]
    return spawns, {"trap_faction": target_fid, "target_faction": target_fid}

def _spawns_stage6(rng: Generator | None = None, profile: GameProfile | None = None) -> tuple[list[dict], dict]:
    # Stage 6: Scout + Full Tactics (1000×1000)
    brain_count = _faction_count(profile, 0, 50)
    flip_roles = rng is not None and rng.random() > 0.5
    trap_fid = 2 if flip_roles else 1
    target_fid = 1 if flip_roles else 2
    
    patrol_count = 40
    target_count = 15
    spawns = [
        {"faction_id": 0, "count": brain_count, "x": 500.0, "y": 100.0, "spread": 60.0, "stats": _faction_stats(profile, 0)},
        {"faction_id": trap_fid, "count": patrol_count, "x": 500.0, "y": 600.0, "spread": 60.0, "stats": [{"index": 0, "value": 200.0}]},
        {"faction_id": target_fid, "count": target_count, "x": 500.0, "y": 800.0, "spread": 40.0, "stats": [{"index": 0, "value": 60.0}]},
    ]
    return spawns, {"trap_faction": trap_fid, "target_faction": target_fid}

def _spawns_stage7(rng: Generator | None = None, profile: GameProfile | None = None) -> tuple[list[dict], dict]:
    # Stage 7: Protected Target (1000×1000)
    brain_count = _faction_count(profile, 0, 60)
    flip_roles = rng is not None and rng.random() > 0.5
    trap_fid = 2 if flip_roles else 1
    target_fid = 1 if flip_roles else 2
    
    guard_count = 50
    hvt_count = 10
    spawns = [
        {"faction_id": 0, "count": brain_count, "x": 100.0, "y": 500.0, "spread": 60.0, "stats": _faction_stats(profile, 0)},
        {"faction_id": trap_fid, "count": guard_count, "x": 750.0, "y": 500.0, "spread": 80.0, "stats": [{"index": 0, "value": 200.0}]},
        {"faction_id": target_fid, "count": hvt_count, "x": 800.0, "y": 500.0, "spread": 40.0, "stats": [{"index": 0, "value": 60.0}]},
    ]
    return spawns, {"trap_faction": trap_fid, "target_faction": target_fid}

def _spawns_stage8(rng: Generator | None = None, profile: GameProfile | None = None) -> tuple[list[dict], dict]:
    # Stage 8: Randomized
    stage_choices = [1, 2, 5, 6, 7]
    if rng is not None:
        idx = rng.integers(0, len(stage_choices))
        choice = stage_choices[idx]
    else:
        import random
        choice = random.choice(stage_choices)
        
    generators = {
        1: _spawns_stage1,
        2: _spawns_stage2,
        5: _spawns_stage5,
        6: _spawns_stage6,
        7: _spawns_stage7,
    }
    return generators[choice](rng=rng, profile=profile)

def get_spawns_for_stage(stage: int, rng: Generator | None = None, profile: GameProfile | None = None) -> tuple[list[dict], dict]:
    """Dispatch to stage-specific spawn generator."""
    generators = {
        0: _spawns_stage0,
        1: _spawns_stage1,
        2: _spawns_stage2,
        3: _spawns_stage3,
        4: _spawns_stage4,
        5: _spawns_stage5,
        6: _spawns_stage6,
        7: _spawns_stage7,
        8: _spawns_stage8,
    }
    gen = generators.get(stage, _spawns_stage0)
    return gen(rng=rng, profile=profile)

def _terrain_flat(config: StageMapConfig) -> dict:
    w, h = config.active_grid_w, config.active_grid_h
    return {
        "hard_costs": [100] * (w * h),
        "soft_costs": [100] * (w * h),
        "width": w,
        "height": h,
        "cell_size": config.cell_size,
    }

def _terrain_two_path(config: StageMapConfig, seed: int) -> dict:
    """Stage 2: Two-path terrain for pheromone training.

    Layout (30×30 grid, cell_size=20 → 600×600 world):
      - Top half (y=0-12): open area → fast/short path → TRAP HERE
      - Wall band at y=13-15: permanent wall with gap at x=2-5
      - Bottom half (y=16-29): safe detour path with mud slow zone

    Brain spawns left, target spawns bottom-right.
    Flow field naturally routes through top (shorter) → into trap.
    Model must pheromone the bottom path to redirect.
    """
    w, h = config.active_grid_w, config.active_grid_h
    hard_costs = [100] * (w * h)
    soft_costs = [100] * (w * h)

    # Horizontal wall band at y=13-15, with gap at x=2-5
    wall_y_start = 13
    wall_y_end = 15
    gap_x_start = 2
    gap_x_end = 5 + (seed % 3)  # slight gap variation

    for y in range(wall_y_start, wall_y_end + 1):
        for x in range(w):
            if not (gap_x_start <= x <= gap_x_end):
                hard_costs[y * w + x] = 65535  # permanent wall (u16::MAX)

    # Mud zone on bottom path (y=20-22, x=10-20) — soft_cost=40 (slow)
    for y in range(20, min(23, h)):
        for x in range(10, min(21, w)):
            soft_costs[y * w + x] = 40

    return {
        "hard_costs": hard_costs,
        "soft_costs": soft_costs,
        "width": w,
        "height": h,
        "cell_size": config.cell_size,
    }

def _terrain_open_with_danger_zones(config: StageMapConfig, seed: int) -> dict:
    """Stage 3: Open field with high-cost zones around trap positions.

    No permanent walls. High hard_cost (300) zones around trap spawn
    points create visible "danger areas" in the terrain channel.
    The flow field will avoid high-cost zones somewhat, but the direct
    path is still cheapest — model must use repellent to fully block.
    """
    w, h = config.active_grid_w, config.active_grid_h
    hard_costs = [100] * (w * h)
    soft_costs = [100] * (w * h)

    # Danger zones around trap spawn positions (in grid coords)
    # Trap positions in world: (250,180), (200,350), (380,280)
    # Convert to grid: world / cell_size = grid
    danger_centers = [
        (12, 9),   # (250/20, 180/20) ≈ (12, 9)
        (10, 17),  # (200/20, 350/20) = (10, 17)
        (19, 14),  # (380/20, 280/20) = (19, 14)
    ]
    danger_radius = 3

    for cx, cy in danger_centers:
        for dy in range(-danger_radius, danger_radius + 1):
            for dx in range(-danger_radius, danger_radius + 1):
                gx, gy = cx + dx, cy + dy
                if 0 <= gx < w and 0 <= gy < h:
                    if dx * dx + dy * dy <= danger_radius * danger_radius:
                        hard_costs[gy * w + gx] = 300

    return {
        "hard_costs": hard_costs,
        "soft_costs": soft_costs,
        "width": w,
        "height": h,
        "cell_size": config.cell_size,
    }

def _terrain_procedural(config: StageMapConfig, seed: int) -> dict:
    # Basic procedural for later stages
    return _terrain_flat(config)

def generate_terrain_for_stage(stage: int, seed: int = 0) -> dict:
    """Generate terrain payload for the given stage."""
    config = STAGE_MAP_CONFIGS.get(stage, STAGE_MAP_CONFIGS[0])

    if stage == 2:
        return _terrain_two_path(config, seed)
    elif stage == 3:
        return _terrain_open_with_danger_zones(config, seed)
    elif stage in (7, 8):
        return _terrain_procedural(config, seed)
    else:
        return _terrain_flat(config)
