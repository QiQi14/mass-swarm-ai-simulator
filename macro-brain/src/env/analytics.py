"""Density analytics — helper functions for spatial density computations.

Extracted from swarm_env.py to meet the 350-line file size convention.
"""

from __future__ import annotations

import numpy as np


def get_density_centroid(
    snapshot: dict | None,
    faction: int,
    world_width: float,
    world_height: float,
    grid_width: int,
    grid_height: int,
) -> tuple[float, float]:
    """Compute centroid of a faction's density heatmap.

    Returns the center of the world if the snapshot is missing or empty.
    """
    default = (world_width / 2.0, world_height / 2.0)

    if snapshot is None:
        return default

    density_maps = snapshot.get("density_maps", {})
    key = str(faction)
    if key not in density_maps:
        return default

    flat = np.array(density_maps[key], dtype=np.float32)
    if len(flat) != grid_width * grid_height:
        return default

    grid = flat.reshape(grid_height, grid_width)
    total = grid.sum()
    if total < 0.01:
        return default

    rows, cols = np.indices(grid.shape)
    cy_cell = (rows * grid).sum() / total
    cx_cell = (cols * grid).sum() / total

    cell_w = world_width / grid_width
    cell_h = world_height / grid_height
    return float(cx_cell * cell_w), float(cy_cell * cell_h)


def compute_flanking(
    snapshot: dict,
    brain_faction: int,
    enemy_faction: int,
    active_sub_factions: list[int],
    grid_width: int,
    grid_height: int,
) -> float:
    """Compute flanking bonus from density heatmaps.

    Returns 0.0 if no sub-factions exist (Stages 1-2).
    """
    if not active_sub_factions:
        return 0.0

    density = snapshot.get("density_heatmap", {})
    own_key = str(brain_faction)
    enemy_key = str(enemy_faction)

    own_density = density.get(own_key)
    enemy_density = density.get(enemy_key)

    if own_density is None or enemy_density is None:
        return 0.0

    from src.env.rewards import flanking_bonus

    own_arr = np.array(own_density, dtype=np.float32).reshape(grid_height, grid_width)
    enemy_arr = np.array(enemy_density, dtype=np.float32).reshape(grid_height, grid_width)

    total_bonus = 0.0
    for sf_id in active_sub_factions:
        sf_key = str(sf_id)
        sf_density = density.get(sf_key)
        if sf_density is not None:
            sf_arr = np.array(sf_density, dtype=np.float32).reshape(grid_height, grid_width)
            total_bonus += flanking_bonus(own_arr, sf_arr, enemy_arr)

    return total_bonus
