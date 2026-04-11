"""State vectorization: JSON snapshot → numpy observation dict.

8-channel fixed 50×50 tensor + 12-dim summary vector.

Channel assignment:
  ch0: brain faction density
  ch1: unified enemy density (ALL enemies merged, LKP-processed under fog)
  ch2: reserved (zeroed) — future ally density for multiplayer
  ch3: sub-factions aggregated
  ch4: terrain (0=passable, 1=wall; padding=1.0)
  ch5: fog explored (0=unexplored, 1=explored; padding=1.0)
  ch6: fog visible (0=hidden, 1=visible; padding=1.0)
  ch7: threat density (Effective Combat Power)

For maps smaller than 50×50, the active arena is centered in the tensor.
Padding zones have: density=0, terrain=1(wall), fog=1(explored/visible).
"""

import numpy as np
from typing import Any

# Always 50×50 — CNN requires fixed shape
MAX_GRID = 50
NUM_CHANNELS = 8
SUMMARY_DIM = 12


def vectorize_snapshot(
    snapshot: dict[str, Any],
    brain_faction: int = 0,
    enemy_factions: list[int] | int = 1,
    active_grid_w: int = 50,
    active_grid_h: int = 50,
    cell_size: float = 20.0,
    fog_enabled: bool = False,
    lkp_buffer=None,
    max_entities: float = 10000.0,
    max_steps: int = 500,
    step_count: int = 0,
) -> dict[str, np.ndarray]:
    """Convert Rust StateSnapshot → numpy observation dict.
    
    Args:
        snapshot: Raw JSON from Rust.
        brain_faction: Faction ID of the RL agent.
        enemy_factions: Enemy faction ID(s).
        active_grid_w: Active map grid width (may be < 50).
        active_grid_h: Active map grid height (may be < 50).
        cell_size: World units per grid cell.
        fog_enabled: Whether fog of war is active this stage.
        lkp_buffer: LKPBuffer instance (required when fog_enabled=True).
        max_entities: Normalization constant for entity counts.
        max_steps: Max steps per episode (for progress normalization).
        step_count: Current step in episode.
    """
    if isinstance(enemy_factions, int):
        enemy_factions = [enemy_factions]
    enemy_factions = sorted(enemy_factions)
    
    # Padding offset for center-aligned active arena
    pad_x = (MAX_GRID - active_grid_w) // 2
    pad_y = (MAX_GRID - active_grid_h) // 2
    
    # Initialize all channels
    channels = [np.zeros((MAX_GRID, MAX_GRID), dtype=np.float32) for _ in range(NUM_CHANNELS)]
    
    density_maps = snapshot.get("density_maps", {})
    active_size = active_grid_h * active_grid_w
    
    def _place_density(flat_data: list, channel_idx: int):
        """Place active-sized density data into center-padded channel."""
        if not flat_data or len(flat_data) != active_size:
            return
        arr = np.array(flat_data, dtype=np.float32).reshape(active_grid_h, active_grid_w)
        channels[channel_idx][pad_y:pad_y+active_grid_h, pad_x:pad_x+active_grid_w] = arr
    
    # ── ch0: Brain density ──────────────────────────────────
    key = str(brain_faction)
    if key in density_maps:
        _place_density(density_maps[key], 0)
    
    # ── ch5: Fog explored, ch6: Fog visible ─────────────────
    # Default: fully explored/visible (no fog) — padding also 1.0
    channels[5].fill(1.0)
    channels[6].fill(1.0)
    
    if fog_enabled:
        fog_explored_raw = snapshot.get("fog_explored", [])
        fog_visible_raw = snapshot.get("fog_visible", [])
        
        if fog_explored_raw and len(fog_explored_raw) == active_size:
            explored = np.array(fog_explored_raw, dtype=np.float32).reshape(active_grid_h, active_grid_w)
            # Reset active area then place
            channels[5][pad_y:pad_y+active_grid_h, pad_x:pad_x+active_grid_w] = explored
        
        if fog_visible_raw and len(fog_visible_raw) == active_size:
            visible = np.array(fog_visible_raw, dtype=np.float32).reshape(active_grid_h, active_grid_w)
            channels[6][pad_y:pad_y+active_grid_h, pad_x:pad_x+active_grid_w] = visible
    
    # ── ch1: Unified enemy density (ALL enemies merged) ─────
    # Aggregate all enemy factions into a single heatmap so the CNN
    # learns to evaluate targets by spatial density, not faction ID.
    for ef in enemy_factions:
        key = str(ef)
        if key in density_maps:
            flat = density_maps[key]
            if flat and len(flat) == active_size:
                arr = np.array(flat, dtype=np.float32).reshape(active_grid_h, active_grid_w)
                channels[1][pad_y:pad_y+active_grid_h, pad_x:pad_x+active_grid_w] += arr
    
    if fog_enabled and lkp_buffer is not None:
        # LKP processes the unified enemy channel (single index 0)
        channels[1] = lkp_buffer.update(0, channels[1], channels[6])
    
    # ── ch2: Reserved (zeroed) — future ally density ────────
    # Intentionally empty. Will be used for teammate density
    # in multiplayer (2v2) fine-tuning phase.
    
    # ── ch3: Sub-factions aggregated ────────────────────────
    known = set([brain_faction] + enemy_factions)
    for sf_key in density_maps:
        sf_id = int(sf_key)
        if sf_id not in known:
            flat = density_maps[sf_key]
            if flat and len(flat) == active_size:
                arr = np.array(flat, dtype=np.float32).reshape(active_grid_h, active_grid_w)
                channels[3][pad_y:pad_y+active_grid_h, pad_x:pad_x+active_grid_w] += arr
    
    # ── ch4: Terrain ────────────────────────────────────────
    # Padding = 1.0 (wall) so CNN learns "edge of world"
    channels[4].fill(1.0)
    terrain_hard = snapshot.get("terrain_hard", [])
    if terrain_hard and len(terrain_hard) == active_size:
        raw = np.array(terrain_hard, dtype=np.float32)
        terrain = np.clip(raw / 65535.0, 0.0, 1.0).reshape(active_grid_h, active_grid_w)
        channels[4][pad_y:pad_y+active_grid_h, pad_x:pad_x+active_grid_w] = terrain
    
    # ── ch7: Effective Combat Power (ECP) density ──────────
    # Merge all enemy ecp_density_maps into a single channel.
    # CNN compares ch1 (raw count) vs ch7 (ECP mass) to distinguish
    # tough bait (high ECP, low count) from squishies (low ECP, high count).
    ecp_density_maps = snapshot.get("ecp_density_maps", {})
    for ef in enemy_factions:
        key = str(ef)
        if key in ecp_density_maps:
            flat = ecp_density_maps[key]
            if flat and len(flat) == active_size:
                arr = np.array(flat, dtype=np.float32).reshape(active_grid_h, active_grid_w)
                channels[7][pad_y:pad_y+active_grid_h, pad_x:pad_x+active_grid_w] += arr
                
    if fog_enabled and lkp_buffer is not None:
        # LKP tracks ECP on index 1
        channels[7] = lkp_buffer.update(1, channels[7], channels[6])
    
    # ── Summary (12 dims) ──────────────────────────────────
    summary_data = snapshot.get("summary", {})
    faction_counts = summary_data.get("faction_counts", {})
    faction_avg = summary_data.get("faction_avg_stats", {})
    
    own_count = faction_counts.get(str(brain_faction), 0)
    total_enemy = sum(faction_counts.get(str(ef), 0) for ef in enemy_factions)
    
    own_hp = 0.0
    if str(brain_faction) in faction_avg:
        h = faction_avg[str(brain_faction)]
        own_hp = h[0] if h else 0.0
    
    enemy_hp = 0.0
    ecount = 0
    for ef in enemy_factions:
        if str(ef) in faction_avg:
            h = faction_avg[str(ef)]
            if h:
                enemy_hp += h[0]
                ecount += 1
    if ecount > 0:
        enemy_hp /= ecount
    
    sub_factions = len(snapshot.get("active_sub_factions", []))
    active_zones = len(snapshot.get("active_zones", []))
    
    # Generalizable metrics: Total HPs
    own_total_hp = own_count * own_hp
    enemy_total_hp = sum(
        faction_counts.get(str(ef), 0) * (faction_avg[str(ef)][0] if faction_avg.get(str(ef)) else 0.0)
        for ef in enemy_factions
    )
    
    # Fog explored percentage (active area only)
    if fog_enabled:
        active_fog = channels[5][pad_y:pad_y+active_grid_h, pad_x:pad_x+active_grid_w]
        fog_explored_pct = float(active_fog.mean())
    else:
        fog_explored_pct = 1.0
    
    # Max possible total HP
    max_total_hp = max_entities * 100.0
    
    summary = np.array([
        min(own_count / max_entities, 1.0),            # 0
        min(total_enemy / max_entities, 1.0),          # 1
        own_hp / 100.0,                                # 2
        enemy_hp / 100.0,                              # 3
        min(sub_factions / 5.0, 1.0),                  # 4
        min(active_zones / 10.0, 1.0),                 # 5
        min(own_total_hp / max_total_hp, 1.0),         # 6
        min(enemy_total_hp / max_total_hp, 1.0),       # 7
        fog_explored_pct,                              # 8
        float(sub_factions > 0),                       # 9
        0.0,  # debuff_applied — set by env            # 10
        min(step_count / max(max_steps, 1), 1.0),      # 11
    ], dtype=np.float32)
    
    obs = {f"ch{i}": channels[i] for i in range(NUM_CHANNELS)}
    obs["summary"] = summary
    return obs
