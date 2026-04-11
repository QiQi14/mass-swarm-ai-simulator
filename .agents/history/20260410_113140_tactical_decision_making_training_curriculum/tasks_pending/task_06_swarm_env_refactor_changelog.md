# Task 06 Changelog

## Touched Files
- `macro-brain/src/env/swarm_env.py`

## Contract Fulfillment
- SwarmEnv `__init__` now initializes MultiDiscrete action space and LKP-integrated observation space with center-padding.
- `action_masks()` returns a completely flattened mask (length 2508) based on `make_coordinate_mask` and active sub-factions/stage unlocks.
- `reset()` correctly resets all state flags, buffers, tracking variables, retrieves fog configurations appropriately.
- `step()` is fully compatible with taking a `(2,)` `np.ndarray` input and passing it into `multidiscrete_to_directives` correctly translating actions. Lure creation logic via extracting "SplitFaction" parameters operates effectively.
- Implementation covers `_get_stage_action_unlock` to incrementally allow capabilities per curriculum tier.
- Lure Success Detection accurately detects cases where the target count has dwindled while the patrol unit is more than 200 grid positions out.

## Deviations/Notes
- `self._target_spawn_pos` was retrieved dynamically inside the `reset()` loop from the returned spawns payload and assigned immediately before calling vectorization, to ensure the new `_check_lure_success` has access to the target coordinates required to compute the patrol's distance.
- `threat_priority_bonus` natively computes evaluation against snapshot counts internally so we check for bonus hit `> 0.0` directly to feed `compute_shaped_reward`.
- Refactored `_compute_reward` to accept kwargs such as `fog_explored`, `flanking_score`, `lure_success`, etc.
