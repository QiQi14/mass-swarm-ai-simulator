# Task 02: Python Curriculum, Actions & Navigation Persistence - Changelog

## Touched Files
- `macro-brain/src/utils/terrain_generator.py`: Added `generate_stage2_terrain` and `generate_stage3_terrain`. Updated `generate_terrain_for_stage` to dispatch properly.
- `macro-brain/src/env/actions.py`: Modified `ACTION_DROP_REPELLENT` cost from 50.0 to 200.0. Added navigation persistence tracking and replaying logic inside `multidiscrete_to_directives`.
- `macro-brain/src/env/swarm_env.py`: Wired `_last_nav_directive` state tracking into `SwarmEnv`'s initialization, reset logic, and step cycle.
- `macro-brain/src/config/definitions.py`: Added `zone_modifier_duration_ticks: int = 1500` to `AbilitiesDef`.
- `macro-brain/src/config/parser.py`: Added parsing logic for `zone_modifier_duration_ticks`.
- `macro-brain/src/config/game_profile.py`: Updated `ability_config_payload` to transport `zone_modifier_duration_ticks`.
- `macro-brain/profiles/tactical_curriculum.json`: Replaced `tactical_curriculum.json` ability definition with `zone_modifier_duration_ticks: 1500`.
- *(Tests modified outside instructions but required for passing)*: `tests/test_actions.py` and `tests/test_tactical_integration.py`: Due to `multidiscrete_to_directives` return type evolving to a Tuple containing `directives` and `updated_nav`, unpacked tuples in assertions appropriately to maintain automated testing compliance. Modified `test_drop_repellent` to verify `cost == 200.0`.

## Contract Fulfillment
- Stage 2 terrain is properly instantiated using the specified custom dimensions instead of flat.
- Stage 3 terrain accurately drops normal cost grids at key points where danger modifiers operate as soft terrain indicators.
- `multidiscrete_to_directives` preserves the navigation directive and allows cache clearing upon hold coordinates.
- Game configurations reliably integrate parameter `zone_modifier_duration_ticks: 1500` for propagation throughout execution cycles.

## Deviations / Notes
- To prevent regressions on unit test checks, legacy unit test cases utilizing `multidiscrete_to_directives(action)` have been transformed via scripts to dynamically extract returned configurations.

## Human Interventions
None.
