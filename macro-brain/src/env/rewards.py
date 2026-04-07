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


def compute_shaped_reward(
    snapshot: dict,
    prev_snapshot: dict | None,
    brain_faction: int,
    enemy_faction: int,
    reward_weights: RewardWeights | None = None,
    starting_entities: float = 50.0,
) -> float:
    """Exploit-proof zero-sum reward function.

    Args:
        snapshot: Current state snapshot from Rust.
        prev_snapshot: Previous state snapshot (None on first step).
        brain_faction: Faction ID controlled by the RL agent.
        enemy_faction: Faction ID of the bot opponent.
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

    own_key = str(brain_faction)
    enemy_key = str(enemy_faction)
    reward = 0.0

    # ── 1. TIME PRESSURE (Anti-Coward) ────────────────────────
    reward += reward_weights.time_penalty_per_step

    if prev_snapshot is not None:
        prev_counts = prev_snapshot.get("summary", {}).get("faction_counts", {})
        curr_counts = snapshot.get("summary", {}).get("faction_counts", {})

        prev_own = prev_counts.get(own_key, prev_counts.get(int(own_key), 0))
        curr_own = curr_counts.get(own_key, curr_counts.get(int(own_key), 0))
        prev_enemy = prev_counts.get(enemy_key, prev_counts.get(int(enemy_key), 0))
        curr_enemy = curr_counts.get(enemy_key, curr_counts.get(int(enemy_key), 0))

        # ── 2. COMBAT TRADING (Aggression Incentive) ──────────
        enemies_killed = max(0, prev_enemy - curr_enemy)
        own_lost = max(0, prev_own - curr_own)

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

    return float(reward)
