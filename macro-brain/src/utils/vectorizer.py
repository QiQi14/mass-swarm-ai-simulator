"""State vectorization: JSON snapshot → numpy observation dict.

This is the SINGLE location where raw Rust density maps (HashMap<u32, Vec<f32>>)
are packed into fixed 4-channel tensors for the neural network.
Channel assignment:
  ch0 = brain_faction
  ch1 = primary enemy
  ch2 = first sub-faction (sorted by ID)
  ch3 = second sub-faction or overflow aggregation
"""

import numpy as np
from typing import Any

from src.env.spaces import GRID_WIDTH, GRID_HEIGHT, NUM_DENSITY_CHANNELS


def vectorize_snapshot(
    snapshot: dict[str, Any],
    brain_faction: int = 0,
    enemy_faction: int = 1,
) -> dict[str, np.ndarray]:
    """Convert Rust StateSnapshot → numpy observation dict."""
    density_maps = snapshot.get("density_maps", {})
    grid_size = GRID_HEIGHT * GRID_WIDTH

    channels = [np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.float32)
                for _ in range(NUM_DENSITY_CHANNELS)]

    # ch0: brain's own forces
    key = str(brain_faction)
    if key in density_maps:
        flat = np.array(density_maps[key], dtype=np.float32)
        if len(flat) == grid_size:
            channels[0] = flat.reshape(GRID_HEIGHT, GRID_WIDTH)

    # ch1: primary enemy
    key = str(enemy_faction)
    if key in density_maps:
        flat = np.array(density_maps[key], dtype=np.float32)
        if len(flat) == grid_size:
            channels[1] = flat.reshape(GRID_HEIGHT, GRID_WIDTH)

    # ch2-3: sub-factions (sorted by ID for determinism)
    sub_factions = sorted([
        int(k) for k in density_maps.keys()
        if int(k) != brain_faction and int(k) != enemy_faction
    ])
    for i, sf in enumerate(sub_factions):
        ch_idx = min(2 + i, NUM_DENSITY_CHANNELS - 1)
        flat = np.array(density_maps[str(sf)], dtype=np.float32)
        if len(flat) == grid_size:
            if i >= NUM_DENSITY_CHANNELS - 2:
                channels[ch_idx] += flat.reshape(GRID_HEIGHT, GRID_WIDTH)
            else:
                channels[ch_idx] = flat.reshape(GRID_HEIGHT, GRID_WIDTH)

    # Terrain
    terrain = np.ones((GRID_HEIGHT, GRID_WIDTH), dtype=np.float32) * 0.5
    terrain_hard = snapshot.get("terrain_hard", [])
    if len(terrain_hard) == grid_size:
        raw = np.array(terrain_hard, dtype=np.float32)
        terrain = np.clip(raw / 65535.0, 0.0, 1.0).reshape(GRID_HEIGHT, GRID_WIDTH)

    # Summary: 6 elements
    summary_data = snapshot.get("summary", {})
    faction_counts = summary_data.get("faction_counts", {})
    faction_avg = summary_data.get("faction_avg_stats", {})
    own_count = faction_counts.get(str(brain_faction), 0)
    enemy_count = faction_counts.get(str(enemy_faction), 0)
    max_entities = 10000.0

    own_health = 0.0
    if str(brain_faction) in faction_avg:
        h = faction_avg[str(brain_faction)]
        own_health = h[0] if h else 0.0

    enemy_health = 0.0
    if str(enemy_faction) in faction_avg:
        h = faction_avg[str(enemy_faction)]
        enemy_health = h[0] if h else 0.0

    sub_faction_count = len(snapshot.get("active_sub_factions", []))
    active_zones_count = len(snapshot.get("active_zones", []))

    summary = np.array([
        min(own_count / max_entities, 1.0),
        min(enemy_count / max_entities, 1.0),
        own_health,
        enemy_health,
        min(sub_faction_count / 5.0, 1.0),
        min(active_zones_count / 10.0, 1.0),
    ], dtype=np.float32)

    return {
        "density_ch0": channels[0],
        "density_ch1": channels[1],
        "density_ch2": channels[2],
        "density_ch3": channels[3],
        "terrain": terrain,
        "summary": summary,
    }
