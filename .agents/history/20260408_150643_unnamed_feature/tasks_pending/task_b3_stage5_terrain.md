Task_ID: B3
Execution_Phase: 2
Model_Tier: basic
Target_Files:
  - macro-brain/src/training/curriculum.py
  - macro-brain/src/utils/terrain_generator.py
Dependencies: None
Context_Bindings:
  - implementation_plan_feature_2.md
Strict_Instructions:
  1. Implement `get_stage5_spawns(rng, profile)` in `curriculum.py` for fully random 1-2 brain groups and 2-4 bot groups around the map.
  2. Update `get_spawns_for_stage` to map stage 5+ to this new generator function.
  3. Update `generate_terrain_for_stage` in `terrain_generator.py` to ensure Stage 5+ generates complex procedural terrain (if not already returning it by default for else branches).
Verification_Strategy:
  Test_Type: unit
  Test_Stack: pytest
  Acceptance_Criteria:
    - Stage 5 returns spawns for both factions
    - Spawn positions are within map bounds
    - Terrain returns the complex config
  Suggested_Test_Commands:
    - cd macro-brain && python -m pytest tests/test_training.py -v
