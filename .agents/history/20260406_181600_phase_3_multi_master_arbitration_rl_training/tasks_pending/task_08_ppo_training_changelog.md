# Task 08: PPO Training Loop + Curriculum + Terrain Generator

## Touched Files
- `macro-brain/requirements.txt` (MODIFIED)
- `macro-brain/src/env/swarm_env.py` (MODIFIED)
- `macro-brain/src/utils/terrain_generator.py` (NEW)
- `macro-brain/src/training/curriculum.py` (NEW)
- `macro-brain/src/training/callbacks.py` (NEW)
- `macro-brain/src/training/train.py` (NEW)
- `macro-brain/tests/test_terrain_generator.py` (NEW)
- `macro-brain/tests/test_training.py` (NEW)

## Contract Fulfillment
- Added `sb3-contrib>=2.6.0` to `requirements.txt`.
- Implemented `action_masks` and `curriculum_stage` inside `SwarmEnv`, adjusting the `reset` method to perform 2 cycles: first to send `ResetEnvironment` with optional terrain and spawns, and then second to retrieve the updated state and return the observation.
- Provided a fully compliant 3-tier Python procedural terrain generator producing passable floors, destructible walls, and permanent walls with guaranteed cleared spawn zones and pathing constraints.
- Created `CurriculumCallback` for stable-baselines3, verifying stage 1 rewards before promoting the training environment to stage 2.
- Created generic and statistics-oriented callbacks inside `callbacks.py`.
- Exposed CLI and MaskablePPO logic inside `train.py`.
- Backed the additions with Pytest code for `terrain_generator` and `swarm_env` action masking + initialization verification.

## Deviations / Notes
- The terrain generator leverages `np.ogrid` logic appropriately to respect the bounds matching the 50x50 board, utilizing `np.clip` and bounding box subsets to guard against out-of-bounds rendering for swamps and walls hitting edges.
- Used a mock ZMQ context to ensure PPO model initialization and step testing runs seamlessly without requiring a running Rust backend.
