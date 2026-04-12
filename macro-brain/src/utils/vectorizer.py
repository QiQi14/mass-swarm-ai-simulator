"""State vectorization: JSON snapshot → numpy observation dict.

8-channel fixed 50×50 tensor + 12-dim summary vector.

Channel Layout (v4.0):
  🟦 Force Picture:
    ch0: all friendly count density (brain + sub-factions merged)
    ch1: all enemy count density (ALL enemies merged, LKP-processed under fog)
    ch2: all friendly ECP density (brain + sub-factions merged)
    ch3: all enemy ECP density (ALL enemies merged, LKP-processed under fog)
  🟩 Environment:
    ch4: terrain cost (base + zone modifier effects, 0=pass, 1=wall; padding=1.0)
    ch5: fog awareness (merged 3-level: 0.0=unknown, 0.5=explored, 1.0=visible)
  🟨 Tactical (plumbed as zeros, activated when game mechanics exist):
    ch6: interactable terrain overlay (0.0 = no interactable)
    ch7: system objective signal (0.0 = no objective)

For maps smaller than 50×50, the active arena is centered in the tensor.
Padding zones have: density=0, terrain=1(wall), fog=1(explored/visible).
"""

import numpy as np
from typing import Any
import logging

logger = logging.getLogger(__name__)

# Always 50×50 — CNN requires fixed shape
MAX_GRID = 50
NUM_CHANNELS = 8
SUMMARY_DIM = 12

# One-time channel verification flag
_channel_verified = False


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
    max_hp: float = 100.0,
    active_sub_faction_ids: list[int] | None = None,
    active_objective_ping: tuple[float, float] | None = None,
    ping_intensity: float = 1.0,
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
        max_hp: Maximum entity HP for normalization (auto-computed from spawns).
        active_sub_faction_ids: List of active sub-faction IDs to merge into ch0/ch2.
    """
    if isinstance(enemy_factions, int):
        enemy_factions = [enemy_factions]
    enemy_factions = sorted(enemy_factions)
    
    if active_sub_faction_ids is None:
        active_sub_faction_ids = []
    
    # Padding offset for center-aligned active arena
    pad_x = (MAX_GRID - active_grid_w) // 2
    pad_y = (MAX_GRID - active_grid_h) // 2
    
    # Initialize all channels
    channels = [np.zeros((MAX_GRID, MAX_GRID), dtype=np.float32) for _ in range(NUM_CHANNELS)]
    
    density_maps = snapshot.get("density_maps", {})
    ecp_density_maps = snapshot.get("ecp_density_maps", {})
    active_size = active_grid_h * active_grid_w
    
    def _place_density(flat_data: list, channel_idx: int, accumulate: bool = False):
        """Place active-sized density data into center-padded channel."""
        if not flat_data or len(flat_data) != active_size:
            return
        arr = np.array(flat_data, dtype=np.float32).reshape(active_grid_h, active_grid_w)
        if accumulate:
            channels[channel_idx][pad_y:pad_y+active_grid_h, pad_x:pad_x+active_grid_w] += arr
        else:
            channels[channel_idx][pad_y:pad_y+active_grid_h, pad_x:pad_x+active_grid_w] = arr
    
    # ── ch0: All friendly count density (brain + sub-factions) ────
    key = str(brain_faction)
    if key in density_maps:
        _place_density(density_maps[key], 0)
    # Merge sub-faction density into ch0 ("all friendly")
    for sf_id in active_sub_faction_ids:
        sf_key = str(sf_id)
        if sf_key in density_maps:
            _place_density(density_maps[sf_key], 0, accumulate=True)
    
    # ── ch1: All enemy count density (ALL enemies merged) ─────────
    for ef in enemy_factions:
        key = str(ef)
        if key in density_maps:
            _place_density(density_maps[key], 1, accumulate=True)
    
    # ── ch2: All friendly ECP density (brain + sub-factions) ──────
    key = str(brain_faction)
    if key in ecp_density_maps:
        _place_density(ecp_density_maps[key], 2)
    # Merge sub-faction ECP into ch2 ("all friendly ECP")
    for sf_id in active_sub_faction_ids:
        sf_key = str(sf_id)
        if sf_key in ecp_density_maps:
            _place_density(ecp_density_maps[sf_key], 2, accumulate=True)
    
    # ── ch3: All enemy ECP density (ALL enemies merged) ───────────
    for ef in enemy_factions:
        key = str(ef)
        if key in ecp_density_maps:
            _place_density(ecp_density_maps[key], 3, accumulate=True)
    
    # ── ch4: Terrain cost ──────────────────────────────────────────
    # Padding = 1.0 (wall) so CNN learns "edge of world"
    channels[4].fill(1.0)
    terrain_hard = snapshot.get("terrain_hard", [])
    if terrain_hard and len(terrain_hard) == active_size:
        raw = np.array(terrain_hard, dtype=np.float32)
        terrain = np.clip(raw / 65535.0, 0.0, 1.0).reshape(active_grid_h, active_grid_w)
        channels[4][pad_y:pad_y+active_grid_h, pad_x:pad_x+active_grid_w] = terrain
    
    # ── ch5: Fog awareness (merged 3-level) ────────────────────────
    # Default: fully visible (no fog) — padding also 1.0
    channels[5].fill(1.0)
    
    if fog_enabled:
        fog_explored_raw = snapshot.get("fog_explored", [])
        fog_visible_raw = snapshot.get("fog_visible", [])
        
        if fog_explored_raw and len(fog_explored_raw) == active_size:
            explored = np.array(fog_explored_raw, dtype=np.float32).reshape(active_grid_h, active_grid_w)
            if fog_visible_raw and len(fog_visible_raw) == active_size:
                visible = np.array(fog_visible_raw, dtype=np.float32).reshape(active_grid_h, active_grid_w)
            else:
                visible = np.zeros((active_grid_h, active_grid_w), dtype=np.float32)
            
            # 3-level merge: 0.0 = unknown, 0.5 = explored but hidden, 1.0 = visible
            merged_fog = np.where(visible > 0.5, 1.0, np.where(explored > 0.5, 0.5, 0.0))
            channels[5][pad_y:pad_y+active_grid_h, pad_x:pad_x+active_grid_w] = merged_fog.astype(np.float32)
    
    # Keep raw visible mask for LKP processing (binary)
    if fog_enabled:
        visible_mask = channels[5].copy()
        # For LKP: visible = cells with value 1.0 in merged fog
        visible_mask = (visible_mask > 0.9).astype(np.float32)
    else:
        visible_mask = np.ones((MAX_GRID, MAX_GRID), dtype=np.float32)
    
    # Apply LKP (Last Known Position) for enemy channels under fog
    if fog_enabled and lkp_buffer is not None:
        channels[1] = lkp_buffer.update(0, channels[1], visible_mask)
        channels[3] = lkp_buffer.update(1, channels[3], visible_mask)
    
    # ── ch6: Interactable terrain overlay (plumbed, zeros) ─────────
    # All zeros — activated when destructible wall mechanics exist.
    
    # ── ch7: System objective signal (plumbed, zeros) ──────────────
    if active_objective_ping is not None:
        px, py = active_objective_ping
        grid_x = int(px / cell_size) + pad_x
        grid_y = int(py / cell_size) + pad_y
        
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                gx, gy = grid_x + dx, grid_y + dy
                if 0 <= gx < MAX_GRID and 0 <= gy < MAX_GRID:
                    dist = (dx**2 + dy**2)**0.5
                    val = max(0.0, ping_intensity - dist / 3.0)
                    channels[7][gy, gx] = max(channels[7][gy, gx], val)
    
    # ── Summary (12 dims) ──────────────────────────────────────────
    summary_data = snapshot.get("summary", {})
    faction_counts = summary_data.get("faction_counts", {})
    faction_avg = summary_data.get("faction_avg_stats", {})
    
    own_count = faction_counts.get(str(brain_faction), 0)
    # Include sub-faction counts in "own" count
    for sf_id in active_sub_faction_ids:
        own_count += faction_counts.get(str(sf_id), 0)
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
    
    # Total HP (profile-driven normalization)
    max_total_hp = max_entities * max_hp
    own_total_hp = own_count * own_hp
    enemy_total_hp = sum(
        faction_counts.get(str(ef), 0) * (faction_avg[str(ef)][0] if faction_avg.get(str(ef)) else 0.0)
        for ef in enemy_factions
    )
    
    # Fog explored percentage (active area only)
    if fog_enabled:
        active_fog = channels[5][pad_y:pad_y+active_grid_h, pad_x:pad_x+active_grid_w]
        # Explored = any non-zero value (0.5 or 1.0)
        fog_explored_pct = float((active_fog > 0.3).mean())
    else:
        fog_explored_pct = 1.0
    
    # Force ratio: own / (own + enemy), avoids division by zero
    total_units = own_count + total_enemy
    force_ratio = own_count / total_units if total_units > 0 else 0.5
    
    # Intervention tracker
    intervention_active = 1.0 if snapshot.get("intervention_active", False) else 0.0
    
    summary = np.array([
        min(own_count / max_entities, 1.0),            # 0: own alive count
        min(total_enemy / max_entities, 1.0),          # 1: enemy alive count
        min(own_hp / max_hp, 1.0),                     # 2: own avg HP (profile-driven)
        min(enemy_hp / max_hp, 1.0),                   # 3: enemy avg HP (profile-driven)
        min(sub_factions / 5.0, 1.0),                  # 4: sub-faction count
        min(own_total_hp / max(max_total_hp, 1), 1.0), # 5: own total HP
        min(enemy_total_hp / max(max_total_hp, 1), 1.0),  # 6: enemy total HP
        min(step_count / max(max_steps, 1), 1.0),      # 7: time elapsed
        fog_explored_pct,                              # 8: fog explored %
        float(sub_factions > 0),                       # 9: has sub-factions
        intervention_active,                           # 10: intervention active
        force_ratio,                                   # 11: force ratio
    ], dtype=np.float32)

    # ── One-time channel verification (first call only) ────────────
    global _channel_verified
    if not _channel_verified and len(enemy_factions) >= 2:
        _channel_verified = True
        ch0_sum = channels[0].sum()
        ch1_sum = channels[1].sum()
        ch2_sum = channels[2].sum()
        ch3_sum = channels[3].sum()
        
        # Dump raw snapshot data for pipeline debugging
        dm_keys = list(density_maps.keys())
        ecp_keys = list(ecp_density_maps.keys())
        dm_detail = {k: f"len={len(v)}, sum={sum(v):.4f}" for k, v in density_maps.items()}
        ecp_detail = {k: f"len={len(v)}, sum={sum(v):.4f}" for k, v in ecp_density_maps.items()}
        
        logger.info(
            "🔬 Channel Verification (first episode):\n"
            f"   ch0 (friendly count): sum={ch0_sum:.4f}\n"
            f"   ch1 (enemy count):    sum={ch1_sum:.4f}\n"
            f"   ch2 (friendly ECP):   sum={ch2_sum:.4f}\n"
            f"   ch3 (enemy ECP):      sum={ch3_sum:.4f}\n"
            f"   summary[0:4]:         {summary[:4]}\n"
            f"   brain_faction={brain_faction}, enemy_factions={enemy_factions}\n"
            f"   density_maps keys:     {dm_keys}\n"
            f"   density_maps detail:   {dm_detail}\n"
            f"   ecp_density_maps keys: {ecp_keys}\n"
            f"   ecp_density_maps detail: {ecp_detail}\n"
            f"   active_grid: {active_grid_w}x{active_grid_h}, active_size={active_size}\n"
            f"   pad: ({pad_x}, {pad_y})"
        )
        if ch2_sum < 0.001:
            logger.error(
                "❌ CRITICAL: ch2 (friendly ECP) is ALL ZEROS!\n"
                "   The CNN cannot see own combat power.\n"
                "   Check Rust ecp_density_maps pipeline for brain faction."
            )
        if ch3_sum < 0.001:
            logger.error(
                "❌ CRITICAL: ch3 (enemy ECP) is ALL ZEROS!\n"
                "   The CNN cannot see threat data.\n"
                "   Training will produce coin-flip target selection.\n"
                "   Check Rust ecp_density_maps pipeline."
            )
        if ch1_sum < 0.001 and not fog_enabled:
            logger.error(
                "❌ CRITICAL: ch1 (enemy count) is ALL ZEROS without fog!\n"
                "   The CNN cannot see enemies at all."
            )
    
    obs = {f"ch{i}": channels[i] for i in range(NUM_CHANNELS)}
    obs["summary"] = summary
    return obs
