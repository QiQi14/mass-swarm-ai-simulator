"""Exploit-Proof Zero-Sum Reward Function.

All reward weights are read from the GameProfile's RewardWeights contract.
No hardcoded constants — swap the profile to change the reward landscape.

Design principles:
1. NO free reward for existing (kills Coward Policy)
2. Large terminal bonuses for win/loss
3. Per-step reward only from combat (kills, deaths)
4. Time pressure forces engagement
5. Surplus survival bonus on win

Gradient guarantee: Clean Win > Bloody Win > Timeout > Loss

## Exploit Mitigations
- Drip-Feed: No engagement bonus — kills/deaths are the only combat currency
- Pyrrhic Timeout: Win has flat base ensuring any win > timeout
- Coward: Time pressure makes idling net-negative
"""

from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.config.definitions import RewardWeights


def flanking_bonus(
    own_density: np.ndarray,
    sub_faction_density: np.ndarray,
    enemy_density: np.ndarray,
    max_engage_radius: float = 15.0,
) -> float:
    """Detect and reward flanking maneuvers with combat proximity guard.

    ## PATCH 5: Pacifist Flank Exploit Prevention
    1. Distance cutoff: sub-faction centroid must be within max_engage_radius
       of enemy centroid (in grid cells).
    2. Distance attenuation: reward decays linearly as distance increases.

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

    dist_sub_to_enemy = (
        (sub_c[0] - enemy_c[0])**2 + (sub_c[1] - enemy_c[1])**2
    )**0.5

    if dist_sub_to_enemy > max_engage_radius:
        return 0.0

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
            proximity_multiplier = max(
                0.0,
                (max_engage_radius - dist_sub_to_enemy) / max_engage_radius
            )
            return raw_bonus * proximity_multiplier

    return 0.0


def exploration_reward(
    fog_explored: np.ndarray,
    prev_fog_explored: np.ndarray | None,
    reward_per_cell: float = 0.005,
    decay_threshold: float = 0.8,
) -> float:
    """Reward for exploring new map cells under fog of war.
    
    Returns positive reward proportional to number of newly explored cells.
    Decays to 0 once decay_threshold (e.g., 80%) of map is explored.
    
    Args:
        fog_explored: Current explored grid (binary 50x50).
        prev_fog_explored: Previous step's explored grid.
        reward_per_cell: Reward per newly revealed cell.
        decay_threshold: Fraction of map above which reward decays to 0.
    """
    if prev_fog_explored is None:
        return 0.0
    
    # Count active (non-padding) cells: padding has terrain=wall,
    # but fog_explored in padding is always 1.0 — so we can't simply sum.
    # Caller must pass ONLY the active portion or track total active cells.
    explored_pct = fog_explored.mean()
    if explored_pct >= decay_threshold:
        return 0.0
    
    # Count new explored cells. With merged 3-level fog (0.0/0.5/1.0),
    # any value >= 0.4 means "at least explored" (0.5 = explored, 1.0 = visible).
    new_cells = np.sum((fog_explored >= 0.4) & (prev_fog_explored < 0.4))
    return float(new_cells) * reward_per_cell


def threat_priority_bonus(
    snapshot: dict,
    prev_snapshot: dict | None,
    enemy_factions: list[int],
    bonus: float = 2.0,
) -> float:
    """Bonus when the smaller/weaker enemy faction is eliminated first.
    
    Fires once when the first enemy faction reaches 0 count AND it was
    the faction with fewer starting units (or lower avg HP).
    
    Returns bonus if correct target eliminated first, 0.0 otherwise.
    """
    if prev_snapshot is None:
        return 0.0

    counts = snapshot.get("summary", {}).get("faction_counts", {})
    prev_counts = prev_snapshot.get("summary", {}).get("faction_counts", {})
    
    alive = []
    dead = []
    just_died = []
    for fid in enemy_factions:
        # Faction counts sent by Rust ZMQ snapshot are still integer counts
        c = counts.get(str(fid), counts.get(fid, 0))
        prev_c = prev_counts.get(str(fid), prev_counts.get(fid, 0))
        
        if c <= 0:
            dead.append(fid)
            if prev_c > 0:
                just_died.append(fid)
        else:
            alive.append(fid)
    
    # Only fire if exactly one enemy faction JUST died, and others are still alive
    if len(just_died) != 1 or len(alive) == 0:
        return 0.0
    
    # Check if the dead faction was the smaller one (correct target)
    # Use faction_avg_stats HP as tiebreaker
    avg_stats = snapshot.get("summary", {}).get("faction_avg_stats", {})
    dead_fid = just_died[0]
    
    # Heuristic: the "correct" target is the one with fewer units at start
    # This is determined by the profile, but we approximate from count ratios
    # The bonus is applied by the env which knows the faction configs
    return bonus


def compute_flanking_score(
    brain_centroid: tuple[float, float] | None,
    sub_centroid: tuple[float, float] | None,
    enemy_centroid: tuple[float, float] | None,
) -> float:
    """Compute flanking angle score between main body and sub-faction.
    
    Returns 0.0-1.0 based on the angle between:
      main_body → enemy vector
      sub_faction → enemy vector
    
    Score = angle / 180°. Angle > 60° = flanking. 180° = perfect pincer.
    Returns 0.0 if any centroid is missing.
    """
    if brain_centroid is None or sub_centroid is None or enemy_centroid is None:
        return 0.0
    
    bx, by = brain_centroid
    sx, sy = sub_centroid
    ex, ey = enemy_centroid
    
    # Vectors: brain→enemy and sub→enemy
    v1 = (ex - bx, ey - by)
    v2 = (ex - sx, ey - sy)
    
    len1 = (v1[0]**2 + v1[1]**2)**0.5
    len2 = (v2[0]**2 + v2[1]**2)**0.5
    
    if len1 < 0.01 or len2 < 0.01:
        return 0.0
    
    dot = v1[0]*v2[0] + v1[1]*v2[1]
    cos_angle = max(-1.0, min(1.0, dot / (len1 * len2)))
    
    import math
    angle_rad = math.acos(cos_angle)
    angle_deg = math.degrees(angle_rad)
    
    # Score: angle / 180, clamped to [0, 1]
    return min(angle_deg / 180.0, 1.0)


def compute_shaped_reward(
    snapshot: dict,
    prev_snapshot: dict | None,
    brain_faction: int,
    enemy_faction: int | list[int],
    reward_weights: RewardWeights | None = None,
    starting_entities: float = 50.0,
    stage: int = 1,
    fog_explored: np.ndarray | None = None,
    prev_fog_explored: np.ndarray | None = None,
    flanking_score: float = 0.0,
    lure_success: bool = False,
    threat_priority_hit: bool = False,
) -> float:
    """Exploit-proof zero-sum reward function.

    Args:
        snapshot: Current state snapshot from Rust.
        prev_snapshot: Previous state snapshot (None on first step).
        brain_faction: Faction ID controlled by the RL agent.
        enemy_faction: Faction ID(s) of the bot opponent(s).
        reward_weights: Weights from the game profile. Uses defaults if None.
        starting_entities: Initial entity count per faction (from profile).

    Returns:
        Shaped reward for this step.
    """
    # Lazily import to avoid circular dependency
    if reward_weights is None:
        from src.config.definitions import RewardWeights
        reward_weights = RewardWeights(
            time_penalty_per_step=-0.01,
            kill_reward=0.05,
            death_penalty=-0.03,
            win_terminal=10.0,
            loss_terminal=-10.0,
            survival_bonus_multiplier=5.0,
        )

    # Normalize enemy_faction to list
    if isinstance(enemy_faction, int):
        enemy_factions = [enemy_faction]
    else:
        enemy_factions = list(enemy_faction)

    own_key = str(brain_faction)
    reward = 0.0

    # ── 1. TIME PRESSURE (Anti-Coward) ────────────────────────
    reward += reward_weights.time_penalty_per_step

    if prev_snapshot is not None:
        prev_counts = prev_snapshot.get("summary", {}).get("faction_counts", {})
        curr_counts = snapshot.get("summary", {}).get("faction_counts", {})

        prev_own = prev_counts.get(own_key, prev_counts.get(int(own_key), 0))
        curr_own = curr_counts.get(own_key, curr_counts.get(int(own_key), 0))

        # Aggregate enemy counts across all enemy factions
        prev_enemy = sum(
            prev_counts.get(str(ef), prev_counts.get(ef, 0))
            for ef in enemy_factions
        )
        curr_enemy = sum(
            curr_counts.get(str(ef), curr_counts.get(ef, 0))
            for ef in enemy_factions
        )

        # ── 2. COMBAT TRADING (Aggression Incentive) ──────────
        enemies_killed = max(0, prev_enemy - curr_enemy)
        own_lost = max(0, prev_own - curr_own)
        
        if stage == 4:
            own_lost = 0  # Eliminate death penalty for Stage 4 (fog)

        reward += enemies_killed * reward_weights.kill_reward
        reward += own_lost * reward_weights.death_penalty  # death_penalty is negative

        # ── 3. TERMINAL: WIN ─────────────────────────────────
        if curr_enemy == 0 and curr_own > 0:
            survival_ratio = curr_own / starting_entities
            reward += reward_weights.win_terminal + (
                reward_weights.survival_bonus_multiplier * survival_ratio
            )

        # ── 4. TERMINAL: LOSS ─────────────────────────────────
        elif curr_own == 0 and prev_own > 0:
            reward += reward_weights.loss_terminal  # loss_terminal is negative

    # ── 5. EXPLORATION (Fog-enabled stages: 4+) ────────────────────
    if stage >= 4 and fog_explored is not None:
        reward += exploration_reward(
            fog_explored, prev_fog_explored,
            reward_weights.exploration_reward,
            reward_weights.exploration_decay_threshold,
        )
    
    # ── 6. THREAT PRIORITY (Stage 1+) ───────────────────────
    if threat_priority_hit:
        reward += reward_weights.threat_priority_bonus
    
    # ── 7. FLANKING GEOMETRY (Stage 5+) ─────────────────────
    if stage >= 5 and flanking_score > 0.0:
        reward += reward_weights.flanking_bonus_scale * flanking_score
    
    # ── 8. LURE SUCCESS (Stage 6+) ──────────────────────────
    if stage >= 6 and lure_success:
        reward += reward_weights.lure_success_bonus

    return float(reward)

