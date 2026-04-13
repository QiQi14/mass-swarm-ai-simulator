# Task 07: 8-Stage Curriculum Spawn Generators

```yaml
Task_ID: task_07_curriculum_stages
Execution_Phase: 2
Model_Tier: standard
Dependencies:
  - task_01_action_obs_spaces
Target_Files:
  - macro-brain/src/training/curriculum.py
Context_Bindings:
  - context/architecture
  - context/conventions
```

## Objective

Rewrite `curriculum.py` with spawn generators, map configs, and terrain generators for all 8 curriculum stages.

## Strict Instructions

### 1. Replace module content completely

The old curriculum had 3 sub-stages for one scenario. The new curriculum has 8 distinct stages with different map sizes, faction configs, terrain layouts, and fog settings.

### 2. Stage Configuration Data Structure

```python
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
    1: StageMapConfig(500, 500, 25, 25, 20.0, fog_enabled=False),
    2: StageMapConfig(800, 800, 40, 40, 20.0, fog_enabled=True),
    3: StageMapConfig(600, 600, 30, 30, 20.0, fog_enabled=False),
    4: StageMapConfig(600, 600, 30, 30, 20.0, fog_enabled=False),
    5: StageMapConfig(800, 800, 40, 40, 20.0, fog_enabled=False),
    6: StageMapConfig(1000, 1000, 50, 50, 20.0, fog_enabled=False),
    7: StageMapConfig(1000, 1000, 50, 50, 20.0, fog_enabled=True),
    8: StageMapConfig(1000, 1000, 50, 50, 20.0, fog_enabled=True),  # randomized
}
```

### 3. Spawn Generators (one per stage)

Each function returns a list of spawn dicts compatible with the ZMQ reset payload:

```python
def get_spawns_for_stage(stage: int, rng=None, profile=None) -> list[dict]:
    """Dispatch to stage-specific spawn generator."""
    generators = {
        1: _spawns_stage1,
        2: _spawns_stage2,
        3: _spawns_stage3,
        4: _spawns_stage4,
        5: _spawns_stage5,
        6: _spawns_stage6,
        7: _spawns_stage7,
        8: _spawns_stage8,
    }
    gen = generators.get(stage, _spawns_stage1)
    return gen(rng=rng, profile=profile)
```

#### Stage 1: Target Selection (500×500 world)

- Brain(50) at center (250, 250)
- Sub-stages: 1a/1b/1c based on internal counter or rng
  - Trap(50) and Target(20) at two fixed positions, swapped or randomized
- Positions scaled to the 500×500 world

#### Stage 2: Scouting (800×800)

- Brain(50) at center (400, 400)
- Target(25) at random edge: (100, 400), (700, 400), (400, 100), or (400, 700)
- No terrain

#### Stage 3: Wall Navigation (600×600)

- Brain(50) at (150, 300) — left side
- Target(20) at (450, 300) — right side, behind wall
- Terrain: horizontal wall with 3-cell gap at random position

#### Stage 4: Pheromone (600×600)

- Brain(50) at (100, 100) — top-left of L
- Target(30) at (450, 450) — bottom-right of L
- Terrain: L-shaped corridor walls

#### Stage 5: Flanking (800×800)

- Brain(60) at (100, 400) — left side
- Defender(40) at (400, 400) — center

#### Stage 6: Lure (1000×1000)

- Brain(50) at (500, 100) — top center
- Patrol(40) at (500, 600) — near target
- Target(15) at (500, 800) — bottom

#### Stage 7: Protected Target (1000×1000)

- Brain(60) at (100, 500) — left edge
- Guard(50) patrolling around HVT
- HVT(10) at (800, 500) — right side, semi-enclosed

#### Stage 8: Randomized

- Randomly select one of stages 1, 2, 5, 6, 7 layouts

### 4. Terrain Generators

Implement terrain generation helpers:

```python
def generate_terrain_for_stage(stage: int, seed: int = 0) -> dict:
    """Generate terrain payload for the given stage."""
    config = STAGE_MAP_CONFIGS.get(stage, STAGE_MAP_CONFIGS[1])
    
    if stage == 3:
        return _terrain_wall_with_gap(config, seed)
    elif stage == 4:
        return _terrain_l_corridor(config, seed)
    elif stage in (7, 8):
        return _terrain_procedural(config, seed)
    else:
        return _terrain_flat(config)
```

Each terrain function returns:
```python
{
    "hard_costs": [...],  # flat list, row-major, active_grid_w * active_grid_h
    "soft_costs": [...],
    "width": active_grid_w,
    "height": active_grid_h,
    "cell_size": cell_size,
}
```

### 5. Get Map Config Helper

```python
def get_map_config(stage: int) -> StageMapConfig:
    """Get map configuration for a curriculum stage."""
    return STAGE_MAP_CONFIGS.get(stage, STAGE_MAP_CONFIGS[1])
```

### 6. Keep `ACTION_NAMES` reference

Update the module-level `ACTION_NAMES` to match the new 8-action vocabulary.

## Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: unit
  Test_Stack: pytest (macro-brain)
  Acceptance_Criteria:
    - "get_spawns_for_stage(1) returns 3 factions with correct counts"
    - "get_spawns_for_stage(2) places target at random edge"
    - "get_map_config(1).active_grid_w == 25"
    - "get_map_config(6).active_grid_w == 50"
    - "get_map_config(2).fog_enabled == True"
    - "get_map_config(3).fog_enabled == False"
    - "generate_terrain_for_stage(3) produces wall with gap"
    - "generate_terrain_for_stage(1) produces flat terrain (all zeros)"
    - "Stage 8 randomly selects from pool"
    - "All spawn coordinates are within world bounds"
  Suggested_Test_Commands:
    - "cd macro-brain && python -m pytest tests/test_curriculum.py -v"
```
