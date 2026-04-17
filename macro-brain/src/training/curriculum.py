"""Tactical Curriculum Stages.

10-stage curriculum (0-9) for training the swarm intelligence.
Stage 0-4: Foundational (navigation, target selection, pheromone, repellent, fog).
Stage 5-8: Physics-enforced tactical skills (AoE flanking, spread, combined arms, screening).
Stage 9:   Randomized graduation capstone.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from numpy.random import Generator
    from src.config.game_profile import GameProfile

# 8-action vocabulary for tactical curriculum
ACTION_NAMES = [
    "Hold", "AttackCoord", "ZoneModifier", "SplitToCoord",
    "MergeBack", "SetPlaystyle", "ActivateSkill", "Retreat"
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
    5: StageMapConfig(1000, 1000, 50, 50, 20.0, fog_enabled=True), # Forced Flanking
    6: StageMapConfig(1000, 1000, 50, 50, 20.0, fog_enabled=True), # Spread Formation
    7: StageMapConfig(1000, 1000, 50, 50, 20.0, fog_enabled=True), # Combined Arms
    8: StageMapConfig(1000, 1000, 50, 50, 20.0, fog_enabled=True), # Screening
    9: StageMapConfig(1000, 1000, 50, 50, 20.0, fog_enabled=True), # Randomized
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
    """Stage 2: Pheromone Fortress (600×600).

    Ranger Fortress layout — kill-order puzzle enforced by combat math.

    Rangers (target): 20×60HP inside walled fortress, HoldPosition.
      Extended-range combat rule (range 150, -12 DPS) added via
      stage_combat_rules.py — they deal ranged fire support.

    Tanks (trap): 20×200HP blocking Path A (clean, shortest entry).
      Standard melee (range 25, -25 DPS), HoldPosition.

    Brain must use DropPheromone on Path B (mud, soft_cost=40) to route
    the swarm through the safe but slow entry, kill squishy rangers
    first, then pivot to fight tanks alone.

    Wrong order (fight tanks first): -25/s melee + -12/s ranged = overwhelmed.
    Correct order (kill rangers via mud): rangers die fast → tanks alone = win
    with ×1.2 HP margin.
    """
    brain_count = _faction_count(profile, 0, 50)

    flip = rng is not None and rng.random() > 0.5
    trap_fid = 2 if flip else 1      # Tanks (melee blockers)
    target_fid = 1 if flip else 2    # Rangers (squishy ranged)

    # Fortress center — rangers spawn inside
    fortress_cx = 420.0
    fortress_cy = 300.0
    ranger_y_jitter = rng.uniform(-30, 30) if rng is not None else 0.0

    # Randomize which opening is Path A (clean+tanks) vs Path B (mud+safe)
    # top_is_clean=True  → Path A at top, Path B at bottom
    # top_is_clean=False → Path A at bottom, Path B at top
    top_is_clean = rng is None or rng.random() > 0.5

    # Tank position: at the clean (Path A) opening
    # Fortress spans roughly Y: 200-400, centered at 300
    # Top opening ~Y=200, bottom opening ~Y=400
    if top_is_clean:
        tank_x = fortress_cx - 40.0  # Just outside fortress entrance
        tank_y = 180.0               # Top opening
    else:
        tank_x = fortress_cx - 40.0
        tank_y = 420.0               # Bottom opening

    # Brain spawns on left edge with Y jitter
    brain_y = 300.0 + (rng.uniform(-100, 100) if rng is not None else 0.0)

    spawns = [
        {"faction_id": 0, "count": brain_count, "x": 80.0, "y": brain_y,
         "spread": 50.0, "stats": _faction_stats(profile, 0)},
        {"faction_id": trap_fid, "count": 20, "x": tank_x, "y": tank_y,
         "spread": 35.0, "stats": [{"index": 0, "value": 200.0}]},
        {"faction_id": target_fid, "count": 20, "x": fortress_cx, "y": fortress_cy + ranger_y_jitter,
         "spread": 30.0, "stats": [{"index": 0, "value": 60.0}]},
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
    """Stage 5: Forced Flanking — AoE Cone Enemy (1000×1000).

    Brain (60 units) spawns at left edge.
    Enemy (30 × 200 HP) HoldPosition at center with AoE cone weapon.
    Frontal charge = AoE cone death, flanking = win.
    """
    brain_count = 60
    enemy_count = 30
    enemy_fid = 1 if rng is None or rng.random() > 0.5 else 2

    brain_y = 500.0 + (rng.uniform(-60, 60) if rng is not None else 0.0)
    enemy_x = 500.0 + (rng.uniform(-20, 20) if rng is not None else 0.0)
    enemy_y = 500.0 + (rng.uniform(-20, 20) if rng is not None else 0.0)

    spawns = [
        {"faction_id": 0, "count": brain_count, "x": 100.0, "y": brain_y,
         "spread": 60.0, "stats": [{"index": 0, "value": 100.0}]},
        {"faction_id": enemy_fid, "count": enemy_count, "x": enemy_x, "y": enemy_y,
         "spread": 40.0, "stats": [{"index": 0, "value": 200.0}]},
    ]
    return spawns, {"trap_faction": enemy_fid, "target_faction": enemy_fid}

def _spawns_stage6(rng: Generator | None = None, profile: GameProfile | None = None) -> tuple[list[dict], dict]:
    """Stage 6: Speed Chase — Activate skill to outrun and meet allies (1000×1000).

    Brain (50 units) base speed 55, placed at x=100.
    Enemy (40 units) base speed 60, placed at x=350, charging.
    Allies (20 units) standard speed, placed at x=800, holding position.
    """
    brain_y = 500.0 + (rng.uniform(-20, 20) if rng is not None else 0.0)
    enemy_y = 500.0 + (rng.uniform(-20, 20) if rng is not None else 0.0)
    ally_y = 500.0 + (rng.uniform(-20, 20) if rng is not None else 0.0)

    spawns = [
        {"faction_id": 0, "count": 50, "x": 100.0, "y": brain_y,
         "spread": 60.0, "stats": [{"index": 0, "value": 100.0}], 
         "movement": {"max_speed": 55.0}},
        {"faction_id": 1, "count": 40, "x": 350.0, "y": enemy_y,
         "spread": 40.0, "stats": [{"index": 0, "value": 100.0}]},
        {"faction_id": 2, "count": 20, "x": 800.0, "y": ally_y,
         "spread": 40.0, "stats": [{"index": 0, "value": 100.0}]},
    ]
    return spawns, {"trap_faction": 1, "target_faction": 1}

def _spawns_stage7(rng: Generator | None = None, profile: GameProfile | None = None) -> tuple[list[dict], dict]:
    """Stage 7: Combined Arms Intro — Heterogeneous Brain vs Standard Enemy (1000×1000).

    Gentle introduction to heterogeneous units. No special weapons.
    Brain: 35 Infantry (class 0, 80 HP) + 15 Tanks (class 1, 300 HP, slower).
    Enemy: 40 × 150 HP, standard melee, gentle Charge.
    """
    brain_infantry = 35
    brain_tanks = 15
    enemy_count = 40
    enemy_fid = 1 if rng is None or rng.random() > 0.5 else 2

    brain_y = 500.0 + (rng.uniform(-80, 80) if rng is not None else 0.0)
    enemy_x = 750.0 + (rng.uniform(-40, 40) if rng is not None else 0.0)
    enemy_y = 500.0 + (rng.uniform(-40, 40) if rng is not None else 0.0)

    spawns = [
        {"faction_id": 0, "count": brain_infantry, "x": 150.0, "y": brain_y,
         "spread": 60.0, "stats": [{"index": 0, "value": 80.0}],
         "unit_class_id": 0},
        {"faction_id": 0, "count": brain_tanks, "x": 100.0, "y": brain_y,
         "spread": 40.0,
         "stats": [{"index": 0, "value": 300.0}, {"index": 4, "value": 0.8}],
         "unit_class_id": 1},
        {"faction_id": enemy_fid, "count": enemy_count, "x": enemy_x, "y": enemy_y,
         "spread": 50.0, "stats": [{"index": 0, "value": 150.0}]},
    ]
    return spawns, {"trap_faction": enemy_fid, "target_faction": enemy_fid}

def _spawns_stage8(rng: Generator | None = None, profile: GameProfile | None = None) -> tuple[list[dict], dict]:
    """Stage 8: Screening — Kinetic Penetration + Heterogeneous Army (1000×1000).

    Brain: 35 Infantry (class 0, 80 HP) + 15 Tanks (class 1, 300 HP, absorption).
    Enemy turrets: 10 × 200 HP, HoldPosition, Kinetic Penetration weapon.
    Protected HVT: 10 × 60 HP, HoldPosition behind turrets.
    Brain must route Tanks in front to absorb kinetic rays.
    """
    turret_fid = 1 if rng is None or rng.random() > 0.5 else 2
    hvt_fid = 2 if turret_fid == 1 else 1

    brain_y = 500.0 + (rng.uniform(-80, 80) if rng is not None else 0.0)
    turret_x = 650.0 + (rng.uniform(-30, 30) if rng is not None else 0.0)
    turret_y = 500.0 + (rng.uniform(-40, 40) if rng is not None else 0.0)
    hvt_x = turret_x + 100.0
    hvt_y = turret_y

    spawns = [
        {"faction_id": 0, "count": 35, "x": 150.0, "y": brain_y,
         "spread": 60.0, "stats": [{"index": 0, "value": 80.0}],
         "unit_class_id": 0},
        {"faction_id": 0, "count": 15, "x": 100.0, "y": brain_y,
         "spread": 40.0,
         "stats": [{"index": 0, "value": 300.0}, {"index": 4, "value": 0.8}],
         "unit_class_id": 1},
        {"faction_id": turret_fid, "count": 10, "x": turret_x, "y": turret_y,
         "spread": 60.0, "stats": [{"index": 0, "value": 200.0}]},
        {"faction_id": hvt_fid, "count": 10, "x": hvt_x, "y": hvt_y,
         "spread": 40.0, "stats": [{"index": 0, "value": 60.0}]},
    ]
    return spawns, {"trap_faction": turret_fid, "target_faction": hvt_fid}

# Module-level tracker for Stage 9 sub-stage delegation
_last_stage9_choice: int = 1

def _spawns_stage9(rng: Generator | None = None, profile: GameProfile | None = None) -> tuple[list[dict], dict]:
    """Stage 9: Randomized Graduation — picks from Stages 1-8."""
    global _last_stage9_choice
    stage_choices = [1, 2, 3, 4, 5, 6, 7, 8]
    if rng is not None:
        idx = rng.integers(0, len(stage_choices))
        choice = stage_choices[idx]
    else:
        import random
        choice = random.choice(stage_choices)

    _last_stage9_choice = choice
    generators = {
        1: _spawns_stage1, 2: _spawns_stage2, 3: _spawns_stage3,
        4: _spawns_stage4, 5: _spawns_stage5, 6: _spawns_stage6,
        7: _spawns_stage7, 8: _spawns_stage8,
    }
    return generators[choice](rng=rng, profile=profile)

def get_last_stage9_choice() -> int:
    """Return which sub-stage was picked for the last Stage 9 episode."""
    return _last_stage9_choice

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
        9: _spawns_stage9,
    }
    gen = generators.get(stage, _spawns_stage0)
    return gen(rng=rng, profile=profile)


def get_stage_snapshot(stage: int, profile: GameProfile | None = None) -> dict:
    """Generate a stage snapshot with actual per-faction spawn stats for UI display.

    Called at training start and each stage graduation. The snapshot captures
    the real HP/count values used by the spawn generators (which override the
    base profile defaults), so the debug visualizer can render correct stats.

    Returns:
        A JSON-serializable dict with stage metadata, map config, and per-faction
        spawn groups including actual HP values.
    """
    map_config = get_map_config(stage)
    # Use rng=None to get deterministic defaults (positions don't matter for UI)
    spawns, metadata = get_spawns_for_stage(stage, rng=None, profile=profile)

    # Build per-faction info from spawn data
    factions: dict[int, dict] = {}
    for spawn in spawns:
        fid = spawn["faction_id"]
        hp = 100.0
        for s in spawn.get("stats", []):
            if s["index"] == 0:
                hp = s["value"]

        if fid not in factions:
            factions[fid] = {
                "faction_id": fid,
                "groups": [],
                "total_count": 0,
                "max_hp": 0.0,
            }

        group_info: dict = {
            "count": spawn["count"],
            "hp": hp,
        }
        if spawn.get("unit_class_id") is not None:
            group_info["unit_class_id"] = spawn["unit_class_id"]

        factions[fid]["groups"].append(group_info)
        factions[fid]["total_count"] += spawn["count"]
        factions[fid]["max_hp"] = max(factions[fid]["max_hp"], hp)

    # Add faction names and roles from profile
    if profile is not None:
        for f in profile.factions:
            if f.id in factions:
                factions[f.id]["name"] = f.name
                factions[f.id]["role"] = f.role

    # Determine roles (trap/target) from metadata
    trap_fid = metadata.get("trap_faction")
    target_fid = metadata.get("target_faction")

    # Get stage description from profile
    stage_desc = ""
    if profile is not None:
        stage_config = profile.get_stage_config(stage)
        if stage_config is not None:
            stage_desc = stage_config.description

    # Get unlocked actions
    unlocked_actions: list[str] = []
    if profile is not None:
        for a in profile.actions_unlocked_at(stage):
            unlocked_actions.append(a.name)

    # Generate representative terrain for this stage (seed=0 for deterministic preview)
    terrain_data = generate_terrain_for_stage(stage, seed=0)

    return {
        "stage": stage,
        "description": stage_desc,
        "map": {
            "world_width": map_config.world_width,
            "world_height": map_config.world_height,
            "grid_w": map_config.active_grid_w,
            "grid_h": map_config.active_grid_h,
            "fog_enabled": map_config.fog_enabled,
        },
        "terrain": {
            "width": terrain_data["width"],
            "height": terrain_data["height"],
            "cell_size": terrain_data["cell_size"],
            "hard_costs": terrain_data["hard_costs"],
            "soft_costs": terrain_data["soft_costs"],
        },
        "factions": factions,
        "trap_faction": trap_fid,
        "target_faction": target_fid,
        "unlocked_actions": unlocked_actions,
    }


def _terrain_flat(config: StageMapConfig) -> dict:
    w, h = config.active_grid_w, config.active_grid_h
    return {
        "hard_costs": [100] * (w * h),
        "soft_costs": [100] * (w * h),
        "width": w,
        "height": h,
        "cell_size": config.cell_size,
    }

def _terrain_fortress(config: StageMapConfig, seed: int) -> dict:
    """Stage 2: Fortress terrain for pheromone training.

    Builds a rectangular walled enclosure (fortress) around the target
    area with exactly 2 openings:
      - Path A (clean, hard_cost=100): Shortest entry — tanks block it
      - Path B (mud, soft_cost=40): Longer entry — safe but slow

    The seed controls which opening (top/bottom of fortress) is A vs B.
    Grid is 30×30 (600×600 world, cell_size=20).

    Fortress occupies grid cells roughly:
      X: 16-26 (world X: 320-520)
      Y: 9-21  (world Y: 180-420)

    Two openings on the LEFT wall (X=16):
      Top opening:  Y=10-11 (world Y: 200-220)
      Bottom opening: Y=19-20 (world Y: 380-400)
    """
    w, h = config.active_grid_w, config.active_grid_h
    hard_costs = [100] * (w * h)
    soft_costs = [100] * (w * h)

    # Fortress wall bounds (grid coordinates)
    fort_x_min = 16
    fort_x_max = 26
    fort_y_min = 9
    fort_y_max = 21

    # Opening positions on the LEFT wall (x=fort_x_min)
    top_opening_y = (10, 11)     # 2 cells tall
    bottom_opening_y = (19, 20)  # 2 cells tall

    # Build fortress walls — all 4 sides
    for y in range(fort_y_min, fort_y_max + 1):
        for x in range(fort_x_min, fort_x_max + 1):
            is_edge = (
                x == fort_x_min or x == fort_x_max or
                y == fort_y_min or y == fort_y_max
            )
            if is_edge:
                # Check if this cell is an opening
                is_opening = False
                if x == fort_x_min:
                    if top_opening_y[0] <= y <= top_opening_y[1]:
                        is_opening = True
                    if bottom_opening_y[0] <= y <= bottom_opening_y[1]:
                        is_opening = True

                if not is_opening:
                    hard_costs[y * w + x] = 65535  # Permanent wall

    # Determine which opening is clean (Path A) vs mud (Path B)
    # seed controls randomization — same seed = same layout for reproducibility
    top_is_clean = (seed % 2) == 0

    # Path B (mud): lay mud OUTSIDE the fortress near the safe opening
    # Mud corridor extends from the opening leftward across ~6 cells
    if top_is_clean:
        # Bottom opening is mud (Path B)
        mud_opening_y = bottom_opening_y
    else:
        # Top opening is mud (Path B)
        mud_opening_y = top_opening_y

    # Mud corridor: extends from opening (x=fort_x_min) leftward
    mud_x_start = fort_x_min - 6
    mud_x_end = fort_x_min  # inclusive — mud right up to the opening
    mud_y_start = mud_opening_y[0] - 1
    mud_y_end = mud_opening_y[1] + 1

    for y in range(max(0, mud_y_start), min(h, mud_y_end + 1)):
        for x in range(max(0, mud_x_start), min(w, mud_x_end + 1)):
            soft_costs[y * w + x] = 40  # Mud: 40% speed

    return {
        "hard_costs": hard_costs,
        "soft_costs": soft_costs,
        "width": w,
        "height": h,
        "cell_size": config.cell_size,
    }

def _terrain_open_with_danger_zones(config: StageMapConfig, seed: int) -> dict:
    """Stage 3: Open field with high-cost zones around trap positions."""
    w, h = config.active_grid_w, config.active_grid_h
    hard_costs = [100] * (w * h)
    soft_costs = [100] * (w * h)

    danger_centers = [
        (12, 9),
        (10, 17),
        (19, 14),
    ]
    danger_radius = 3

    for cx, cy in danger_centers:
        for dy in range(-danger_radius, danger_radius + 1):
            for dx in range(-danger_radius, danger_radius + 1):
                gx, gy = cx + dx, cy + dy
                if 0 <= gx < w and 0 <= gy < h:
                    if dx * dx + dy * dy <= danger_radius * danger_radius:
                        hard_costs[gy * w + gx] = 400

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
        return _terrain_fortress(config, seed)
    elif stage == 3:
        return _terrain_open_with_danger_zones(config, seed)
    elif stage == 5:
        # V-wall chokepoint — delegated to terrain_generator.py
        from src.utils.terrain_generator import generate_stage5_terrain
        return generate_stage5_terrain(seed=seed)
    elif stage in (6, 7):
        return _terrain_flat(config)  # Open field for spread / combined arms
    elif stage in (8, 9):
        return _terrain_procedural(config, seed)
    else:
        return _terrain_flat(config)
