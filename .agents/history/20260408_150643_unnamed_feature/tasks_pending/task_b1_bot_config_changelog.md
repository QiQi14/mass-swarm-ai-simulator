# Task B1: Bot Config + Profile Updates Changelog

## Target Files Modified
- `macro-brain/src/config/definitions.py` (Modified)
- `macro-brain/src/config/parser.py` (Modified)
- `macro-brain/src/config/game_profile.py` (Modified)
- `macro-brain/profiles/default_swarm_combat.json` (Modified)
- `macro-brain/src/env/swarm_env.py` (Modified)
- `macro-brain/tests/test_bot_behavior.py` (New)

## Execution Summary
1. **Config Interfaces**:
   - Added `BotStrategyDef` and `BotStageBehaviorDef` to `definitions.py`.
   - Updated `parser.py` to parse `bot_stage_behaviors` from raw JSON.
   - Wired `bot_stage_behaviors` into `game_profile.py`, including accessor `get_bot_behavior_for_stage` and serialization `bot_behaviors_payload`.

2. **Game Profile JSON**:
   - Updated Stage 5 in the training curriculum.
   - Added the 5-stage `bot_stage_behaviors` map corresponding to Charge, Adaptive, HoldPosition, and Mixed logic.

3. **SwarmEnv Integration**:
   - Wired `BotController` into `SwarmEnv` initialization.
   - Invoked `BotController.configure()` dynamically based on the curriculum stage accessed from the profile.
   - Sent `bot_behaviors` into the environment reset payload via `ZMQ`.
   - Updated the step function to capture both `bot_directive` and `brain_directive` and bundle them inside a `"macro_directives"` batched JSON array for sending to Rust.

4. **Security Patches**:
   - Added `_validate_bot_directive` boundary inside `SwarmEnv` ensuring `BotController` cannot configure directives affecting the `brain_faction`.

## Verification
- Wrote `macro-brain/tests/test_bot_behavior.py` asserting properties of strategy dict mappings, stage fallback logic, and profile loading structure.
- **Fixed `macro-brain/tests/test_swarm_env.py` expectations**:
   - Replaced old `{"type": "macro_directive", "directive": "Hold"}` assertions with `{"type": "macro_directives", "directives": [{"directive": "Hold"}, {"directive": "Hold"}]}` logic tests for Tick Swallowing.
   - Refactored `GameProfile` initialization slightly inside testing environments to prevent required-argument failures by registering a default field array.
- The `pytest tests/ -v` test suite executed cleanly reporting **61 completed Unit Tests without Errors**.

## Human Interventions
No human interventions were required during this execution. All task logic complied entirely with the implementation plan limits.
