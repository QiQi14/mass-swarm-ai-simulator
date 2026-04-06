# Task 08: PPO Training Loop + Curriculum + Terrain Generator

**Task_ID:** `task_08_ppo_training`
**Execution_Phase:** 4
**Model_Tier:** `advanced`
**Target_Files:**
  - `macro-brain/src/training/train.py` (NEW)
  - `macro-brain/src/training/callbacks.py` (NEW)
  - `macro-brain/src/training/curriculum.py` (NEW)
  - `macro-brain/src/utils/terrain_generator.py` (NEW)
  - `macro-brain/src/env/swarm_env.py` (MODIFY — action_masks + curriculum_stage + ResetEnvironment reset)
  - `macro-brain/requirements.txt` (MODIFY — add sb3-contrib)
  - `macro-brain/tests/test_terrain_generator.py` (NEW)
  - `macro-brain/tests/test_training.py` (NEW)
**Dependencies:** Task 06 (SwarmEnv), Task 07 (ZMQ protocol + AiResponse)
**Context_Bindings:**
  - `implementation_plan.md` → Training Strategy, Curriculum, Terrain Generator sections (FULL)
  - `implementation_plan_feature_3.md` → Task 08 section (legacy reference)

## Strict Instructions

### 1. Update `requirements.txt`

Add `sb3-contrib>=2.6.0` for MaskablePPO:

```
pyzmq>=25.1.2
gymnasium>=1.2.0
numpy>=2.0.0
stable-baselines3>=2.6.0
sb3-contrib>=2.6.0
torch>=2.11.0
tensorboard>=2.19.0
pytest>=8.0.0
```

### 2. Modify `swarm_env.py` — Action Masking + Curriculum

Add `action_masks()` method (required by `MaskablePPO`):

```python
def action_masks(self) -> np.ndarray:
    mask = np.ones(8, dtype=bool)
    if self.curriculum_stage == 1:
        mask[4:8] = False  # Lock terrain-dependent actions
    else:
        if not self._active_sub_factions:
            mask[6] = False  # MergeFaction
            mask[7] = False  # SetAggroMask
    return mask
```

Add `curriculum_stage` to `__init__`:
```python
self.curriculum_stage = config.get("curriculum_stage", 1)
```

Update `reset()` to send `ResetEnvironment` via ZMQ:
```python
def reset(self, seed=None, options=None):
    # Cycle 1: recv initial snapshot → send ResetEnvironment
    raw = self._socket.recv_string()
    
    terrain = None
    if self.curriculum_stage >= 2:
        from src.utils.terrain_generator import generate_random_terrain
        terrain = generate_random_terrain(seed=self.np_random.integers(0, 2**31))
    
    self._socket.send_string(json.dumps({
        "type": "reset_environment",
        "terrain": terrain,
        "spawns": [
            {"faction_id": 0, "count": 150, "x": 200.0, "y": 500.0, "spread": 80.0},
            {"faction_id": 1, "count": 150, "x": 800.0, "y": 500.0, "spread": 80.0},
        ]
    }))
    
    # Cycle 2: recv fresh post-reset snapshot → send Hold
    raw = self._socket.recv_string()
    snapshot = json.loads(raw)
    ...
```

### 3. Create `terrain_generator.py`

Procedural terrain with 3-tier encoding and BFS connectivity guarantee:

```python
TIER0_PASSABLE = 100
TIER1_DESTRUCTIBLE = 62_000
TIER2_PERMANENT = 65_535

def generate_random_terrain(
    width: int = 50, height: int = 50,
    wall_density: float = 0.1,
    num_chokepoints: int = 3,
    num_swamp_patches: int = 5,
    swamp_cost_range: tuple = (30, 70),
    destructible_ratio: float = 0.4,  # 40% of walls are destructible
    seed: int | None = None,
) -> dict:
    """Generate terrain compatible with Rust TerrainGrid.
    
    GUARANTEES:
    1. Spawn zones (left-center, right-center) always clear
    2. BFS-verified connectivity between spawn zones
    3. If disconnected, horizontal corridor carved
    4. Mixed permanent (60%) and destructible (40%) walls
    """
```

### 4. Create `curriculum.py`

2-stage SB3 callback:

```python
class CurriculumCallback(BaseCallback):
    """Stage 1→2 promotion when mean_reward > threshold."""
    
    def __init__(self, stage1_threshold=0.3, window=50):
        ...
    
    def _promote_to_stage2(self):
        """Enable terrain randomization and full action space."""
        for env in self.training_env.envs:
            env.unwrapped.curriculum_stage = 2
```

### 5. Create `train.py`

CLI entry point using `MaskablePPO`:

```python
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=100_000)
    parser.add_argument("--max-steps", type=int, default=200)
    parser.add_argument("--checkpoint-dir", default="./checkpoints")
    parser.add_argument("--curriculum", action="store_true")
    args = parser.parse_args()
    
    env = SwarmEnv(config={"max_steps": args.max_steps})
    env = ActionMasker(env, lambda e: e.action_masks())
    
    model = MaskablePPO(
        "MlpPolicy",  # or "MultiInputPolicy" if using Dict obs
        env,
        verbose=1,
        tensorboard_log="./tb_logs/",
    )
    
    callbacks = [CheckpointCallback(...)]
    if args.curriculum:
        callbacks.append(CurriculumCallback())
    
    model.learn(total_timesteps=args.timesteps, callback=callbacks)
```

### 6. Create `callbacks.py`

TensorBoard logging + checkpoint callbacks.

## Key Decisions
- **MaskablePPO** from `sb3-contrib` (NOT regular PPO)
- **MaskableMultiInputPolicy** for Dict observation space
- **Stage 1:** Actions 0-3 only (flat terrain)
- **Stage 2:** All 8 actions (procedural terrain)
- **Heuristic Bot:** Faction 1 = existing Rust behavior (no new code)

## Verification_Strategy
```
Test_Type: unit + integration
Test_Stack: pytest (Python)
Acceptance_Criteria:
  - terrain_generator produces correct dimensions
  - terrain_generator spawn zones are always clear
  - terrain_generator BFS connectivity guaranteed
  - terrain_generator deterministic with same seed
  - terrain_generator produces both permanent and destructible walls
  - train.py runs without import errors
  - MaskablePPO initializes with correct policy
  - action_masks returns correct shape and values per stage
  - CurriculumCallback promotes at threshold
  - ResetEnvironment sent correctly in reset()
  - Can run 100 timesteps without crash (with mock ZMQ)
Suggested_Test_Commands:
  - "cd macro-brain && python -m pytest tests/test_terrain_generator.py -v"
  - "cd macro-brain && python -m pytest tests/test_training.py -v"
```
