# Task 11: Integration Tests — Changelog

## Touched Files

- **`macro-brain/tests/test_lkp_buffer.py`** — NEW: 8 integration tests for LKPBuffer
- **`macro-brain/tests/test_feature_extractor.py`** — NEW: 7 integration tests for TacticalExtractor
- **`macro-brain/tests/test_tactical_integration.py`** — NEW: 20 end-to-end integration tests

## Contract Fulfillment

### test_lkp_buffer.py (8 tests)
All 5 specified tests plus 3 additional robustness tests:
- `test_lkp_overwrites_visible_cells` — Visible cells get ground truth density ✅
- `test_lkp_decays_hidden_cells` — Hidden cells decay by decay_rate per update ✅
- `test_lkp_never_negative` — Decayed density never drops below 0 ✅
- `test_lkp_reset_zeros_memory` — reset() clears all stored density ✅
- `test_lkp_mixed_visible_hidden` — Partial visibility: some overwrite, others decay ✅
- `test_lkp_update_returns_copy` — update() returns copy, not internal reference ✅
- `test_lkp_get_returns_copy` — get() returns copy, not internal reference ✅
- `test_lkp_independent_channels` — Updating one channel doesn't affect the other ✅

### test_feature_extractor.py (7 tests)
All 4 specified tests plus 3 additional robustness tests:
- `test_extractor_forward_shape` — Forward pass produces (B, 256) tensor ✅
- `test_extractor_batch_processing` — Batch of 4 produces (4, 256) output ✅
- `test_extractor_handles_summary_dim` — 12-dim summary processed correctly ✅
- `test_extractor_cnn_output_nonzero` — Non-zero input → non-zero output ✅
- `test_extractor_features_dim_configurable` — features_dim can be set to 128 ✅
- `test_extractor_zero_input_produces_finite_output` — No NaN/Inf on zero input ✅
- `test_extractor_gradient_flows` — Backprop gradients flow through full extractor ✅

### test_tactical_integration.py (20 tests)
All 11 specified tests plus 9 additional coverage tests:
- `test_observation_shape_all_stages` — All 8 stages: 8ch×(50,50)+summary(12) ✅
- `test_action_masking_stage1` — Stage 1: only Hold and AttackCoord unmasked ✅
- `test_action_masking_stage4` — Stage 4: +DropPheromone, +DropRepellent ✅
- `test_action_masking_stage6` — Stage 6+: all 8 actions unmasked ✅
- `test_coordinate_masking_small_map` — Stage 1 (25×25): 625 of 2500 active ✅
- `test_coordinate_masking_full_map` — Stage 6 (50×50): all 2500 active ✅
- `test_coordinate_masking_matches_stage_env` — Env mask count matches stage config ✅
- `test_center_padding` — Terrain padding = 1.0 (wall) ✅
- `test_density_padding_is_zero` — Density channels 0.0 in padding zone ✅
- `test_fog_disabled_channels` — Fog off: ch5/ch6 all 1.0 ✅
- `test_fog_enabled_channels` — Stage 2: ch5 mostly unexplored, brain vicinity explored ✅
- `test_reward_gradient` — tactical_win > brute_force > {loss ≈ timeout} ✅
- `test_reward_values_not_nan` — All reward computations produce finite floats ✅
- `test_multidiscrete_action_accepted` — SwarmEnv.step(np.array([1, 625])) no crash ✅
- `test_action_sinking` — Hold(0) ignores coordinate ✅
- `test_merge_back_sinking` — MergeBack(5) ignores coordinate ✅
- `test_attack_coord_produces_waypoint` — AttackCoord decodes to UpdateNavigation ✅
- `test_split_to_coord_produces_two_directives` — SplitToCoord → Split+Nav ✅
- `test_lure_produces_split_and_aggro` — Lure → Split+Nav+AggroMask(×2) ✅
- `test_no_circular_imports` — All critical modules import cleanly ✅

## Deviations/Notes

1. **Reward gradient assertion**: The implementation plan states the gradient as `loss ≈ timeout`. Testing confirmed this is approximate — the exact ordering depends on casualties in the loss scenario. The test uses `abs(loss - timeout) < 3.0` for the loss/timeout comparison, while strictly enforcing `tactical > brute > {loss, timeout}`.

2. **Mock env profile path**: The `mock_env` fixture uses `profiles/tactical_curriculum.json` (the only existing profile). The legacy `stage1_tactical.json` no longer exists per the plan's "Fresh Start" directive.

3. **Additional tests beyond spec**: Added 12 extra tests (copy semantics, gradient flow, intermediate stages, density padding, import validation) for comprehensive coverage without modifying any source code.

## Human Interventions

None.
