# Task 08: Training Callbacks Update

```yaml
Task_ID: task_08_training_callbacks
Execution_Phase: 4
Model_Tier: standard
Dependencies:
  - task_06_swarm_env_refactor
  - task_07_curriculum_stages
Target_Files:
  - macro-brain/src/training/callbacks.py
Context_Bindings:
  - context/conventions
```

## Objective

Update training callbacks for the 8-action vocabulary, 8-stage curriculum, and new tactical metrics (fog/lure/flanking).

## Strict Instructions

### 1. Update `ACTION_NAMES`

```python
ACTION_NAMES = [
    "Hold", "AttackCoord", "DropPheromone", "DropRepellent",
    "SplitToCoord", "MergeBack", "Retreat", "Lure",
]
```

### 2. Update `EpisodeLogCallback`

- `num_actions` default to 8
- Add CSV columns for new metrics: `fog_explored_pct`, `flanking_score`, `lure_success`
- Track rolling lure success rate and flanking score
- Add `_lure_successes = deque(maxlen=WINDOW)` and `_flanking_scores = deque(maxlen=WINDOW)`

### 3. Update `EnvStatCallback`

Add logging for new env info fields:

```python
if "fog_explored_pct" in info:
    self.logger.record("env/fog_explored_pct", info["fog_explored_pct"])
if "flanking_score" in info:
    self.logger.record("env/flanking_score", info["flanking_score"])
if "lure_success" in info:
    self.logger.record("env/lure_success", int(info["lure_success"]))
```

### 4. Update `CurriculumCallback`

- Change `max_substage` to 8
- Graduation thresholds per stage (from profile curriculum config):
  - Stages 1-6: 80% WR
  - Stage 7: 75% WR
  - Stage 8: 80% WR over 500 episodes
- Additional graduation conditions by stage:
  - Stage 5: `flanking_score > 0.3`
  - Stage 6: `lure_success_rate > 0.4`
- When graduating, update env's `curriculum_stage` AND reconfigure map size, fog toggle, action mask

### 5. Reset state on graduation

When advancing to next stage, also reset:
- `self.episode_logger._lure_successes.clear()`
- `self.episode_logger._flanking_scores.clear()`

## Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: unit
  Test_Stack: pytest (macro-brain)
  Acceptance_Criteria:
    - "ACTION_NAMES has exactly 8 entries"
    - "CSV header includes fog_explored_pct, flanking_score, lure_success columns"
    - "CurriculumCallback graduates Stage 1 at 80% WR"
    - "CurriculumCallback graduates Stage 5 requires flanking_score > 0.3"
    - "CurriculumCallback graduates Stage 6 requires lure_success_rate > 0.4"
    - "CurriculumCallback advances to max stage 8"
    - "Rolling stats reset on graduation"
  Suggested_Test_Commands:
    - "cd macro-brain && python -m pytest tests/test_callbacks.py -v"
```
