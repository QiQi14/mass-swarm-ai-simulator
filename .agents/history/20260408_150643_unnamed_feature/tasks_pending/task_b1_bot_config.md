Task_ID: B1
Execution_Phase: 2
Model_Tier: advanced
Target_Files:
  - macro-brain/src/config/definitions.py
  - macro-brain/src/config/parser.py
  - macro-brain/src/config/game_profile.py
  - macro-brain/profiles/default_swarm_combat.json
  - macro-brain/src/env/swarm_env.py
Dependencies: A1
Context_Bindings:
  - implementation_plan.md
  - implementation_plan_feature_1.md
  - implementation_plan_feature_2.md
Strict_Instructions:
  1. Add `BotStrategyDef` and `BotStageBehaviorDef` in `definitions.py`.
  2. Parse the `bot_stage_behaviors` correctly in `parser.py`.
  3. Add the behaviors to `game_profile.py` with `get_bot_behavior_for_stage` helper.
  4. Update `default_swarm_combat.json` with Stage 5 and the 5 bot_stage_behaviors.
  5. In `swarm_env.py`, wire the `BotController`, instantiate it, call `.configure()` on reset, and implement `_validate_bot_directive(bot_directive)` (PATCH 2).
  6. In `swarm_env.py step()`, compute the bot directive, validate it, and send ONE batched payload `{"type": "macro_directives", "directives": [brain, bot]}` (PATCH 1). Update the dummy payload in the tick-swallowing loop.
Verification_Strategy:
  Test_Type: unit
  Test_Stack: pytest
  Acceptance_Criteria:
    - Profile JSON loads the 5 stages and behaviors
    - SwarmEnv constructs the expected batch ZMQ payload
    - `_validate_bot_directive` replaces hijacking attempts with Hold
    - Tick swallowing loop also sends the batch format
  Suggested_Test_Commands:
    - cd macro-brain && python -m pytest tests/test_bot_behavior.py -v
