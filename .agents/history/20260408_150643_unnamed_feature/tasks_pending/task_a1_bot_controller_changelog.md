# Task A1: Bot Controller Changelog

## Touched Files
- [NEW] `macro-brain/src/env/bot_controller.py`
- [NEW] `macro-brain/tests/test_bot_controller.py`

## Contract Fulfillment
- Implemented `BotController` class exactly according to the provided `implementation_plan_feature_1.md` contract.
- Implemented `MIN_LOCK_STEPS = 15` hysteresis logic in the `Adaptive` strategy to prevent frame-by-frame jitter, locking modes properly.
- All directive builders output the inner-format JSON (no `"type"` wrapper) as explicitly described.
- Implemented comprehensive `pytest` covering strategies, counting, state lock verification, mixed functionality, and hysteresis resetting during `.configure()`. 

## Deviations/Notes
- `_validate_bot_directive` logic was explicitly NOT placed inside `BotController.py` since the instructions indicated: "wait for B1 to place it in SwarmEnv".
- No human interventions occurred. 
