"""State vectorization: JSON snapshot → numpy observation dict.

This is the SINGLE location where raw Rust density maps (HashMap<u32, Vec<f32>>)
are packed into fixed 4-channel tensors for the neural network.

Channel assignment (multi-faction aware):
  ch0 = brain faction
  ch1 = first enemy faction (lowest faction ID)
  ch2 = second enemy faction (next faction ID)
  ch3 = overflow / sub-factions aggregation
"""

import numpy as np
from typing import Any

from src.env.spaces import GRID_WIDTH, GRID_HEIGHT, NUM_DENSITY_CHANNELS


def vectorize_snapshot(
    snapshot: dict[str, Any],
    brain_faction: int = 0,
    enemy_factions: list[int] | int = 1,
) -> dict[str, np.ndarray]:
    """Convert Rust StateSnapshot → numpy observation dict.

    Args:
        snapshot: Raw JSON from Rust containing density_maps, terrain, summary.
        brain_faction: Faction ID of the RL agent.
        enemy_factions: Single faction ID or list of enemy faction IDs.
    """
    # Normalize enemy_factions to a sorted list
    if isinstance(enemy_factions, int):
        enemy_factions = [enemy_factions]
    enemy_factions = sorted(enemy_factions)

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

    # ch1..chN: enemy factions (sorted by ID for determinism)
    for i, ef in enumerate(enemy_factions):
        ch_idx = min(1 + i, NUM_DENSITY_CHANNELS - 1)
        key = str(ef)
        if key in density_maps:
            flat = np.array(density_maps[key], dtype=np.float32)
            if len(flat) == grid_size:
                if i >= NUM_DENSITY_CHANNELS - 1:
                    # Overflow: aggregate into last channel
                    channels[ch_idx] += flat.reshape(GRID_HEIGHT, GRID_WIDTH)
                else:
                    channels[ch_idx] = flat.reshape(GRID_HEIGHT, GRID_WIDTH)

    # Remaining channels: sub-factions
    known_factions = set([brain_faction] + enemy_factions)
    sub_factions = sorted([
        int(k) for k in density_maps.keys()
        if int(k) not in known_factions
    ])
    base_ch = 1 + len(enemy_factions)
    for i, sf in enumerate(sub_factions):
        ch_idx = min(base_ch + i, NUM_DENSITY_CHANNELS - 1)
        flat = np.array(density_maps[str(sf)], dtype=np.float32)
        if len(flat) == grid_size:
            if base_ch + i >= NUM_DENSITY_CHANNELS:
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
    max_entities = 10000.0

    own_count = faction_counts.get(str(brain_faction), 0)

    # Aggregate all enemy counts
    total_enemy_count = sum(
        faction_counts.get(str(ef), 0) for ef in enemy_factions
    )

    own_health = 0.0
    if str(brain_faction) in faction_avg:
        h = faction_avg[str(brain_faction)]
        own_health = h[0] if h else 0.0

    # Average health across all enemy factions
    enemy_health = 0.0
    enemy_health_count = 0
    for ef in enemy_factions:
        if str(ef) in faction_avg:
            h = faction_avg[str(ef)]
            if h:
                enemy_health += h[0]
                enemy_health_count += 1
    if enemy_health_count > 0:
        enemy_health /= enemy_health_count

    sub_faction_count = len(snapshot.get("active_sub_factions", []))
    active_zones_count = len(snapshot.get("active_zones", []))

    summary = np.array([
        min(own_count / max_entities, 1.0),
        min(total_enemy_count / max_entities, 1.0),
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
