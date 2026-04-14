# Test Archive Index

> Auto-generated. Run `python3 .agents/scripts/gen_tests_index.py <archive_path>` to regenerate.

**Feature:** Tactical Decision-Making Training Curriculum
**Archived:** 2026-04-10
**Tasks Verified:** 10

## Test Files

| Test File | Task | Test Type | Test Stack | Criteria Covered | Result |
|-----------|------|-----------|------------|-----------------|--------|
| `macro-brain/tests/test_spaces_task01.py` | task_01_action_obs_spaces | unit | pytest (macro-brain) | ** Verified make_action_space, make_observation_space, decode_spatial, make_coordinate_mask, grid_to | PASS |
| `macro-brain/tests/test_rewards_task02.py` | task_02_reward_components | unit | pytest (macro-brain) | ** Verified RewardWeights, exploration_reward, compute_flanking_score, compute_shaped_reward
- **Tes | PASS |
| `macro-brain/tests/test_lkp_vectorizer_task03.py` | task_03_vectorizer_lkp | unit | pytest (macro-brain) | ** Covers LKPBuffer methods and vectorize_snapshot paths with/without fog
- **Test Stack:** pytest ( | PASS |
| `types.rs` | task_04_rust_fog_zmq | unit | cargo test (micro-core) | ** JSON roundtrip serialization checks for fog
- **Test Stack:** cargo test (micro-core) | PASS |
| `macro-brain/tests/test_actions.py` | task_05_action_mapper | unit | pytest (macro-brain) | ** 
  - `test_hold_action`: "Hold action ignores coordinate, returns Hold directive"
  - `test_attac | PASS |
| `macro-brain/tests/test_swarm_env.py` | task_06_swarm_env_refactor | unit | unknown | ** 
  - `action_masks` logic (length, sub-factions blocking, stage-locking, coordinate maps)
  - `st | PASS |
| `(2,) np.ndarray` | task_06_swarm_env_refactor | unit | unknown | ** 
  - `action_masks` logic (length, sub-factions blocking, stage-locking, coordinate maps)
  - `st | PASS |
| `macro-brain/tests/test_curriculum.py` | task_07_curriculum_stages | unit | pytest (macro-brain) | ** 
  - `test_get_spawns_for_stage_1`: "get_spawns_for_stage(1) returns 3 factions with correct coun | PASS |
| `macro-brain/tests/test_callbacks_task08.py` | task_08_training_callbacks | unit | pytest (macro-brain) | ** ACTION_NAMES length, CSV headers addition, Curriculum graduation Stage 1/5/6.
- **Test Stack:** p | PASS |
| `macro-brain/tests/test_feature_extractor_task09.py` | task_09_feature_extractor_train | unit | pytest (macro-brain) | ** Shape of output, tensor compatibility, feature_dim configuration.
- **Test Stack:** pytest (macro | PASS |
| `macro-brain/tests/test_game_profile_task10.py` | task_10_game_profile | unit | pytest (macro-brain) | ** Tested for tactical_curriculum.json existence, parsing correctness, exact structure (8 actions, 8 | PASS |

## Verification Summary

| Task | Test Type | Files | Result |
|------|-----------|-------|--------|
| task_01_action_obs_spaces | unit | 1 file(s) | PASS |
| task_02_reward_components | unit | 1 file(s) | PASS |
| task_03_vectorizer_lkp | unit | 1 file(s) | PASS |
| task_04_rust_fog_zmq | unit | 1 file(s) | PASS |
| task_05_action_mapper | unit | 1 file(s) | PASS |
| task_06_swarm_env_refactor | unit | 2 file(s) | PASS |
| task_07_curriculum_stages | unit | 1 file(s) | PASS |
| task_08_training_callbacks | unit | 1 file(s) | PASS |
| task_09_feature_extractor_train | unit | 1 file(s) | PASS |
| task_10_game_profile | unit | 1 file(s) | PASS |

---

*Generated on 2026-04-13 20:18:34*
