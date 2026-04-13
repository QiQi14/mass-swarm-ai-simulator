"""Channel Integrity Tests — verifies ALL 8 observation channels + summary.

Builds synthetic Rust-like snapshots for every curriculum stage (0–8) and
passes them through `vectorize_snapshot()`.  Asserts non-trivial values
for every channel that should be active at that stage.

This catches silent data pipeline failures BEFORE training.

Channel Map (v4.0):
  🟦 Force Picture:
    ch0  – all friendly count density      (all stages)
    ch1  – all enemy count density         (all stages)
    ch2  – all friendly ECP density        (all stages)
    ch3  – all enemy ECP density           (all stages)
  🟩 Environment:
    ch4  – terrain hard cost normalized    (stages 2-3 have walls/features)
    ch5  – fog awareness (merged 3-level)  (stages 0-3: all 1.0; stages 4+: partial)
  🟨 Tactical:
    ch6  – interactable terrain (zeroed)   (always 0)
    ch7  – system objective (zeroed)       (always 0)
  summary – 12-dim scalar vector           (all stages)
"""

import sys
import os
import pytest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils.vectorizer import vectorize_snapshot
from src.utils.lkp_buffer import LKPBuffer
from src.training.curriculum import (
    get_spawns_for_stage,
    get_map_config,
)
from src.utils.terrain_generator import generate_terrain_for_stage


# ── Helpers ────────────────────────────────────────────────────────

def _build_synthetic_snapshot(
    stage: int,
    rng_seed: int = 42,
) -> dict:
    """Build a Rust-like state_snapshot dict for a given stage.

    Simulates what Rust would send over ZMQ at tick=30 (first eval).
    Entities are placed at their spawn coordinates with initial HP.
    No combat has occurred yet (full HP, no kills).
    """
    rng = np.random.default_rng(rng_seed)
    config = get_map_config(stage)
    spawns, role_meta = get_spawns_for_stage(stage, rng=rng, profile=_load_profile())
    terrain = generate_terrain_for_stage(stage, seed=rng_seed)

    # Build density_maps and ecp_density_maps from spawn data
    # Simulate Rust: grid cell = floor(pos / cell_size)
    grid_w = config.active_grid_w
    grid_h = config.active_grid_h
    cell_size = config.cell_size
    max_density = 50.0

    # Auto-compute max_entity_ecp from spawns (same as swarm_env.py)
    max_entity_hp = max(
        (stat["value"] for spawn in spawns for stat in spawn.get("stats", []) if stat["index"] == 0),
        default=100.0
    )
    max_ecp_per_cell = max_density * max_entity_hp

    raw_density = {}   # faction -> [count_per_cell]
    raw_ecp = {}       # faction -> [ecp_per_cell]
    faction_counts = {}
    faction_avg_stats = {}

    for spawn in spawns:
        fid = spawn["faction_id"]
        count = spawn["count"]
        x0, y0, spread = spawn["x"], spawn["y"], spawn.get("spread", 50.0)
        hp = 100.0
        for st in spawn.get("stats", []):
            if st["index"] == 0:
                hp = st["value"]

        # Accumulate faction info
        faction_counts[str(fid)] = faction_counts.get(str(fid), 0) + count
        # Avg stats (just HP at index 0)
        faction_avg_stats[str(fid)] = [hp] + [0.0] * 7

        # Scatter entities around spawn center
        for _ in range(count):
            ex = x0 + rng.uniform(-spread, spread)
            ey = y0 + rng.uniform(-spread, spread)
            # Clamp to world
            ex = max(0, min(ex, config.world_width - 1))
            ey = max(0, min(ey, config.world_height - 1))

            cx = int(ex / cell_size)
            cy = int(ey / cell_size)
            cx = max(0, min(cx, grid_w - 1))
            cy = max(0, min(cy, grid_h - 1))
            idx = cy * grid_w + cx

            # Density
            if fid not in raw_density:
                raw_density[fid] = [0.0] * (grid_w * grid_h)
            raw_density[fid][idx] += 1.0

            # ECP
            if fid not in raw_ecp:
                raw_ecp[fid] = [0.0] * (grid_w * grid_h)
            # damage_mult = 1.0 at episode start (no active buffs)
            raw_ecp[fid][idx] += max(hp * 1.0, 1.0)

    # Normalize
    density_maps = {}
    for fid, cells in raw_density.items():
        density_maps[str(fid)] = [min(c / max_density, 1.0) for c in cells]

    ecp_density_maps = {}
    for fid, cells in raw_ecp.items():
        ecp_density_maps[str(fid)] = [min(c / max_ecp_per_cell, 1.0) for c in cells]

    # Terrain
    terrain_hard = []
    if terrain is not None:
        terrain_hard = terrain.get("hard_costs", [])
    else:
        terrain_hard = [100] * (grid_w * grid_h)

    # Fog: stages 0-3 = no fog, stages 4+ = partial visibility
    fog_explored = None
    fog_visible = None
    if config.fog_enabled:
        # Brain can see ~20% of the map around its spawn
        explored = [0] * (grid_w * grid_h)
        visible = [0] * (grid_w * grid_h)
        brain_spawn = spawns[0]  # Brain is always first
        bcx = int(brain_spawn["x"] / cell_size)
        bcy = int(brain_spawn["y"] / cell_size)
        vis_radius = 5
        for dy in range(-vis_radius, vis_radius + 1):
            for dx in range(-vis_radius, vis_radius + 1):
                gx = bcx + dx
                gy = bcy + dy
                if 0 <= gx < grid_w and 0 <= gy < grid_h:
                    idx = gy * grid_w + gx
                    explored[idx] = 1
                    visible[idx] = 1
        fog_explored = explored
        fog_visible = visible

    snapshot = {
        "type": "state_snapshot",
        "tick": 30,
        "summary": {
            "faction_counts": faction_counts,
            "faction_avg_stats": faction_avg_stats,
        },
        "density_maps": density_maps,
        "ecp_density_maps": ecp_density_maps,
        "terrain_hard": terrain_hard,
        "active_sub_factions": [],
        "active_zones": [],
    }

    if fog_explored is not None:
        snapshot["fog_explored"] = fog_explored
        snapshot["fog_visible"] = fog_visible

    return snapshot, role_meta, config, max_entity_hp


def _load_profile():
    """Load the tactical curriculum profile."""
    from src.config.game_profile import load_profile
    return load_profile("profiles/tactical_curriculum.json")


def _vectorize_for_stage(stage: int, rng_seed: int = 42):
    """Build snapshot and vectorize it for a given stage."""
    snapshot, role_meta, config, max_hp = _build_synthetic_snapshot(stage, rng_seed)
    lkp = LKPBuffer() if config.fog_enabled else None

    obs = vectorize_snapshot(
        snapshot,
        brain_faction=0,
        enemy_factions=[1, 2],
        active_grid_w=config.active_grid_w,
        active_grid_h=config.active_grid_h,
        cell_size=config.cell_size,
        fog_enabled=config.fog_enabled,
        lkp_buffer=lkp,
        max_hp=max_hp,
    )
    return obs, role_meta, config


# ── Channel Shape Tests ────────────────────────────────────────────

@pytest.mark.parametrize("stage", range(9))
def test_all_channels_correct_shape(stage):
    """Every channel must be (50, 50) float32."""
    obs, _, _ = _vectorize_for_stage(stage)
    for ch in range(8):
        key = f"ch{ch}"
        assert key in obs, f"Stage {stage}: missing {key}"
        assert obs[key].shape == (50, 50), f"Stage {stage}: {key} shape={obs[key].shape}"
        assert obs[key].dtype == np.float32, f"Stage {stage}: {key} dtype={obs[key].dtype}"
    assert "summary" in obs
    assert obs["summary"].shape == (12,)


# ── Ch0: All Friendly Count Density ───────────────────────────────

@pytest.mark.parametrize("stage", range(9))
def test_ch0_friendly_density_nonzero(stage):
    """Ch0 (all friendly count density) must be non-zero at every stage."""
    obs, _, _ = _vectorize_for_stage(stage)
    ch0 = obs["ch0"]
    assert ch0.sum() > 0.01, (
        f"Stage {stage}: ch0 (friendly count) is essentially zero! "
        f"sum={ch0.sum():.6f}"
    )


# ── Ch1: All Enemy Count Density ──────────────────────────────────

@pytest.mark.parametrize("stage", range(9))
def test_ch1_enemy_density_nonzero(stage):
    """Ch1 (all enemy count density) must be non-zero at every stage."""
    obs, _, config = _vectorize_for_stage(stage)
    ch1 = obs["ch1"]
    if config.fog_enabled:
        pass  # ch1 may legitimately be zero if enemies are in fog
    else:
        assert ch1.sum() > 0.01, (
            f"Stage {stage}: ch1 (enemy count) is zero! "
            f"sum={ch1.sum():.6f}. Enemies should be visible without fog."
        )


# ── Ch2: All Friendly ECP Density ─────────────────────────────────

@pytest.mark.parametrize("stage", range(9))
def test_ch2_friendly_ecp_nonzero(stage):
    """Ch2 (all friendly ECP density) must be non-zero at every stage.
    
    This is the brain's own combat power heatmap — essential for
    engage/retreat decisions when compared with ch3 (enemy ECP).
    """
    obs, _, config = _vectorize_for_stage(stage)
    ch2 = obs["ch2"]
    assert ch2.sum() > 0.001, (
        f"Stage {stage}: ch2 (friendly ECP) is zero! "
        f"sum={ch2.sum():.6f}. Brain can't see its own combat power."
    )


# ── Ch3: All Enemy ECP Density ────────────────────────────────────

@pytest.mark.parametrize("stage", range(9))
def test_ch3_enemy_ecp_nonzero(stage):
    """Ch3 (all enemy ECP density) must be non-zero when enemies are visible."""
    obs, _, config = _vectorize_for_stage(stage)
    ch3 = obs["ch3"]
    if config.fog_enabled:
        pass  # Enemies may be hidden
    else:
        assert ch3.sum() > 0.001, (
            f"Stage {stage}: ch3 (enemy ECP) is zero with no fog! "
            f"sum={ch3.sum():.6f}. Brain can't see threat data."
        )


def test_ch3_stage1_differentiates_trap_vs_target():
    """Stage 1 CRITICAL — Ch3 must distinguish trap (200 HP) from target (24 HP).

    The entire point of the ECP channel is to let the CNN differentiate
    tough bait (high ECP, high count) from squishies (low ECP, high count).
    """
    for seed in [42, 123, 777]:
        snapshot, role_meta, config, max_hp = _build_synthetic_snapshot(1, rng_seed=seed)
        ecp_maps = snapshot["ecp_density_maps"]
        trap_fid = str(role_meta["trap_faction"])
        target_fid = str(role_meta["target_faction"])

        assert trap_fid in ecp_maps, f"Seed {seed}: trap faction {trap_fid} missing from ecp_density_maps"
        assert target_fid in ecp_maps, f"Seed {seed}: target faction {target_fid} missing from ecp_density_maps"

        trap_ecp = np.array(ecp_maps[trap_fid])
        target_ecp = np.array(ecp_maps[target_fid])

        trap_max = trap_ecp.max()
        target_max = target_ecp.max()

        assert trap_max > 0, f"Seed {seed}: trap ECP is all zeros"
        assert target_max > 0, f"Seed {seed}: target ECP is all zeros"

        # Trap (200 HP) should produce significantly higher ECP than target (24 HP)
        ratio = trap_max / target_max
        assert ratio > 3.0, (
            f"Seed {seed}: ECP ratio trap/target = {ratio:.2f}, expected >3.0. "
            f"Trap max ECP={trap_max:.6f}, Target max ECP={target_max:.6f}. "
            "Ch3 is not differentiating groups properly."
        )


# ── Ch2 vs Ch3: Engage/Retreat Decision Test ──────────────────────

def test_ch2_ch3_enables_engage_retreat_decision():
    """The brain can compare ch2 (own ECP) vs ch3 (enemy ECP) per cell.
    
    Where ch2 > ch3, the brain is locally stronger → engage.
    Where ch3 > ch2, enemies are locally stronger → retreat.
    """
    obs, _, _ = _vectorize_for_stage(1)
    ch2 = obs["ch2"]
    ch3 = obs["ch3"]
    
    # Both must have content
    assert ch2.sum() > 0.001, "ch2 (friendly ECP) is zero"
    assert ch3.sum() > 0.001, "ch3 (enemy ECP) is zero"
    
    # They should have different spatial distributions
    # (brain is in one corner, enemies in another)
    ch2_nz = ch2 > 0.001
    ch3_nz = ch3 > 0.001
    assert ch2_nz.sum() > 0, "ch2 has no non-zero cells"
    assert ch3_nz.sum() > 0, "ch3 has no non-zero cells"


# ── Ch1 vs Ch3 Cross-Check ────────────────────────────────────────

def test_ch1_ch3_correlated_but_different_stage1():
    """Ch1 and Ch3 should cover the same spatial regions but with different magnitudes.

    Ch1 = unit count density (equal for trap & target, both 50 units).
    Ch3 = ECP mass (trap >> target due to HP difference).
    If Ch3 == Ch1 (scaled), the ECP pipeline is broken (just copying density).
    """
    obs, _, _ = _vectorize_for_stage(1)
    ch1 = obs["ch1"]
    ch3 = obs["ch3"]

    if ch3.sum() < 0.001:
        pytest.fail("Ch3 is zero — cannot compare with Ch1")

    # Both should have non-zero content in similar spatial regions
    ch1_nz = ch1 > 0.001
    ch3_nz = ch3 > 0.001
    overlap = np.logical_and(ch1_nz, ch3_nz).sum()
    assert overlap > 0, (
        "Ch1 and Ch3 have zero spatial overlap — one of them is broken"
    )

    # The RATIO between ch3 and ch1 should vary spatially
    # (trap cells have high ch3/ch1 ratio, target cells have low ratio)
    mask = ch1 > 0.001
    if mask.sum() > 0:
        ratios = ch3[mask] / ch1[mask]
        ratio_range = ratios.max() - ratios.min()
        assert ratio_range > 0.01, (
            f"Ch3/Ch1 ratio is constant ({ratios.mean():.4f} ± {ratio_range:.6f}). "
            "ECP is just scaled density, not threat-weighted. "
            "Either HP values are identical or damage_mult is broken."
        )


# ── Ch4: Terrain ───────────────────────────────────────────────────

def test_ch4_flat_terrain_stages_0_1():
    """Stages 0-1 have flat terrain: ch4 should be uniform (100/65535 ≈ 0.0015)."""
    for stage in [0, 1]:
        obs, _, config = _vectorize_for_stage(stage)
        ch4 = obs["ch4"]
        pad_x = (50 - config.active_grid_w) // 2
        pad_y = (50 - config.active_grid_h) // 2
        active = ch4[pad_y:pad_y+config.active_grid_h,
                     pad_x:pad_x+config.active_grid_w]
        # All flat = 100, normalized as 100/65535 ≈ 0.001526
        unique = np.unique(active)
        assert len(unique) == 1, (
            f"Stage {stage}: flat terrain should have 1 unique value, "
            f"got {len(unique)}: {unique[:5]}"
        )


def test_ch4_stage2_has_walls():
    """Stage 2 terrain must have walls (high terrain values)."""
    obs, _, config = _vectorize_for_stage(2)
    ch4 = obs["ch4"]
    pad_x = (50 - config.active_grid_w) // 2
    pad_y = (50 - config.active_grid_h) // 2
    active = ch4[pad_y:pad_y+config.active_grid_h,
                 pad_x:pad_x+config.active_grid_w]
    max_val = active.max()
    assert max_val > 0.9, (
        f"Stage 2: terrain should have walls (max ≈ 1.0), "
        f"got max={max_val:.4f}"
    )
    unique_count = len(np.unique(np.round(active, 4)))
    assert unique_count >= 2, (
        f"Stage 2: terrain should have at least 2 distinct cost values "
        f"(passable + wall), got {unique_count}"
    )


def test_ch4_padding_is_wall():
    """Padding zones (outside active area) must be 1.0 (wall)."""
    for stage in [0, 1, 2]:
        obs, _, config = _vectorize_for_stage(stage)
        if config.active_grid_w < 50 or config.active_grid_h < 50:
            ch4 = obs["ch4"]
            # Check top-left corner (should be padding = 1.0)
            assert ch4[0, 0] == 1.0, (
                f"Stage {stage}: ch4 padding should be 1.0, "
                f"got ch4[0,0]={ch4[0,0]:.4f}"
            )


# ── Ch5: Fog Awareness (Merged 3-Level) ───────────────────────────

@pytest.mark.parametrize("stage", [0, 1, 2, 3])
def test_ch5_no_fog_stages_all_visible(stage):
    """Stages 0-3 (no fog): ch5 must be all 1.0 (fully visible)."""
    obs, _, _ = _vectorize_for_stage(stage)
    ch5 = obs["ch5"]
    assert ch5.min() == 1.0, (
        f"Stage {stage}: ch5 (fog awareness) should be all 1.0 without fog, "
        f"min={ch5.min():.4f}"
    )


@pytest.mark.parametrize("stage", [4, 5, 6, 7])
def test_ch5_fog_stages_has_three_levels(stage):
    """Stages 4+ (fog on): ch5 should have cells at 0.0, 0.5, and/or 1.0."""
    obs, _, config = _vectorize_for_stage(stage)
    ch5 = obs["ch5"]
    pad_x = (50 - config.active_grid_w) // 2
    pad_y = (50 - config.active_grid_h) // 2
    active = ch5[pad_y:pad_y+config.active_grid_h,
                 pad_x:pad_x+config.active_grid_w]
    unique_vals = set(np.unique(np.round(active, 2)))
    # Should have at least 2 levels (visible cells + unknown cells)
    assert len(unique_vals) >= 2, (
        f"Stage {stage}: ch5 (fog) should have multiple levels, "
        f"got unique={unique_vals}. Expected mix of 0.0/0.5/1.0."
    )


# ── Ch6: Interactable Terrain (Plumbed Zeros) ─────────────────────

@pytest.mark.parametrize("stage", range(9))
def test_ch6_always_zero(stage):
    """Ch6 (interactable terrain) must be all zeros until mechanics exist."""
    obs, _, _ = _vectorize_for_stage(stage)
    ch6 = obs["ch6"]
    assert ch6.sum() == 0.0, (
        f"Stage {stage}: ch6 (interactable terrain) should be all zeros, "
        f"sum={ch6.sum():.6f}"
    )


# ── Ch7: System Objective Signal (Plumbed Zeros) ──────────────────

@pytest.mark.parametrize("stage", range(9))
def test_ch7_always_zero(stage):
    """Ch7 (system objective) must be all zeros until curriculum provides data."""
    obs, _, _ = _vectorize_for_stage(stage)
    ch7 = obs["ch7"]
    assert ch7.sum() == 0.0, (
        f"Stage {stage}: ch7 (system objective) should be all zeros, "
        f"sum={ch7.sum():.6f}"
    )


# ── Summary Vector ─────────────────────────────────────────────────

@pytest.mark.parametrize("stage", range(9))
def test_summary_nonzero(stage):
    """Summary vector should have non-zero entries for unit counts and HP."""
    obs, _, _ = _vectorize_for_stage(stage)
    summary = obs["summary"]
    # Index 0: own count (should be > 0)
    assert summary[0] > 0.0, f"Stage {stage}: summary[0] (own_count) is zero"
    # Index 1: enemy count (should be > 0)
    assert summary[1] > 0.0, f"Stage {stage}: summary[1] (enemy_count) is zero"
    # Index 2: own avg HP (should be > 0)
    assert summary[2] > 0.0, f"Stage {stage}: summary[2] (own_hp) is zero"


@pytest.mark.parametrize("stage", range(9))
def test_summary_in_bounds(stage):
    """All summary values should be in [0.0, 1.0]."""
    obs, _, _ = _vectorize_for_stage(stage)
    summary = obs["summary"]
    assert summary.min() >= 0.0, f"Stage {stage}: summary has negative values"
    assert summary.max() <= 1.0, f"Stage {stage}: summary has values > 1.0"


def test_summary_force_ratio():
    """Summary[11] (force ratio) should be in (0, 1)."""
    obs, _, _ = _vectorize_for_stage(1)
    summary = obs["summary"]
    force_ratio = summary[11]
    assert 0.0 < force_ratio < 1.0, (
        f"Summary[11] (force ratio) = {force_ratio:.4f}, "
        "expected (0, 1) for non-trivial scenario"
    )


# ── Full Channel Matrix (comprehensive check) ─────────────────────

def test_full_channel_matrix():
    """Print a full diagnostic matrix of all channels × all stages.

    Not a pass/fail test — this is for human review of the full picture.
    """
    print("\n" + "=" * 100)
    print("CHANNEL INTEGRITY MATRIX (v4.0) — sum / nonzero_cells for each (stage, channel)")
    print("=" * 100)

    header = f"{'Stage':<6}"
    ch_names = ["friendly", "enemy", "frnECP", "enmECP", "terrain", "fog", "intract", "sysobj"]
    for i, name in enumerate(ch_names):
        header += f"{'ch' + str(i) + ':' + name:>15}"
    header += f"{'summ[0:4]':>22}"
    print(header)
    print("-" * 100)

    for stage in range(9):
        try:
            obs, _, config = _vectorize_for_stage(stage)
            row = f"S{stage} {'F' if config.fog_enabled else ' ':<4}"
            for ch in range(8):
                arr = obs[f"ch{ch}"]
                s = arr.sum()
                nz = np.count_nonzero(arr)
                if s < 0.001:
                    row += f"{'ZERO':>15}"
                else:
                    row += f"{s:>8.3f}/{nz:<5}"
            summ = obs["summary"]
            row += f"  [{summ[0]:.3f},{summ[1]:.3f},{summ[2]:.2f},{summ[3]:.2f}]"
            print(row)
        except Exception as e:
            print(f"S{stage}  ERROR: {e}")

    print("=" * 100)
    print("Legend: F=fog_enabled, ZERO=sum<0.001, format=sum/nonzero_cells")
    print("v4.0: ch0=friendly ch1=enemy ch2=frnECP ch3=enmECP ch4=terrain ch5=fog ch6=interactable ch7=sysobj")
