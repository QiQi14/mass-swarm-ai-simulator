# Changelog for task_02_reward_components

## Touched Files
- `macro-brain/src/config/definitions.py`
- `macro-brain/src/env/rewards.py`

## Contract Fulfillment
- Extended `RewardWeights` frozen dataclass with new tactical shaping weights (approach, exploration, threat priority, flanking, lure, debuff).
- Implemented `exploration_reward`, `threat_priority_bonus`, and `compute_flanking_score` functions.
- Updated `compute_shaped_reward` signature and conditionally computed new tactical rewards based on current `stage` and injected states (`fog_explored`, `flanking_score`, `lure_success`, `threat_priority_hit`).

## Deviations/Notes
- **GAP REPORT:** When running the suggested test command `cd macro-brain && python -m pytest tests/test_rewards.py -v` (using `.venv/bin/python`), it failed with: `ImportError: cannot import name 'GRID_WIDTH' from 'src.env.spaces' (/Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/macro-brain/src/env/spaces.py)`. The error originates in `src/utils/vectorizer.py`. According to **Rule 1: Scope Isolation**, I have STOPPED and am reporting this gap, as modifying `src/utils/vectorizer.py` is outside my `Target_Files`. `spaces.py` seems to have renamed `GRID_WIDTH` to `MAX_GRID_WIDTH` during a previous task, missing the update in `vectorizer.py`.

## Human Interventions
- None.
