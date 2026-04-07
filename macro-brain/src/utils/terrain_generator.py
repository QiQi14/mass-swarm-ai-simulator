"""Procedural terrain generators for curriculum stages.

Stage 1-2: Flat map (terrain=None)
Stage 3:   Simple terrain — 1-2 walls, guaranteed wide corridor
Stage 4:   Complex terrain — full procedural (walls, swamps, chokepoints)

All generators guarantee:
  1. Spawn zones always clear (left, right)
  2. BFS-verified connectivity between spawns
  3. If disconnected, a horizontal corridor is carved
"""

import numpy as np

TIER0_PASSABLE = 100
TIER1_DESTRUCTIBLE = 62_000
TIER2_PERMANENT = 65_535

# Grid dimensions (must match Rust StateVectorizer: 50x50)
GRID_W = 50
GRID_H = 50
CELL_SIZE = 20.0

# Spawn zone centers in grid coordinates (matches flow field cell space)
# Left spawn: grid (10, 25) = world (200, 500)
# Right spawn: grid (40, 25) = world (800, 500)
SPAWN_LEFT = (10, 25)
SPAWN_RIGHT = (40, 25)
SPAWN_CLEAR_RADIUS = 4


def generate_flat_terrain() -> None:
    """Stages 1-2: No terrain at all. Returns None so Rust uses flat default."""
    return None


def generate_simple_terrain(seed: int | None = None) -> dict:
    """Stage 3: Simple terrain — 1-2 straight walls with gaps.

    Designed to teach the agent:
      - Basic pathfinding around a wall
      - SplitFaction to flank through the gap
      - ZoneModifier to redirect flow fields

    Layout: A single vertical wall in the center with 1-2 wide gaps.
    Much simpler than the full procedural generator. The agent should
    be able to see the wall and discover that splitting its army to
    go around both sides is better than queuing through one gap.
    """
    rng = np.random.default_rng(seed)

    hard = np.full((GRID_H, GRID_W), TIER0_PASSABLE, dtype=np.uint16)
    soft = np.full((GRID_H, GRID_W), TIER0_PASSABLE, dtype=np.uint16)

    num_walls = rng.choice([1, 2])

    for i in range(num_walls):
        # Wall position: vertical line in the middle third of the map
        if num_walls == 1:
            wall_x = rng.integers(20, 30)
        else:
            # Two walls: one in left-center, one in right-center
            wall_x = rng.integers(18, 24) if i == 0 else rng.integers(28, 34)

        # Wall height: 60-80% of map height
        wall_height = rng.integers(int(GRID_H * 0.6), int(GRID_H * 0.8))
        wall_start_y = rng.integers(0, GRID_H - wall_height)

        # Decide wall type: mostly permanent for Stage 3 (simple)
        wall_type = TIER2_PERMANENT if rng.random() < 0.7 else TIER1_DESTRUCTIBLE

        # Wall thickness: 1-2 cells
        thickness = rng.choice([1, 2])

        for dx in range(thickness):
            x = wall_x + dx
            if 0 <= x < GRID_W:
                hard[wall_start_y:wall_start_y + wall_height, x] = wall_type

        # Carve 1-2 gaps in the wall (passages)
        num_gaps = rng.choice([1, 2])
        for _ in range(num_gaps):
            gap_y = rng.integers(wall_start_y + 3, wall_start_y + wall_height - 3)
            gap_size = rng.integers(3, 6)  # 3–5 cells wide
            y_start = max(0, gap_y - gap_size // 2)
            y_end = min(GRID_H, gap_y + gap_size // 2 + 1)
            for dx in range(thickness):
                x = wall_x + dx
                if 0 <= x < GRID_W:
                    hard[y_start:y_end, x] = TIER0_PASSABLE

    # Optionally add 1-2 small swamp patches for soft cost variation
    num_swamps = rng.integers(0, 3)
    for _ in range(num_swamps):
        cx = rng.integers(5, GRID_W - 5)
        cy = rng.integers(5, GRID_H - 5)
        radius = 2
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy <= radius * radius:
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < GRID_H and 0 <= nx < GRID_W:
                        if hard[ny, nx] < TIER1_DESTRUCTIBLE:
                            soft[ny, nx] = int(rng.integers(40, 70))

    # Clear spawn zones
    _clear_spawn_zones(hard, soft)

    # BFS connectivity check
    _ensure_connectivity(hard, soft)

    return _to_payload(hard, soft)


def generate_complex_terrain(seed: int | None = None) -> dict:
    """Stage 4: Full procedural terrain — walls, chokepoints, swamps.

    Designed to teach the agent:
      - Navigating complex mazes using flow fields
      - Breaching destructible walls with zone modifiers
      - Using MergeFaction to consolidate before chokepoints
      - Timeout avoidance (must find paths, not wander)

    This is the existing generator from the original implementation,
    with parameterized difficulty.
    """
    rng = np.random.default_rng(seed)

    hard = np.full((GRID_H, GRID_W), TIER0_PASSABLE, dtype=np.uint16)
    soft = np.full((GRID_H, GRID_W), TIER0_PASSABLE, dtype=np.uint16)

    # ── Wall Clusters (chokepoints) ─────────────────────────────
    num_chokepoints = rng.integers(3, 6)
    for _ in range(num_chokepoints):
        cx = rng.integers(10, GRID_W - 10)
        cy = rng.integers(10, GRID_H - 10)
        radius = rng.integers(2, 5)

        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy <= radius * radius:
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < GRID_H and 0 <= nx < GRID_W:
                        hard[ny, nx] = TIER2_PERMANENT

    # ── Scattered Walls (density-based) ─────────────────────────
    wall_density = rng.uniform(0.05, 0.15)
    num_walls = int(GRID_W * GRID_H * wall_density)
    xs = rng.integers(0, GRID_W, num_walls)
    ys = rng.integers(0, GRID_H, num_walls)

    destructible_ratio = rng.uniform(0.3, 0.5)
    for x, y in zip(xs, ys):
        if hard[y, x] < TIER1_DESTRUCTIBLE:
            if rng.random() < destructible_ratio:
                hard[y, x] = TIER1_DESTRUCTIBLE
            else:
                hard[y, x] = TIER2_PERMANENT

    # ── Swamp Patches (soft cost modifiers) ─────────────────────
    num_swamps = rng.integers(3, 8)
    for _ in range(num_swamps):
        cx = rng.integers(5, GRID_W - 5)
        cy = rng.integers(5, GRID_H - 5)
        radius = rng.integers(2, 4)
        swamp_cost = int(rng.integers(30, 70))

        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy <= radius * radius:
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < GRID_H and 0 <= nx < GRID_W:
                        if hard[ny, nx] < TIER1_DESTRUCTIBLE:
                            soft[ny, nx] = swamp_cost

    # ── Maze-like corridors (optional, 30% chance) ──────────────
    if rng.random() < 0.3:
        _add_maze_corridors(hard, rng)

    # Clear spawn zones
    _clear_spawn_zones(hard, soft)

    # BFS connectivity check
    _ensure_connectivity(hard, soft)

    return _to_payload(hard, soft)


# ── Helpers ─────────────────────────────────────────────────────────

def _add_maze_corridors(hard: np.ndarray, rng):
    """Add 2-3 horizontal/vertical corridor walls with gaps."""
    num_corridors = rng.integers(2, 4)
    for _ in range(num_corridors):
        is_horizontal = rng.random() < 0.5
        if is_horizontal:
            y = rng.integers(8, GRID_H - 8)
            x_start = rng.integers(5, 15)
            x_end = rng.integers(35, GRID_W - 5)
            hard[y, x_start:x_end] = TIER2_PERMANENT
            # Carve 1-2 gaps
            for _ in range(rng.integers(1, 3)):
                gap_x = rng.integers(x_start + 2, x_end - 2)
                gap_size = rng.integers(3, 6)
                hard[y, gap_x:min(GRID_W, gap_x + gap_size)] = TIER0_PASSABLE
        else:
            x = rng.integers(8, GRID_W - 8)
            y_start = rng.integers(5, 15)
            y_end = rng.integers(35, GRID_H - 5)
            hard[y_start:y_end, x] = TIER2_PERMANENT
            for _ in range(rng.integers(1, 3)):
                gap_y = rng.integers(y_start + 2, y_end - 2)
                gap_size = rng.integers(3, 6)
                hard[gap_y:min(GRID_H, gap_y + gap_size), x] = TIER0_PASSABLE


def _clear_spawn_zones(hard: np.ndarray, soft: np.ndarray):
    """Guarantee spawn zones are always passable."""
    for sx, sy in [SPAWN_LEFT, SPAWN_RIGHT]:
        r = SPAWN_CLEAR_RADIUS
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r:
                    ny, nx = sy + dy, sx + dx
                    if 0 <= ny < GRID_H and 0 <= nx < GRID_W:
                        hard[ny, nx] = TIER0_PASSABLE
                        soft[ny, nx] = TIER0_PASSABLE


def _ensure_connectivity(hard: np.ndarray, soft: np.ndarray):
    """BFS from left spawn to right spawn. Carve corridor if disconnected."""
    queue = [SPAWN_LEFT]
    visited = {SPAWN_LEFT}
    connected = False

    while queue:
        x, y = queue.pop(0)
        if (x, y) == SPAWN_RIGHT:
            connected = True
            break

        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < GRID_W and 0 <= ny < GRID_H and (nx, ny) not in visited:
                if hard[ny, nx] < TIER1_DESTRUCTIBLE:
                    visited.add((nx, ny))
                    queue.append((nx, ny))

    if not connected:
        # Carve a 3-cell-wide horizontal corridor from left to right spawn
        sy = SPAWN_LEFT[1]
        for sx in range(SPAWN_LEFT[0], SPAWN_RIGHT[0] + 1):
            for dy in range(-1, 2):
                ny = sy + dy
                if 0 <= ny < GRID_H:
                    hard[ny, sx] = TIER0_PASSABLE
                    soft[ny, sx] = TIER0_PASSABLE


def _to_payload(hard: np.ndarray, soft: np.ndarray) -> dict:
    """Convert numpy grids to Rust TerrainPayload dict."""
    return {
        "hard_costs": hard.flatten().tolist(),
        "soft_costs": soft.flatten().tolist(),
        "width": GRID_W,
        "height": GRID_H,
        "cell_size": CELL_SIZE,
    }


# ── Stage-Aware Entry Point ────────────────────────────────────────

def generate_terrain_for_stage(stage: int, seed: int | None = None) -> dict | None:
    """Dispatch to the correct terrain generator based on curriculum stage.

    Stage 1-2: None (flat)
    Stage 3:   Simple (1-2 walls with gaps)
    Stage 4+:  Complex (full procedural)
    """
    if stage <= 2:
        return generate_flat_terrain()
    elif stage == 3:
        return generate_simple_terrain(seed=seed)
    else:
        return generate_complex_terrain(seed=seed)
