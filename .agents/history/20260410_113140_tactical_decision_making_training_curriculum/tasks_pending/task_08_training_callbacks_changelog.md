# Task 08: Training Callbacks Update Changelog

## Touched Files
- `macro-brain/src/training/callbacks.py`

## Contract Fulfillment
- **ACTION_NAMES Update**: Updated `ACTION_NAMES` to explicitly align with the 8-action tactical vocabulary.
- **EpisodeLogCallback Enhancement**: Adjusted default `num_actions` to 8 initialization. Configured dedicated `deque` variables and tracking logic to log rolling stats for `_lure_successes` and `_flanking_scores` based on `info` values. Updated headers to include newly added metrics (`fog_explored_pct`, `flanking_score`, `lure_success`).
- **EnvStatCallback Extension**: Updated `_on_step` hook to successfully parse and emit standard logs for tactical metrics whenever available in the environment `info` trace.
- **CurriculumCallback Revamp**: Scaled `max_substage` to 8 and updated dynamic thresholds explicitly per prompt logic. Targets WR=0.8 for stages 1-6, WR=0.75 for stage 7. Introduces 500-ep streak requirement for ultimate stage 8 graduation. Applied explicit extra criterion constraints based on rolling stats to Stage 5 (`flanking_score > 0.3`) and Stage 6 (`lure_success_rate > 0.4`).
- **Graduation Reset**: Ensured rolling score tracking deques (`_lure_successes` and `_flanking_scores`) are explicitly fully cleared during the sub-stage graduation progression callback hook.

## Deviations/Notes
- Since the callback heavily leverages `.episode_logger` deques to verify `extra_criteria`, strict handling was written to parse `[-200:]` history explicitly. Divide by zero issues on early streaks are mitigated safely.
- No other major deviations from the objective specs.
