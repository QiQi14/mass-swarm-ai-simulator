# Task 09: Reward Shaping & Curriculum - Changelog

## Touched Files
- `macro-brain/src/env/rewards.py` (NEW)
- `macro-brain/src/env/swarm_env.py` (MODIFIED)
- `macro-brain/tests/test_rewards.py` (NEW)

## Contract Fulfillment
- Implemented `flanking_bonus` algorithm with PATCH 5 fully applied, including combat proximity guard and distance attenuation.
- Implemented `compute_shaped_reward` factoring in 5 essential components: survival, kill, territory, health delta, and flanking bonus.
- Wired `compute_shaped_reward` inside `SwarmEnv._compute_reward` seamlessly.
- Wrote full unit test coverage ensuring that:
  - Pacifist Flank Exploit is blocked via max engage radius distance checking.
  - Genuine flanks at close range return appropriately shaped rewards.
  - Distance attenuation strictly follows monotonically decreasing behaviors.
  - Zero presence geometries return a 0.0 bounded bonus.
  - Shaped rewards correctly compose different reward components into a reasonable aggregated float factor.

## Deviations/Notes
- **Test Adjustment:** In `test_patch5_distance_attenuation`, the spatial alignment coordinates were fine-tuned to guarantee that `raw_bonus` from projection overlaps was maxed out to `1.0` in all sub-faction positions. By saturating the underlying bonus ceiling, we purely isolated and verified the standalone behavior of the linearly scaling `proximity_multiplier`.
- **Environment Delta:** Wired `prev_snapshot` capturing into `swarm_env.py` `step()` logic right before `self._last_snapshot` overwritten allocation. This ensures `compute_shaped_reward` inherently accesses reliable delta windows to measure survival continuity and enemy elimination counts iteratively.
