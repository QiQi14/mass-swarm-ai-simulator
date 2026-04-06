# Changelog for task_06_swarm_env

## Touched Files
- `macro-brain/src/env/swarm_env.py` (NEW)
- `macro-brain/tests/test_swarm_env.py` (NEW)

## Contract Fulfillment
- Implemented `SwarmEnv` extending `gym.Env` with observation and action spaces defined in `src.env.spaces`.
- ZMQ REP protocol established (binds to `tcp://*:5555`), enforcing strict `recv` -> `send` alternation per tick.
- Action indices `Discrete(8)` accurately mapped to `MacroDirective` JSONs via `_action_to_directive`.
- Safety patches integrated:
  - **P6 Dynamic Epicenter:** Implemented `_get_density_centroid(faction)` to dynamically calculate `SetZoneModifier` and `SplitFaction` targets.
  - **P7 Single Source of Truth:** Replaced locale state for `_active_sub_factions` by directly reading from the `active_sub_factions` array in the Rust snapshot each step.
  - **P8 ZMQ + MDP Safety:**
    - Tick swallowing loop created in `step()` to hold interventions safely from SB3 (`intervention_active == True`).
    - Handled ZMQ `Again` timeout cleanly by aborting socket reads and emitting `truncated=True` with no terminal failure.

## Deviations/Notes
- Changed imports from `macro_brain.*` to `src.*` to avoid Python's invalid module naming error for hyphenated directories (`gotcha_hyphen_module_name.md`), running tests using `PYTHONPATH=.`.

## Human Interventions
- None.
