# Task 02: Python Curriculum, Actions & Navigation Persistence

```yaml
Task_ID: task_02_python_curriculum_actions
Execution_Phase: 2
Model_Tier: advanced
Feature: "Curriculum Stage 2 & 3 Adjustment"
Dependencies:
  - task_01_rust_zone_duration_config (zone_modifier_duration_ticks field in AbilityConfigPayload)
Context_Bindings:
  - context/engine-mechanics
  - context/training-curriculum
  - context/ipc-protocol
  - context/conventions
Target_Files:
  - macro-brain/src/utils/terrain_generator.py
  - macro-brain/src/training/curriculum.py
  - macro-brain/src/env/actions.py
  - macro-brain/src/env/swarm_env.py
  - macro-brain/src/config/definitions.py
  - macro-brain/src/config/parser.py
  - macro-brain/src/config/game_profile.py
  - macro-brain/profiles/tactical_curriculum.json
```

## Objective

Fix four issues in the Python macro-brain:

1. **Stage 3 terrain exploit** — danger zones use `hard_cost=300`, which the flow field auto-avoids. Change to `hard_cost=100` with `soft_cost=40` visual markers.
2. **Stage 2 terrain** — `terrain_generator.py` returns `None` for Stage 2, but Stage 2 needs the two-path terrain from `curriculum.py`. Wire Stage 2 to the correct terrain generator.
3. **Repellent cost modifier** — `+50` is too weak. Change to `+200`.
4. **Navigation persistence** — zone modifiers replace the movement directive. Cache and replay the last navigation directive when casting zone abilities.
5. **Zone duration config** — Pass `zone_modifier_duration_ticks: 1500` through the profile pipeline.

---

## Strict Instructions

### Step 1: Fix Stage 2 & 3 Terrain in `terrain_generator.py`

**File:** `macro-brain/src/utils/terrain_generator.py`

The `generate_terrain_for_stage` function (line 273) currently dispatches:
- Stage ≤ 2 → `None` (flat)
- Stage 3 → `generate_simple_terrain` (walls with gaps — WRONG for Stage 3)

But the curriculum requires:
- **Stage 2** → Two-path terrain (wall band with gap, trap on fast path, mud on slow path)
- **Stage 3** → Open field with normal-cost danger zones around trap positions

**1a.** Add a new function `generate_stage2_terrain`:

```python
def generate_stage2_terrain(seed: int | None = None) -> dict:
    """Stage 2: Two-path terrain for pheromone training.

    Layout (30×30 grid within center of 50×50, cell_size=20 → 600×600 active world):
      - Top half (y=0-12): open area — fast/short path — TRAP HERE
      - Wall band at y=13-15: permanent wall (65535) with gap at x=2-5
      - Bottom half (y=16-29): safe detour path with mud slow zone (soft_cost=40)

    Brain spawns left, target spawns bottom-right.
    Flow field naturally routes through top (shorter) → into trap.
    Model must pheromone the bottom path to redirect.

    NOTE: Uses the ACTIVE grid size (30×30) from StageMapConfig,
    NOT the full 50×50 observation grid.
    """
    from src.training.curriculum import get_map_config
    config = get_map_config(2)
    w, h = config.active_grid_w, config.active_grid_h  # 30×30

    hard = np.full((h, w), TIER0_PASSABLE, dtype=np.uint16)
    soft = np.full((h, w), TIER0_PASSABLE, dtype=np.uint16)

    rng = np.random.default_rng(seed)

    # Horizontal wall band at y=13-15, with gap at x=2-5
    wall_y_start = 13
    wall_y_end = 15
    gap_x_start = 2
    gap_x_end = 5 + (seed % 3 if seed else 0)  # slight gap variation

    for y in range(wall_y_start, wall_y_end + 1):
        for x in range(w):
            if not (gap_x_start <= x <= gap_x_end):
                hard[y, x] = TIER2_PERMANENT

    # Mud zone on bottom path (y=20-22, x=10-20)
    for y in range(20, min(23, h)):
        for x in range(10, min(21, w)):
            soft[y, x] = 40

    return {
        "hard_costs": hard.flatten().tolist(),
        "soft_costs": soft.flatten().tolist(),
        "width": w,
        "height": h,
        "cell_size": config.cell_size,
    }
```

**1b.** Add a new function `generate_stage3_terrain`:

```python
def generate_stage3_terrain(seed: int | None = None) -> dict:
    """Stage 3: Open field — danger zones are NORMAL COST terrain.

    The direct path goes straight through trap spawn positions at cost 100.
    The flow field will route directly through them by default.
    The agent MUST cast DropRepellent (+200 cost) on these zones to
    push the flow field around the traps.

    Danger centers are marked with soft_cost = 40 (visual mud markers)
    so the observation space can detect them via the terrain channel,
    but hard_cost stays at 100 (normal) — pathfinder routes THROUGH.

    NOTE: Uses the ACTIVE grid size (30×30) from StageMapConfig.
    """
    from src.training.curriculum import get_map_config
    config = get_map_config(3)
    w, h = config.active_grid_w, config.active_grid_h  # 30×30

    hard = np.full((h, w), TIER0_PASSABLE, dtype=np.uint16)
    soft = np.full((h, w), TIER0_PASSABLE, dtype=np.uint16)

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
                        # hard_cost stays 100 (normal) — pathfinder GOES THROUGH
                        # soft_cost = 40 (visual marker in terrain observation channel)
                        soft[gy, gx] = 40

    return {
        "hard_costs": hard.flatten().tolist(),
        "soft_costs": soft.flatten().tolist(),
        "width": w,
        "height": h,
        "cell_size": config.cell_size,
    }
```

**1c.** Update the `generate_terrain_for_stage` dispatch:

```python
def generate_terrain_for_stage(stage: int, seed: int | None = None) -> dict | None:
    """Dispatch to the correct terrain generator based on curriculum stage."""
    if stage <= 1:
        return generate_flat_terrain()
    elif stage == 2:
        return generate_stage2_terrain(seed=seed)
    elif stage == 3:
        return generate_stage3_terrain(seed=seed)
    else:
        return generate_complex_terrain(seed=seed)
```

> [!IMPORTANT]
> The old `generate_simple_terrain` is no longer used by Stage 3. You may leave it in the file (it might be useful for later stages) but do NOT delete it.

---

### Step 2: Fix Repellent Cost Modifier

**File:** `macro-brain/src/env/actions.py`

Find the `ACTION_DROP_REPELLENT` handler (~line 146-150):

```python
elif action_type == ACTION_DROP_REPELLENT:
    directives.append(build_set_zone_modifier_directive(
        brain_faction, world_x, world_y,
        radius=100.0, cost_modifier=50.0,
    ))
```

Change `cost_modifier=50.0` to `cost_modifier=200.0`:

```python
elif action_type == ACTION_DROP_REPELLENT:
    directives.append(build_set_zone_modifier_directive(
        brain_faction, world_x, world_y,
        radius=100.0, cost_modifier=200.0,  # +200 per conventions.md
    ))
```

---

### Step 3: Add Navigation Persistence

**File:** `macro-brain/src/env/actions.py`

**3a.** Change the return type of `multidiscrete_to_directives` to include the cached nav directive. Add a `last_nav_directive` parameter:

```python
def multidiscrete_to_directives(
    action: np.ndarray,
    brain_faction: int,
    active_sub_factions: list[int],
    cell_size: float = 20.0,
    pad_offset_x: float = 0.0,
    pad_offset_y: float = 0.0,
    split_percentage: float = 0.30,
    scout_percentage: float = 0.10,
    last_nav_directive: dict | None = None,
) -> tuple[list[dict], dict | None]:
    """Map MultiDiscrete [action_type, flat_coord] to directive list.

    Args:
        action: numpy array of shape (2,) — [action_idx, flat_coord].
        brain_faction: Brain faction ID.
        active_sub_factions: Currently active sub-faction IDs.
        cell_size: World units per grid cell.
        pad_offset_x: Grid padding offset X (for center-padded maps).
        pad_offset_y: Grid padding offset Y.
        split_percentage: Fraction of swarm to split off (SplitToCoord).
        scout_percentage: Fraction of swarm for scout group.
        last_nav_directive: Cached last AttackCoord/Retreat directive for replay.

    Returns:
        Tuple of (directives, updated_last_nav_directive).
        The caller caches the second element for the next step.
    """
```

**3b.** Track nav updates. Initialize at the top of the function body:

```python
    updated_nav = last_nav_directive  # default: no change
```

**3c.** In `ACTION_ATTACK_COORD` handler, cache the nav directive:

```python
    elif action_type == ACTION_ATTACK_COORD:
        nav = build_update_nav_directive(
            brain_faction,
            target_waypoint=(world_x, world_y),
        )
        directives.append(nav)
        updated_nav = nav
```

**3d.** In `ACTION_DROP_PHEROMONE` and `ACTION_DROP_REPELLENT` handlers, replay last nav after the zone modifier:

```python
    elif action_type == ACTION_DROP_PHEROMONE:
        directives.append(build_set_zone_modifier_directive(
            brain_faction, world_x, world_y,
            radius=100.0, cost_modifier=-50.0,
        ))
        # Replay last navigation so the swarm keeps moving
        if last_nav_directive is not None:
            directives.append(last_nav_directive)

    elif action_type == ACTION_DROP_REPELLENT:
        directives.append(build_set_zone_modifier_directive(
            brain_faction, world_x, world_y,
            radius=100.0, cost_modifier=200.0,
        ))
        # Replay last navigation so the swarm keeps moving
        if last_nav_directive is not None:
            directives.append(last_nav_directive)
```

**3e.** In `ACTION_RETREAT` handler, also cache the nav:

```python
    elif action_type == ACTION_RETREAT:
        nav = build_retreat_directive(
            brain_faction, world_x, world_y,
        )
        directives.append(nav)
        updated_nav = nav
```

**3f.** In `ACTION_HOLD` handler, clear the nav cache (Hold means stop):

```python
    if action_type == ACTION_HOLD:
        directives.append(build_hold_directive(brain_faction))
        updated_nav = None  # Clear cache — Hold means stop
```

**3g.** Change the return statement at the end:

```python
    return directives, updated_nav
```

---

### Step 4: Wire Nav Cache in SwarmEnv

**File:** `macro-brain/src/env/swarm_env.py`

**4a.** In `__init__` (around line 88-90 area), add:

```python
self._last_nav_directive: dict | None = None
```

**4b.** In `reset()`, clear the cache (alongside existing resets around line 182-189):

```python
self._last_nav_directive = None
```

**4c.** In `step()`, update the call to `multidiscrete_to_directives` (line 294-301). Change:

```python
brain_directive = multidiscrete_to_directives(
    action,
    brain_faction=self.brain_faction,
    active_sub_factions=self._active_sub_factions,
    cell_size=self._cell_size,
    pad_offset_x=self._pad_offset_x,
    pad_offset_y=self._pad_offset_y,
)
```

To:

```python
brain_directive, self._last_nav_directive = multidiscrete_to_directives(
    action,
    brain_faction=self.brain_faction,
    active_sub_factions=self._active_sub_factions,
    cell_size=self._cell_size,
    pad_offset_x=self._pad_offset_x,
    pad_offset_y=self._pad_offset_y,
    last_nav_directive=self._last_nav_directive,
)
```

---

### Step 5: Add `zone_modifier_duration_ticks` to Python Config Pipeline

**5a. File:** `macro-brain/src/config/definitions.py`

Add `zone_modifier_duration_ticks` field to `AbilitiesDef` (line 86-91):

```python
@dataclass(frozen=True)
class AbilitiesDef:
    buff_cooldown_ticks: int
    movement_speed_stat: int | None
    combat_damage_stat: int | None
    activate_buff: ActivateBuffDef
    zone_modifier_duration_ticks: int = 1500
```

**5b. File:** `macro-brain/src/config/parser.py`

In `_parse_profile`, update the `AbilitiesDef` construction (line 76-84):

```python
    abilities = AbilitiesDef(
        buff_cooldown_ticks=ab_raw["buff_cooldown_ticks"],
        movement_speed_stat=ab_raw.get("movement_speed_stat"),
        combat_damage_stat=ab_raw.get("combat_damage_stat"),
        activate_buff=ActivateBuffDef(
            modifiers=[StatModifierDef(**m) for m in buff_raw["modifiers"]],
            duration_ticks=buff_raw["duration_ticks"]
        ),
        zone_modifier_duration_ticks=ab_raw.get("zone_modifier_duration_ticks", 1500),
    )
```

**5c. File:** `macro-brain/src/config/game_profile.py`

Update `ability_config_payload()` (line 89-95):

```python
    def ability_config_payload(self) -> dict:
        """Serialize ability config for ZMQ ResetEnvironment payload."""
        return {
            "buff_cooldown_ticks": self.abilities.buff_cooldown_ticks,
            "movement_speed_stat": self.abilities.movement_speed_stat,
            "combat_damage_stat": self.abilities.combat_damage_stat,
            "zone_modifier_duration_ticks": self.abilities.zone_modifier_duration_ticks,
        }
```

**5d. File:** `macro-brain/profiles/tactical_curriculum.json`

Add `zone_modifier_duration_ticks` to the abilities section (line 75-86). Insert after `"combat_damage_stat": 2,`:

```json
"abilities": {
    "buff_cooldown_ticks": 180,
    "movement_speed_stat": 1,
    "combat_damage_stat": 2,
    "zone_modifier_duration_ticks": 1500,
    "activate_buff": {
        "modifiers": [
            { "stat_index": 0, "modifier_type": "Multiplier", "value": 0.25 },
            { "stat_index": 2, "modifier_type": "Multiplier", "value": 0.25 }
        ],
        "duration_ticks": 9999
    }
}
```

---

## Anti-Patterns

- **DO NOT** remove the terrain generators from `curriculum.py` (they may be used by tests)
- **DO NOT** change `generate_simple_terrain` or `generate_complex_terrain` — leave them as-is
- **DO NOT** add dense rewards for using Pheromone/Repellent (the strategist explicitly rejected this)
- **DO NOT** change the return type of `build_set_zone_modifier_directive` — it stays as-is
- **DO NOT** use `soft_cost` in `generate_stage3_terrain`'s hard_costs array — only soft_costs

---

## Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: integration
  Test_Stack: Python (pytest)
  Acceptance_Criteria:
    - "generate_terrain_for_stage(2) returns a two-path dict (not None)"
    - "generate_terrain_for_stage(3) returns a dict with all hard_costs == 100 and some soft_costs == 40"
    - "multidiscrete_to_directives returns a tuple (list, dict|None)"
    - "ACTION_DROP_REPELLENT produces cost_modifier=200.0"
    - "Casting DropPheromone after AttackCoord replays the nav directive"
    - "tactical_curriculum.json loads with zone_modifier_duration_ticks=1500"
    - "All existing tests pass: cd macro-brain && .venv/bin/python -m pytest tests/ -v"
  Suggested_Test_Commands:
    - "cd macro-brain && .venv/bin/python -m pytest tests/ -v"
    - "cd macro-brain && .venv/bin/python -c \"from src.config.game_profile import load_profile; p=load_profile('profiles/tactical_curriculum.json'); print(p.abilities.zone_modifier_duration_ticks)\""
    - "cd macro-brain && .venv/bin/python -c \"from src.utils.terrain_generator import generate_terrain_for_stage; t=generate_terrain_for_stage(3); print('max hard_cost:', max(t['hard_costs']))\""
```
