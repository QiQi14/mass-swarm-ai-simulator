import numpy as np

TIER0_PASSABLE = 100
TIER1_DESTRUCTIBLE = 62_000
TIER2_PERMANENT = 65_535

def generate_random_terrain(
    width: int = 50, height: int = 50,
    wall_density: float = 0.1,
    num_chokepoints: int = 3,
    num_swamp_patches: int = 5,
    swamp_cost_range: tuple = (30, 70),
    destructible_ratio: float = 0.4,
    seed: int | None = None,
) -> dict:
    """Generate terrain compatible with Rust TerrainGrid.
    
    Returns dict with keys matching Rust TerrainPayload:
      {"hard_costs": [...], "soft_costs": [...], "width": int, "height": int, "cell_size": float}
    
    GUARANTEES:
    1. Spawn zones (left-center, right-center) always clear
    2. BFS-verified connectivity between spawn zones
    3. If disconnected, horizontal corridor carved
    4. Mixed permanent (60%) and destructible (40%) walls
    """
    rng = np.random.default_rng(seed)
    
    # Separate grids: hard_costs for walls, soft_costs for terrain speed modifiers
    hard = np.full((height, width), TIER0_PASSABLE, dtype=np.uint16)
    soft = np.full((height, width), TIER0_PASSABLE, dtype=np.uint16)
    
    # Scatter wall clusters (affect hard_costs only)
    for _ in range(num_chokepoints):
        cx, cy = rng.integers(10, width-10), rng.integers(10, height-10)
        rr, cc = np.ogrid[-3:4, -3:4]
        mask = rr**2 + cc**2 <= 9
        sy, ey = max(0, cy-3), min(height, cy+4)
        sx, ex = max(0, cx-3), min(width, cx+4)
        m = mask[max(0, 3-cy):mask.shape[0]-max(0, (cy+4)-height), max(0, 3-cx):mask.shape[1]-max(0, (cx+4)-width)]
        hard[sy:ey, sx:ex][m] = TIER2_PERMANENT
        
    # Scatter swamp patches (affect soft_costs only, NOT hard_costs)
    for _ in range(num_swamp_patches):
        cx, cy = rng.integers(5, width-5), rng.integers(5, height-5)
        rr, cc = np.ogrid[-2:3, -2:3]
        mask = rr**2 + cc**2 <= 4
        cost = int(rng.integers(swamp_cost_range[0], swamp_cost_range[1]))
        
        sy, ey = max(0, cy-2), min(height, cy+3)
        sx, ex = max(0, cx-2), min(width, cx+3)
        m = mask[max(0, 2-cy):mask.shape[0]-max(0, (cy+3)-height), max(0, 2-cx):mask.shape[1]-max(0, (cx+3)-width)]
        region = soft[sy:ey, sx:ex]
        # Only apply swamp where there's no wall
        hard_region = hard[sy:ey, sx:ex]
        region[m & (hard_region < TIER1_DESTRUCTIBLE)] = cost

    # Scatter individual wall cells based on density
    num_cells = width * height
    num_walls = int(num_cells * wall_density)
    xs = rng.integers(0, width, num_walls)
    ys = rng.integers(0, height, num_walls)
    
    for x, y in zip(xs, ys):
        if hard[y, x] < TIER1_DESTRUCTIBLE:
            tier = TIER1_DESTRUCTIBLE if rng.random() < destructible_ratio else TIER2_PERMANENT
            hard[y, x] = tier
            
    # Guarantee spawn zones (left-center, right-center) always clear
    spawn_left = (10, 25)  # x, y 
    spawn_right = (40, 25)  # x, y 
    
    radius = 4
    for spawn in [spawn_left, spawn_right]:
        sx, sy = spawn
        rr, cc = np.ogrid[-radius:radius+1, -radius:radius+1]
        mask = rr**2 + cc**2 <= radius**2
        s_y, e_y = max(0, sy-radius), min(height, sy+radius+1)
        s_x, e_x = max(0, sx-radius), min(width, sx+radius+1)
        m = mask[max(0, radius-sy):mask.shape[0]-max(0, (sy+radius+1)-height), max(0, radius-sx):mask.shape[1]-max(0, (sx+radius+1)-width)]
        hard[s_y:e_y, s_x:e_x][m] = TIER0_PASSABLE
        soft[s_y:e_y, s_x:e_x][m] = TIER0_PASSABLE

    # BFS connectivity guarantee: left spawn to right spawn
    queue = [spawn_left]
    visited = set(queue)
    connected = False
    
    while queue:
        x, y = queue.pop(0)
        if (x, y) == spawn_right:
            connected = True
            break
            
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited:
                if hard[ny, nx] < TIER1_DESTRUCTIBLE:
                    visited.add((nx, ny))
                    queue.append((nx, ny))
                    
    if not connected:
        # Carve a horizontal corridor through both grids
        sy = spawn_left[1]
        for sx in range(spawn_left[0], spawn_right[0] + 1):
            hard[max(0, sy-1):min(height, sy+2), sx] = TIER0_PASSABLE
            soft[max(0, sy-1):min(height, sy+2), sx] = TIER0_PASSABLE
            
    return {
        "hard_costs": hard.flatten().tolist(),
        "soft_costs": soft.flatten().tolist(),
        "width": width,
        "height": height,
        "cell_size": 20.0,
    }

