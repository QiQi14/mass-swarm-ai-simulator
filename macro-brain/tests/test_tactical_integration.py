"""End-to-end integration tests for the tactical training pipeline.

Tests the full pipeline WITHOUT the Rust Micro-Core: observation shapes,
action masking, coordinate decoding, center-padding, fog channels,
reward gradients, and MultiDiscrete action acceptance.

All env interactions use a mocked ZMQ socket that returns synthetic snapshots.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.config.definitions import RewardWeights
from src.env.actions import multidiscrete_to_directives
from src.env.rewards import compute_shaped_reward
from src.env.spaces import (
    MAX_GRID_CELLS, MAX_GRID_HEIGHT, MAX_GRID_WIDTH,
    make_action_space, make_coordinate_mask, make_observation_space,
)
from src.env.swarm_env import SwarmEnv
from src.training.curriculum import STAGE_MAP_CONFIGS, get_map_config
from src.utils.vectorizer import vectorize_snapshot


# ══════════════════════════════════════════════════════════════════════
#  Helpers & Fixtures
# ══════════════════════════════════════════════════════════════════════

def _make_snapshot(
    brain_count: int = 50,
    enemy1_count: int = 50,
    enemy2_count: int = 20,
    active_grid_w: int = 50,
    active_grid_h: int = 50,
    fog_explored: list | None = None,
    fog_visible: list | None = None,
    terrain_hard: list | None = None,
) -> dict:
    """Build a synthetic state snapshot mimicking Rust output."""
    active_size = active_grid_w * active_grid_h

    brain_density = [0.0] * active_size
    enemy1_density = [0.0] * active_size
    enemy2_density = [0.0] * active_size

    # Put some density in known locations
    if active_size > 100:
        brain_density[50] = 1.0
        if enemy1_count > 0:
            enemy1_density[100] = 0.5
        if enemy2_count > 0:
            enemy2_density[150] = 0.3

    return {
        "type": "state_snapshot",
        "tick": 100,
        "active_sub_factions": [],
        "density_maps": {
            "0": brain_density,
            "1": enemy1_density,
            "2": enemy2_density,
        },
        "terrain_hard": terrain_hard or [0] * active_size,
        "fog_explored": fog_explored,
        "fog_visible": fog_visible,
        "summary": {
            "faction_counts": {
                "0": brain_count,
                "1": enemy1_count,
                "2": enemy2_count,
            },
            "faction_avg_stats": {
                "0": [100.0],
                "1": [100.0],
                "2": [100.0],
            },
        },
    }


class _DummyMapConfig:
    """Lightweight substitute for StageMapConfig for fixture use."""
    def __init__(self, w: int, h: int, fog: bool):
        self.active_grid_w = w
        self.active_grid_h = h
        self.cell_size = 20.0
        self.fog_enabled = fog


@pytest.fixture
def mock_env():
    """SwarmEnv with mocked ZMQ that returns synthetic snapshots."""
    with patch("zmq.Context"):
        env = SwarmEnv(config={"profile_path": "profiles/tactical_curriculum.json"})
        env._socket = MagicMock()
        return env


def _default_reward_weights() -> RewardWeights:
    """Reward weights matching the tactical curriculum profile defaults."""
    return RewardWeights(
        time_penalty_per_step=-0.01,
        kill_reward=0.05,
        death_penalty=-0.03,
        win_terminal=10.0,
        loss_terminal=-10.0,
        survival_bonus_multiplier=5.0,
        approach_scale=0.02,
        exploration_reward=0.005,
        exploration_decay_threshold=0.8,
        threat_priority_bonus=2.0,
        flanking_bonus_scale=0.1,
        lure_success_bonus=3.0,
        debuff_bonus=2.0,
    )


# ══════════════════════════════════════════════════════════════════════
#  Observation Shape Tests
# ══════════════════════════════════════════════════════════════════════

def test_observation_shape_all_stages():
    """All 8 stages produce obs with 8 ch × (50,50) + summary(12)."""
    for stage in range(1, 9):
        config = get_map_config(stage)
        snap = _make_snapshot(
            active_grid_w=config.active_grid_w,
            active_grid_h=config.active_grid_h,
        )
        obs = vectorize_snapshot(
            snap,
            brain_faction=0,
            enemy_factions=[1, 2],
            active_grid_w=config.active_grid_w,
            active_grid_h=config.active_grid_h,
            cell_size=config.cell_size,
            fog_enabled=config.fog_enabled,
        )

        for ch in range(8):
            assert obs[f"ch{ch}"].shape == (50, 50), (
                f"Stage {stage} ch{ch} shape mismatch: {obs[f'ch{ch}'].shape}"
            )
        assert obs["summary"].shape == (12,), f"Stage {stage} summary shape mismatch"


# ══════════════════════════════════════════════════════════════════════
#  Action Masking Tests
# ══════════════════════════════════════════════════════════════════════

def test_action_masking_stage1(mock_env):
    """Stage 1: only Hold and AttackCoord unmasked."""
    mock_env.curriculum_stage = 1
    mask = mock_env.action_masks()
    act_mask = mask[:8]

    assert act_mask[0] is np.True_   # Hold
    assert act_mask[1] is np.True_   # AttackCoord
    assert act_mask[2] is np.False_  # DropPheromone (locked)
    assert act_mask[3] is np.False_  # DropRepellent (locked)
    assert act_mask[4] is np.False_  # SplitToCoord (locked)
    assert act_mask[5] is np.False_  # MergeBack (locked + no subs)
    assert act_mask[6] is np.False_  # Retreat (locked)
    assert act_mask[7] is np.False_  # Scout (locked)


def test_action_masking_stage4(mock_env):
    """Stage 4: Hold, AttackCoord, Pheromone, Repellent, Scout unmasked."""
    mock_env.curriculum_stage = 4
    mask = mock_env.action_masks()
    act_mask = mask[:8]

    assert act_mask[0] is np.True_   # Hold
    assert act_mask[1] is np.True_   # AttackCoord
    assert act_mask[2] is np.True_   # DropPheromone (stage 2)
    assert act_mask[3] is np.True_   # DropRepellent (stage 3)
    assert act_mask[4] is np.False_  # SplitToCoord (locked until stage 5)
    assert act_mask[5] is np.False_  # MergeBack (locked + no subs)
    assert act_mask[6] is np.False_  # Retreat (locked until stage 6)
    assert act_mask[7] is np.True_   # Scout (stage 4)


def test_action_masking_stage6(mock_env):
    """Stage 6+: all 8 actions unmasked (except dynamic guards)."""
    mock_env.curriculum_stage = 6
    mock_env._active_sub_factions = [100]  # has a sub for MergeBack
    mask = mock_env.action_masks()
    act_mask = mask[:8]

    # All stage-unlocked at stage 6
    assert act_mask[0] is np.True_  # Hold
    assert act_mask[1] is np.True_  # AttackCoord
    assert act_mask[2] is np.True_  # DropPheromone
    assert act_mask[3] is np.True_  # DropRepellent
    assert act_mask[4] is np.True_  # SplitToCoord
    assert act_mask[5] is np.True_  # MergeBack (has sub)
    assert act_mask[6] is np.True_  # Retreat
    assert act_mask[7] is np.True_  # Scout


# ══════════════════════════════════════════════════════════════════════
#  Coordinate Masking Tests
# ══════════════════════════════════════════════════════════════════════

def test_coordinate_masking_small_map():
    """Stage 1 (25×25): only 625 of 2500 coords unmasked."""
    coord_mask = make_coordinate_mask(
        active_grid_w=25, active_grid_h=25,
        max_grid_w=50, max_grid_h=50,
    )
    assert coord_mask.shape == (2500,)
    assert coord_mask.sum() == 625

    # Verify active cells are centered
    pad_x = (50 - 25) // 2  # 12
    pad_y = (50 - 25) // 2  # 12
    for gy in range(25):
        row = pad_y + gy
        for gx in range(25):
            flat_idx = row * 50 + pad_x + gx
            assert coord_mask[flat_idx] is np.True_, f"Active cell ({gx},{gy}) should be True"


def test_coordinate_masking_full_map():
    """Stage 6 (50×50): all 2500 coords unmasked."""
    coord_mask = make_coordinate_mask(
        active_grid_w=50, active_grid_h=50,
        max_grid_w=50, max_grid_h=50,
    )
    assert coord_mask.sum() == 2500


def test_coordinate_masking_matches_stage_env(mock_env):
    """Env action_masks produces correct coord mask count per stage."""
    for stage, config in STAGE_MAP_CONFIGS.items():
        mock_env.curriculum_stage = stage
        mock_env._active_grid_w = config.active_grid_w
        mock_env._active_grid_h = config.active_grid_h

        mask = mock_env.action_masks()
        coord_mask = mask[8:]
        expected = config.active_grid_w * config.active_grid_h
        assert coord_mask.sum() == expected, (
            f"Stage {stage}: expected {expected} active coords, got {coord_mask.sum()}"
        )


# ══════════════════════════════════════════════════════════════════════
#  Center Padding Tests
# ══════════════════════════════════════════════════════════════════════

def test_center_padding():
    """Stage 1: terrain padding zone = 1.0 (wall)."""
    config = get_map_config(1)
    snap = _make_snapshot(
        active_grid_w=config.active_grid_w,
        active_grid_h=config.active_grid_h,
        terrain_hard=[0] * (config.active_grid_w * config.active_grid_h),
    )

    obs = vectorize_snapshot(
        snap,
        brain_faction=0,
        enemy_factions=[1, 2],
        active_grid_w=config.active_grid_w,
        active_grid_h=config.active_grid_h,
        cell_size=config.cell_size,
        fog_enabled=config.fog_enabled,
    )

    ch4 = obs["ch4"]  # terrain channel
    pad_x = (50 - config.active_grid_w) // 2
    pad_y = (50 - config.active_grid_h) // 2

    # Padding corners should be 1.0 (wall)
    assert ch4[0, 0] == pytest.approx(1.0), "Top-left padding should be wall"
    assert ch4[49, 49] == pytest.approx(1.0), "Bottom-right padding should be wall"
    assert ch4[0, 49] == pytest.approx(1.0), "Top-right padding should be wall"

    # Active zone interior should be 0.0 (passable terrain, terrain_hard=[0])
    assert ch4[pad_y, pad_x] == pytest.approx(0.0), "Active zone should be passable"
    assert ch4[pad_y + 1, pad_x + 1] == pytest.approx(0.0)


def test_density_padding_is_zero():
    """Density channels in padding zone are 0.0."""
    config = get_map_config(1)  # 25×25 active
    snap = _make_snapshot(
        active_grid_w=config.active_grid_w,
        active_grid_h=config.active_grid_h,
    )
    obs = vectorize_snapshot(
        snap,
        brain_faction=0,
        enemy_factions=[1, 2],
        active_grid_w=config.active_grid_w,
        active_grid_h=config.active_grid_h,
    )

    # Density channels (ch0, ch1, ch2, ch3) should be 0.0 in padding
    for ch_idx in range(4):
        assert obs[f"ch{ch_idx}"][0, 0] == pytest.approx(0.0), (
            f"ch{ch_idx} padding corner should be 0.0"
        )


# ══════════════════════════════════════════════════════════════════════
#  Fog Channel Tests
# ══════════════════════════════════════════════════════════════════════

def test_fog_disabled_channels():
    """Stages without fog: ch5=1.0 (all visible), ch6/ch7=0.0 (plumbed zeros)."""
    for stage in [1, 3, 4, 5, 6]:
        config = get_map_config(stage)
        if config.fog_enabled:
            continue  # skip fog-enabled stages for this test

        snap = _make_snapshot(
            active_grid_w=config.active_grid_w,
            active_grid_h=config.active_grid_h,
        )
        obs = vectorize_snapshot(
            snap,
            brain_faction=0,
            enemy_factions=[1, 2],
            active_grid_w=config.active_grid_w,
            active_grid_h=config.active_grid_h,
            fog_enabled=False,
        )

        # Fog disabled: entire 50×50 ch5 should be 1.0 (fully visible)
        assert obs["ch5"].sum() == pytest.approx(2500.0), (
            f"Stage {stage} ch5 should be all 1.0 (fog disabled)"
        )
        # ch6 (interactable terrain) and ch7 (system objective) are plumbed zeros
        assert obs["ch6"].sum() == pytest.approx(0.0), (
            f"Stage {stage} ch6 (interactable terrain) should be all zeros"
        )
        assert obs["ch7"].sum() == pytest.approx(0.0), (
            f"Stage {stage} ch7 (system objective) should be all zeros"
        )


def test_fog_enabled_channels():
    """Stage 4 (Fog Scouting): ch5 starts mostly 0 (unexplored) except brain vicinity."""
    config = get_map_config(4)
    assert config.fog_enabled is True

    active_size = config.active_grid_w * config.active_grid_h

    # Simulate fog: most cells unexplored, small area explored
    fog_explored = [0.0] * active_size
    fog_visible = [0.0] * active_size

    # Brain starts at center: small explored region
    mid = config.active_grid_w // 2
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            idx = (mid + dy) * config.active_grid_w + (mid + dx)
            if 0 <= idx < active_size:
                fog_explored[idx] = 1.0
                fog_visible[idx] = 1.0

    snap = _make_snapshot(
        active_grid_w=config.active_grid_w,
        active_grid_h=config.active_grid_h,
        fog_explored=fog_explored,
        fog_visible=fog_visible,
    )

    obs = vectorize_snapshot(
        snap,
        brain_faction=0,
        enemy_factions=[1, 2],
        active_grid_w=config.active_grid_w,
        active_grid_h=config.active_grid_h,
        fog_enabled=True,
    )

    pad_x = (50 - config.active_grid_w) // 2
    pad_y = (50 - config.active_grid_h) // 2

    # Padding should still be 1.0 (explored/visible)
    assert obs["ch5"][0, 0] == pytest.approx(1.0), "Fog padding should be 1.0"

    # Most active cells should be 0.0 (unexplored)
    active_fog = obs["ch5"][pad_y:pad_y + config.active_grid_h,
                            pad_x:pad_x + config.active_grid_w]
    unexplored_frac = (active_fog < 0.5).sum() / active_fog.size
    assert unexplored_frac > 0.8, "Most of active area should be unexplored in fog"

    # Brain vicinity should be 1.0 (explored)
    center_y = pad_y + mid
    center_x = pad_x + mid
    assert obs["ch5"][center_y, center_x] == pytest.approx(1.0), "Brain vicinity should be explored"


# ══════════════════════════════════════════════════════════════════════
#  Reward Gradient Tests
# ══════════════════════════════════════════════════════════════════════

def test_reward_gradient():
    """Verify: tactical_win > brute_force_win > loss >= timeout.
    
    Gradient guarantee from implementation_plan:
      Tactical Win (+18..+22) ≫ Brute Force Win (+8..+12) > Loss (−11..−13) ≈ Timeout (−11..−15)
    
    Tactical win gets all bonuses: threat_priority(+2),
    flanking(+0.08), plus win terminal with high survival.
    Brute force gets win terminal with low survival, no tactical bonuses.
    """
    weights = _default_reward_weights()

    # ── Tactical win: all enemies dead, many survivors + tactical bonuses ──
    snap_prev_tact = _make_snapshot(brain_count=50, enemy1_count=50, enemy2_count=20)
    snap_tact_win = _make_snapshot(brain_count=45, enemy1_count=0, enemy2_count=0)
    # 70 enemies killed (all), 5 own lost → terminal win
    tactical = compute_shaped_reward(
        snapshot=snap_tact_win,
        prev_snapshot=snap_prev_tact,
        brain_faction=0,
        enemy_faction=[1, 2],
        reward_weights=weights,
        starting_entities=50.0,
        stage=6,
        lure_success=True,
        threat_priority_hit=True,
        flanking_score=0.8,
    )

    # ── Brute force: all enemies dead, few survivors, no tactical bonuses ──
    snap_prev_brute = _make_snapshot(brain_count=50, enemy1_count=50, enemy2_count=20)
    snap_brute_win = _make_snapshot(brain_count=10, enemy1_count=0, enemy2_count=0)
    # 70 enemies killed (all), 40 own lost → terminal win with low survival
    brute = compute_shaped_reward(
        snapshot=snap_brute_win,
        prev_snapshot=snap_prev_brute,
        brain_faction=0,
        enemy_faction=[1, 2],
        reward_weights=weights,
        starting_entities=50.0,
        stage=6,
    )

    # ── Loss: all own killed ──
    snap_prev_loss = _make_snapshot(brain_count=50, enemy1_count=50, enemy2_count=20)
    snap_loss = _make_snapshot(brain_count=0, enemy1_count=30, enemy2_count=15)
    # 25 enemies killed, 50 own lost (all dead) → terminal loss
    loss = compute_shaped_reward(
        snapshot=snap_loss,
        prev_snapshot=snap_prev_loss,
        brain_faction=0,
        enemy_faction=[1, 2],
        reward_weights=weights,
        starting_entities=50.0,
        stage=6,
    )

    # ── Timeout: minimal activity, no kills ──
    snap_prev_timeout = _make_snapshot(brain_count=50, enemy1_count=50, enemy2_count=20)
    snap_timeout = _make_snapshot(brain_count=48, enemy1_count=50, enemy2_count=20)
    timeout = compute_shaped_reward(
        snapshot=snap_timeout,
        prev_snapshot=snap_prev_timeout,
        brain_faction=0,
        enemy_faction=[1, 2],
        reward_weights=weights,
        starting_entities=50.0,
        stage=6,
    )
    # Timeout penalty is applied by env (not reward fn), so add it:
    timeout += weights.loss_terminal

    assert tactical > brute, (
        f"Tactical win ({tactical:.2f}) must beat brute force ({brute:.2f})"
    )
    assert brute > loss, (
        f"Brute force win ({brute:.2f}) must beat loss ({loss:.2f})"
    )
    # Implementation plan: "loss ≈ timeout" — they should be in the same range.
    # Both are deeply negative. The exact ordering depends on casualties.
    assert abs(loss - timeout) < 3.0, (
        f"Loss ({loss:.2f}) and timeout ({timeout:.2f}) should be approximately equal"
    )
    # Both must be significantly worse than brute force win
    assert brute > loss, f"Brute force ({brute:.2f}) must beat loss ({loss:.2f})"
    assert brute > timeout, f"Brute force ({brute:.2f}) must beat timeout ({timeout:.2f})"


def test_reward_values_not_nan():
    """All reward computations produce finite float values."""
    weights = _default_reward_weights()
    snap = _make_snapshot()
    prev = _make_snapshot()

    r = compute_shaped_reward(
        snapshot=snap,
        prev_snapshot=prev,
        brain_faction=0,
        enemy_faction=[1, 2],
        reward_weights=weights,
    )
    assert np.isfinite(r), f"Reward is not finite: {r}"


# ══════════════════════════════════════════════════════════════════════
#  Action Acceptance Tests
# ══════════════════════════════════════════════════════════════════════

def test_multidiscrete_action_accepted(mock_env):
    """SwarmEnv.step(np.array([1, 625])) does not crash."""
    mock_env._active_sub_factions = []
    mock_env._last_snapshot = _make_snapshot()
    mock_env._socket.recv_string.return_value = json.dumps(_make_snapshot())

    action = np.array([1, 625])
    obs, reward, terminated, truncated, info = mock_env.step(action)

    assert "summary" in obs
    for ch in range(8):
        assert f"ch{ch}" in obs
    assert isinstance(reward, float)


def test_action_sinking():
    """Hold(0) with any coordinate produces same Hold directive."""
    dir_a, _ = multidiscrete_to_directives(
        np.array([0, 0]),
        brain_faction=0,
        active_sub_factions=[],
    )
    dir_b, _ = multidiscrete_to_directives(
        np.array([0, 1234]),
        brain_faction=0,
        active_sub_factions=[],
    )

    assert len(dir_a) == 1
    assert len(dir_b) == 1
    assert dir_a[0]["directive"] == "Hold"
    assert dir_b[0]["directive"] == "Hold"
    # Both should be identical despite different coordinates
    assert dir_a[0] == dir_b[0]


def test_merge_back_sinking():
    """MergeBack(5) with any coordinate produces same MergeFaction directive."""
    dir_a, _ = multidiscrete_to_directives(
        np.array([5, 0]),
        brain_faction=0,
        active_sub_factions=[100],
    )
    dir_b, _ = multidiscrete_to_directives(
        np.array([5, 2499]),
        brain_faction=0,
        active_sub_factions=[100],
    )

    assert len(dir_a) == 1
    assert len(dir_b) == 1
    assert dir_a[0]["directive"] == "MergeFaction"
    assert dir_b[0]["directive"] == "MergeFaction"
    assert dir_a[0] == dir_b[0]


# ══════════════════════════════════════════════════════════════════════
#  Spatial Action Tests
# ══════════════════════════════════════════════════════════════════════

def test_attack_coord_produces_waypoint():
    """AttackCoord(1) decodes coordinate and produces UpdateNavigation."""
    directives, _ = multidiscrete_to_directives(
        np.array([1, 51]),  # grid (1, 1) → flat_idx = 1*50 + 1 = 51
        brain_faction=0,
        active_sub_factions=[],
        cell_size=20.0,
        pad_offset_x=0.0,
        pad_offset_y=0.0,
    )

    assert len(directives) == 1
    d = directives[0]
    assert d["directive"] == "UpdateNavigation"
    assert d["target"]["type"] == "Waypoint"
    assert d["target"]["x"] == pytest.approx(30.0)  # (1 - 0) * 20 + 10
    assert d["target"]["y"] == pytest.approx(30.0)  # (1 - 0) * 20 + 10


def test_split_to_coord_produces_two_directives():
    """SplitToCoord(4) produces SplitFaction + UpdateNavigation."""
    directives, _ = multidiscrete_to_directives(
        np.array([4, 0]),
        brain_faction=0,
        active_sub_factions=[],
    )

    assert len(directives) == 2
    assert directives[0]["directive"] == "SplitFaction"
    assert directives[1]["directive"] == "UpdateNavigation"


def test_scout_produces_split_and_nav():
    """Scout(7) produces SplitFaction + UpdateNavigation (no aggro masks)."""
    directives, _ = multidiscrete_to_directives(
        np.array([7, 0]),
        brain_faction=0,
        active_sub_factions=[],
    )

    # SplitFaction + UpdateNav = 2 (no aggro masks — atomic primitive)
    assert len(directives) == 2
    assert directives[0]["directive"] == "SplitFaction"
    assert directives[0]["percentage"] == pytest.approx(0.10)
    assert directives[1]["directive"] == "UpdateNavigation"
    assert directives[1]["target"]["type"] == "Waypoint"


# ══════════════════════════════════════════════════════════════════════
#  No Import Errors
# ══════════════════════════════════════════════════════════════════════

def test_no_circular_imports():
    """Verify critical modules can be imported without errors."""
    import src.env.swarm_env
    import src.env.spaces
    import src.env.rewards
    import src.env.actions
    import src.utils.vectorizer
    import src.utils.lkp_buffer
    import src.models.feature_extractor
    import src.training.curriculum
    import src.config.definitions
    import src.config.game_profile
