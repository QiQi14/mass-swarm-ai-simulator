# Task 04: Python Profile + Env Extension Changelog

## Touched Files
- `macro-brain/profiles/default_swarm_combat.json`
- `macro-brain/src/config/game_profile.py`
- `macro-brain/src/env/swarm_env.py`
- `macro-brain/src/env/spaces.py`
- `macro-brain/tests/test_training.py`
- `macro-brain/tests/test_vectorizer.py`
- `macro-brain/tests/test_swarm_env.py`

## Contract Fulfillment
- Extended `default_swarm_combat.json` and Python's `GameProfile` to define injectable configs: Movement (`movement`), Environment Thresholds (`terrain_thresholds`), Removal Rules (`removal_rules`), and Abstract Abilities (`abilities.activate_buff`). Max density logic mapped dynamically through profile `training.max_density`.
- Updated `SwarmEnv.reset()` payload to serialize these properties dynamically into `ResetEnvironment` ZMQ message.
- Replaced `Frenzy` implementations with `ActivateBuff` semantic in Action Space mappings (`spaces.py`) and directives generation (`swarm_env.py`), enforcing Abstract Buff contracts defined by engine.
- Ensured all tests verify correct mapping and ZMQ mock structure.

## Deviations/Notes
- The test `test_patch8_intervention_swallowing` and `test_patch8_zmq_timeout_truncates` was hanging/failing because the original implementation of the test missed the actual loop condition fields in mock payloads. I fixed the mock logic to accurately supply loop-terminated fields `"type": "state_snapshot"` and the timeout assertions matching `{"zmq_timeout": True}`.

## Human Interventions
- None.
