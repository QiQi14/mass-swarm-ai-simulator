# Feature 3: Spawn Generators & Terrain (Tasks 03–04)

## Purpose

Create new spawn generators for Stages 5–9 plus a V-wall terrain generator for Stage 5. All stages 5–9 use 1000×1000 maps for consistency.

---

## Task 03: Spawn Generators

### Target Files

- `macro-brain/src/training/curriculum.py`

### Dependencies

None (Phase 1 — spawn generators are independent of combat rules)

### Context Bindings

- `context/training` (existing spawn patterns, map configs)

---

### Strict Instructions

#### Step 1: Update `STAGE_MAP_CONFIGS`

Make Stage 5 use 1000×1000 (consistent with Stages 6–9):

```python
5: StageMapConfig(active_grid_w=50, active_grid_h=50, cell_size=20.0, fog_enabled=True),
# Already 1000×1000 — was 800×800, changed per user feedback (consistent map size)
```

#### Step 2: Add Stage 7, 8, 9 map configs

```python
7: StageMapConfig(active_grid_w=50, active_grid_h=50, cell_size=20.0, fog_enabled=True),
8: StageMapConfig(active_grid_w=50, active_grid_h=50, cell_size=20.0, fog_enabled=True),
9: StageMapConfig(active_grid_w=50, active_grid_h=50, cell_size=20.0, fog_enabled=True),
```

#### Step 3: Rewrite `_spawns_stage5()`

AoE cone flanking scenario on 1000×1000 map:

```python
def _spawns_stage5(rng=None, profile=None):
    """Stage 5: Forced Flanking — AoE Cone Enemy (1000×1000).
    
    Brain (60 units) spawns at left edge.
    Enemy (30 × 200 HP) HoldPosition at the V-chokepoint center.
    Enemy has AoE cone weapon — frontal charge = death, flanking = win.
    """
    brain_count = 60
    enemy_count = 30
    enemy_fid = 1 if rng is None or rng.random() > 0.5 else 2
    
    brain_y = 500.0 + (rng.uniform(-60, 60) if rng else 0.0)
    enemy_x = 500.0 + (rng.uniform(-20, 20) if rng else 0.0)
    enemy_y = 500.0 + (rng.uniform(-20, 20) if rng else 0.0)
    
    spawns = [
        {"faction_id": 0, "count": brain_count, "x": 100.0, "y": brain_y,
         "spread": 60.0, "stats": [{"index": 0, "value": 100.0}]},
        {"faction_id": enemy_fid, "count": enemy_count, "x": enemy_x, "y": enemy_y,
         "spread": 40.0, "stats": [{"index": 0, "value": 200.0}]},
    ]
    return spawns, {"trap_faction": enemy_fid, "target_faction": enemy_fid}
```

#### Step 4: Rewrite `_spawns_stage6()`

AoE circle spread formation scenario:

```python
def _spawns_stage6(rng=None, profile=None):
    """Stage 6: Spread Formation — AoE Circle Enemy (1000×1000).
    
    Brain (60 units) spawns at center.
    Enemy (40 × 150 HP) Charge behavior with AoE Circle splash.
    Enemy rushes brain — clumped brain = AoE wipe, spread = survive.
    """
    brain_count = 60
    enemy_count = 40
    enemy_fid = 1 if rng is None or rng.random() > 0.5 else 2
    
    brain_x = 500.0 + (rng.uniform(-40, 40) if rng else 0.0)
    brain_y = 500.0 + (rng.uniform(-40, 40) if rng else 0.0)
    
    edge = rng.integers(0, 4) if rng else 0
    edge_positions = [(100.0, 500.0), (900.0, 500.0), (500.0, 100.0), (500.0, 900.0)]
    enemy_x, enemy_y = edge_positions[edge]
    
    spawns = [
        {"faction_id": 0, "count": brain_count, "x": brain_x, "y": brain_y,
         "spread": 60.0, "stats": [{"index": 0, "value": 100.0}]},
        {"faction_id": enemy_fid, "count": enemy_count, "x": enemy_x, "y": enemy_y,
         "spread": 40.0, "stats": [{"index": 0, "value": 150.0}]},
    ]
    return spawns, {"trap_faction": enemy_fid, "target_faction": enemy_fid}
```

#### Step 5: NEW `_spawns_stage7()` — Combined Arms Intro

```python
def _spawns_stage7(rng=None, profile=None):
    """Stage 7: Combined Arms Intro — Heterogeneous Brain vs Standard Enemy (1000×1000).
    
    This is a GENTLE introduction to heterogeneous units. No special weapons.
    Brain learns:
      - It has 2 unit types (Infantry: fast/fragile, Tanks: slow/tanky)
      - Tanks naturally draw fire (higher HP)
      - Mixed approach is better than using only one class
    
    Brain: 35 Infantry (class 0, 80 HP) + 15 Tanks (class 1, 300 HP, slower)
    Enemy: 40 × 150 HP, standard melee, HoldPosition → gentle Charge.
    """
    brain_infantry = 35
    brain_tanks = 15
    enemy_count = 40
    enemy_fid = 1 if rng is None or rng.random() > 0.5 else 2
    
    brain_y = 500.0 + (rng.uniform(-80, 80) if rng else 0.0)
    enemy_x = 750.0 + (rng.uniform(-40, 40) if rng else 0.0)
    enemy_y = 500.0 + (rng.uniform(-40, 40) if rng else 0.0)
    
    spawns = [
        # Brain Infantry (class 0) — fast scouts
        {"faction_id": 0, "count": brain_infantry, "x": 150.0, "y": brain_y,
         "spread": 60.0, "stats": [{"index": 0, "value": 80.0}],
         "unit_class_id": 0},
        # Brain Tanks (class 1) — slow but tanky, slightly behind
        {"faction_id": 0, "count": brain_tanks, "x": 100.0, "y": brain_y,
         "spread": 40.0,
         "stats": [{"index": 0, "value": 300.0}, {"index": 4, "value": 0.8}],
         "unit_class_id": 1},
        # Standard enemy
        {"faction_id": enemy_fid, "count": enemy_count, "x": enemy_x, "y": enemy_y,
         "spread": 50.0, "stats": [{"index": 0, "value": 150.0}]},
    ]
    return spawns, {"trap_faction": enemy_fid, "target_faction": enemy_fid}
```

#### Step 6: NEW `_spawns_stage8()` — Screening (Kinetic Penetration)

```python
def _spawns_stage8(rng=None, profile=None):
    """Stage 8: Screening — Kinetic Penetration + Heterogeneous Army (1000×1000).
    
    Brain heterogeneous:
      Class 0 (Infantry): 35 × 80 HP
      Class 1 (Tank):     15 × 300 HP, stat[4]=0.8 absorption, slower
    
    Enemy turrets: 10 × 200 HP, HoldPosition, Kinetic Penetration weapon.
    Protected HVT: 10 × 60 HP, HoldPosition behind turrets.
    
    Brain must route Tanks in front of Infantry to absorb kinetic rays.
    """
    turret_fid = 1 if rng is None or rng.random() > 0.5 else 2
    hvt_fid = 2 if turret_fid == 1 else 1
    
    brain_y = 500.0 + (rng.uniform(-80, 80) if rng else 0.0)
    turret_x = 650.0 + (rng.uniform(-30, 30) if rng else 0.0)
    turret_y = 500.0 + (rng.uniform(-40, 40) if rng else 0.0)
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
```

#### Step 7: Rewrite `_spawns_stage9()` — Randomized Pool (was Stage 8)

```python
_last_stage9_choice: int = 1  # Module-level tracker

def _spawns_stage9(rng=None, profile=None):
    """Stage 9: Randomized — picks from Stages 1-8."""
    global _last_stage9_choice
    stage_choices = [1, 2, 3, 4, 5, 6, 7, 8]
    choice = stage_choices[rng.integers(0, len(stage_choices))] if rng else 1
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
```

#### Step 8: Update `get_spawns_for_stage()` dispatch

Add Stages 7, 8, 9 to the dispatch dict.

---

## Task 04: V-Wall Terrain Generator

### Target Files

- `macro-brain/src/utils/terrain_generator.py`

### Dependencies

None (Phase 1)

### Strict Instructions

#### Add `generate_stage5_terrain()` — V-wall on 1000×1000 (50×50 grid)

```python
def generate_stage5_terrain(seed=None):
    """Stage 5: V-shaped wall chokepoint for forced flanking (1000×1000).
    
    Layout (50×50 grid, cell_size=20 → 1000×1000 world):
      - Open left side (brain spawn zone)
      - V-shaped permanent wall at center, opening toward brain
      - Open flanks above and below the V
      - Enemy sits at the V's apex
    
    V geometry (in grid coords, 50×50):
      Left tip: x=20, y=25 (center of map)
      Upper arm: from (20,25) to (38,10)  — wall thickness 2
      Lower arm: from (20,25) to (38,40) — wall thickness 2
    """
    from src.training.curriculum import get_map_config
    config = get_map_config(5)
    w, h = config.active_grid_w, config.active_grid_h  # 50×50
    
    hard = np.full((h, w), TIER0_PASSABLE, dtype=np.uint16)
    soft = np.full((h, w), TIER0_PASSABLE, dtype=np.uint16)
    rng = np.random.default_rng(seed)
    
    tip_x, tip_y = 20, 25
    end_x = 38
    tip_x += int(rng.integers(-1, 2))
    upper_end_y = 10 + int(rng.integers(-2, 3))
    lower_end_y = 40 + int(rng.integers(-2, 3))
    
    _draw_thick_line(hard, tip_x, tip_y, end_x, upper_end_y, thickness=2)
    _draw_thick_line(hard, tip_x, tip_y, end_x, lower_end_y, thickness=2)
    
    return {
        "hard_costs": hard.flatten().tolist(),
        "soft_costs": soft.flatten().tolist(),
        "width": w, "height": h, "cell_size": config.cell_size,
    }
```

#### Update `generate_terrain_for_stage()` dispatch

```python
def generate_terrain_for_stage(stage, seed=None):
    if stage <= 1:
        return generate_flat_terrain()
    elif stage == 2:
        return generate_stage2_terrain(seed=seed)
    elif stage == 3:
        return generate_stage3_terrain(seed=seed)
    elif stage == 5:
        return generate_stage5_terrain(seed=seed)
    elif stage in (6, 7):
        return generate_flat_terrain()  # Open field
    else:
        return generate_complex_terrain(seed=seed)
```

> [!NOTE]
> - **Stage 6:** Open field (flat). AoE circle works purely via damage physics.
> - **Stage 7:** Open field (flat). Combined arms intro — no terrain needed.
> - **Stage 8:** Complex terrain (existing generator) — turrets + terrain add difficulty.

---

## Verification Strategy

### Task 03 (Spawns)

```yaml
Acceptance_Criteria:
  - "Stage 5: brain=60, enemy=30 (200 HP)"
  - "Stage 6: brain=60, enemy=40 (150 HP)"
  - "Stage 7: infantry=35 (class 0, 80 HP), tanks=15 (class 1, 300 HP), enemy=40 (150 HP)"
  - "Stage 8: infantry=35, tanks=15, turrets=10 (200 HP), hvt=10 (60 HP)"
  - "Stage 9: pool includes stages 1-8, get_last_stage9_choice() works"
  - "get_map_config(5).active_grid_w == 50 (1000×1000)"
```

### Task 04 (Terrain)

```yaml
Acceptance_Criteria:
  - "generate_stage5_terrain() returns dict with hard_costs of length 2500 (50×50)"
  - "V-wall cells are 65535, non-wall are 100"
  - "Stage 6 & 7 terrain is flat (generate_flat_terrain)"
```
