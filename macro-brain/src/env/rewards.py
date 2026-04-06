import numpy as np

def flanking_bonus(
    own_density: np.ndarray,
    sub_faction_density: np.ndarray,
    enemy_density: np.ndarray,
    max_engage_radius: float = 15.0,  # Grid cells (~300 world units at 20px/cell)
) -> float:
    """Detect and reward flanking maneuvers with combat proximity guard.

    ## PATCH 5: Pacifist Flank Exploit Prevention
    The original implementation only checked projection geometry, not distance.
    An RL agent would exploit this by sending a sub-faction to the map corner,
    aligned with the projection axis, earning infinite flanking points while
    completely out of combat range.

    ## Fix
    1. Distance cutoff: sub-faction centroid must be within max_engage_radius
       of enemy centroid (in grid cells).
    2. Distance attenuation: reward decays linearly as distance increases.
       A flank at point-blank range gets full bonus; a flank at the edge
       of engage range gets near-zero bonus.

    Returns 0.0-1.0 (bonus only, never negative).
    """
    def centroid(density: np.ndarray) -> tuple[float, float] | None:
        total = density.sum()
        if total < 0.01:
            return None
        rows, cols = np.indices(density.shape)
        cy = (rows * density).sum() / total
        cx = (cols * density).sum() / total
        return (cx, cy)

    main_c = centroid(own_density)
    sub_c = centroid(sub_faction_density)
    enemy_c = centroid(enemy_density)

    if main_c is None or sub_c is None or enemy_c is None:
        return 0.0

    # ═══════════════════════════════════════════════════════════════
    # PATCH 5a: Combat Proximity Check
    # Sub-faction MUST be within engagement range of the enemy.
    # Without this, the agent parks the sub-faction at the map corner
    # and collects free flanking points forever.
    # ═══════════════════════════════════════════════════════════════
    dist_sub_to_enemy = (
        (sub_c[0] - enemy_c[0])**2 + (sub_c[1] - enemy_c[1])**2
    )**0.5

    if dist_sub_to_enemy > max_engage_radius:
        return 0.0  # Too far away — no flanking credit

    # Vector projection (existing logic)
    main_to_enemy = (enemy_c[0] - main_c[0], enemy_c[1] - main_c[1])
    main_to_sub = (sub_c[0] - main_c[0], sub_c[1] - main_c[1])

    main_to_enemy_len = (main_to_enemy[0]**2 + main_to_enemy[1]**2)**0.5
    main_to_sub_len = (main_to_sub[0]**2 + main_to_sub[1]**2)**0.5

    if main_to_enemy_len < 0.01 or main_to_sub_len < 0.01:
        return 0.0

    dot = main_to_enemy[0] * main_to_sub[0] + main_to_enemy[1] * main_to_sub[1]
    cos_sim = dot / (main_to_enemy_len * main_to_sub_len)

    if cos_sim > 0.5:
        projection_ratio = dot / (main_to_enemy_len**2)
        if projection_ratio > 1.0:
            raw_bonus = min(projection_ratio - 1.0, 1.0)

            # ═══════════════════════════════════════════════════════
            # PATCH 5b: Distance Attenuation
            # Reward decays linearly with distance to enemy.
            # At dist=0: full bonus. At dist=max_engage_radius: zero.
            # This prevents "barely in range" passive flanking.
            # ═══════════════════════════════════════════════════════
            proximity_multiplier = max(
                0.0,
                (max_engage_radius - dist_sub_to_enemy) / max_engage_radius
            )
            return raw_bonus * proximity_multiplier

    return 0.0


def compute_shaped_reward(
    snapshot: dict,
    prev_snapshot: dict | None,
    brain_faction: int = 0,
    enemy_faction: int = 1,
    weights: dict | None = None,
) -> float:
    """Compute shaped reward from state transition."""
    w = weights or {
        "survival": 0.25,
        "kill": 0.25,
        "territory": 0.15,
        "health": 0.15,
        "flanking": 0.20,
    }

    survival = 0.0
    kill = 0.0
    territory = 0.0
    health_delta = 0.0

    own_key = str(brain_faction)
    enemy_key = str(enemy_faction)

    # 1. Survival & Kill & Health Delta
    if prev_snapshot is not None:
        prev_summary = prev_snapshot.get("summary", {})
        curr_summary = snapshot.get("summary", {})
        
        prev_counts = prev_summary.get("faction_counts", {})
        curr_counts = curr_summary.get("faction_counts", {})

        prev_own = prev_counts.get(own_key, 0)
        curr_own = curr_counts.get(own_key, 0)
        prev_enemy = prev_counts.get(enemy_key, 0)
        curr_enemy = curr_counts.get(enemy_key, 0)

        # Reward staying alive
        if curr_own > 0:
            survival = 1.0
        
        # Reward eliminating enemies
        if prev_enemy > curr_enemy:
            # normalized roughly assuming small step decrements
            kill = min(float(prev_enemy - curr_enemy) / 10.0, 1.0)
            
        # Health delta
        prev_avg = prev_summary.get("faction_avg_stats", {})
        curr_avg = curr_summary.get("faction_avg_stats", {})
        
        prev_h = prev_avg.get(own_key, [0.0])[0] if own_key in prev_avg else 0.0
        curr_h = curr_avg.get(own_key, [0.0])[0] if own_key in curr_avg else 0.0
        
        health_delta = max(min(float(curr_h - prev_h) / 10.0, 1.0), -1.0)

    # 2. Territory
    density_maps = snapshot.get("density_maps", {})
    if own_key in density_maps:
        arr = np.array(density_maps[own_key])
        territory = min(float(np.count_nonzero(arr > 0.01)) / (50.0 * 50.0), 1.0)

    # 3. Flanking bonus (uses patched version with proximity guard)
    flank = 0.0
    sub_factions = snapshot.get("active_sub_factions", [])

    if own_key in density_maps and enemy_key in density_maps and sub_factions:
        own_grid = np.array(density_maps[own_key]).reshape(50, 50)
        enemy_grid = np.array(density_maps[enemy_key]).reshape(50, 50)

        for sf in sub_factions:
            sf_key = str(sf)
            if sf_key in density_maps:
                sf_grid = np.array(density_maps[sf_key]).reshape(50, 50)
                flank = max(flank, flanking_bonus(own_grid, sf_grid, enemy_grid))

    total = (
        w["survival"] * survival
        + w["kill"] * kill
        + w["territory"] * territory
        + w["health"] * health_delta
        + w["flanking"] * flank
    )
    return float(total)
