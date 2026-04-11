# AGENT ROLE: EXECUTION SPECIALIST

You are an **Execution Specialist** in a multi-agent DAG workflow.
You have been assigned ONE specific task. You implement it with surgical precision.

---

## Your Assignment

| Field   | Value |
|---------|-------|
| Task ID | `task_09_feature_extractor_train` |
| Feature | Tactical Decision-Making Training Curriculum |
| Tier    | standard |

---

## ⛔ MANDATORY PROCESS — ALL TIERS (DO NOT SKIP)

> **These rules apply to EVERY executor, regardless of tier. Violating them
> causes an automatic QA FAIL and project BLOCK.**

### Rule 1: Scope Isolation
- You may ONLY create or modify files listed in `Target_Files` in your Task Brief.
- If a file must be changed but is NOT in `Target_Files`, **STOP and report the gap** — do NOT modify it.
- NEVER edit `task_state.json`, `implementation_plan.md`, or any file outside your scope.

### Rule 2: Changelog (Handoff Documentation)
After ALL code is written and BEFORE calling `./task_tool.sh done`, you MUST:

1. **Create** `tasks_pending/task_09_feature_extractor_train_changelog.md`
2. **Include in the changelog:**
   - **Touched Files:** A bulleted list of every file you created or modified.
   - **Contract Fulfillment:** Brief confirmation of the interfaces/DTOs you implemented.
   - **Deviations/Notes:** Any edge cases you handled or deviations from the brief the QA agent should verify.
3. **Then and only then** run:
   ```bash
   ./task_tool.sh done task_09_feature_extractor_train
   ```

> **⚠️ Calling `./task_tool.sh done` without creating the changelog file is FORBIDDEN.**

### Rule 3: No Placeholders
- Do not use `// TODO`, `/* FIXME */`, or stub implementations.
- Output fully functional, production-ready code.

### Rule 4: Human Intervention Protocol
During execution, a human may intercept your work and propose changes, provide code snippets, or redirect your approach. When this happens:

1. **ADOPT the concept, VERIFY the details.** Humans are exceptional at architectural vision but make detail mistakes (wrong API, typos, outdated syntax). Independently verify all human-provided code against the actual framework version and project contracts.
2. **TRACK every human intervention in the changelog.** Add a dedicated `## Human Interventions` section to your changelog documenting:
   - What the human proposed (1-2 sentence summary)
   - What you adopted vs. what you corrected
   - Any deviations from the original task brief caused by the intervention
3. **DO NOT silently incorporate changes.** The QA agent and Architect must be able to trace exactly what came from the spec vs. what came from a human mid-flight. Untracked changes are invisible to the verification pipeline.

---

## Context Loading (Tier-Dependent)

**If your tier is `standard` or `advanced`:**

> **CRITICAL FIRST STEP:** The Planner might omit critical skills or knowledge in your `Context_Bindings`. It is YOUR responsibility to self-heal missing context.
1. Read `.agents/skills/index.md` (Skills Catalog)
2. Read `.agents/knowledge/README.md` (Master Knowledge Index)
   *(If you discover a skill or knowledge domain relevant to your task that isn't in your `Context_Bindings`, **read it immediately** before starting.)*
3. Read `.agents/context.md` — Thin index pointing to context sub-files
4. Load ONLY the `context/*` sub-files listed in your `Context_Bindings` below
5. Scan `.agents/knowledge/` — Lessons from previous sessions relevant to your task
6. Read `.agents/workflows/execution-lifecycle.md` — Your 4-step execution loop
7. Read `.agents/rules/execution-boundary.md` — Scope and contract constraints

- `./.agents/context/tech-stack.md`
- `./.agents/context/conventions.md`

---

## Task Brief

# Task 09: Custom Feature Extractor & Train Script

```yaml
Task_ID: task_09_feature_extractor_train
Execution_Phase: 4
Model_Tier: standard
Dependencies:
  - task_06_swarm_env_refactor
Target_Files:
  - macro-brain/src/models/__init__.py  # NEW FILE (empty or with import)
  - macro-brain/src/models/feature_extractor.py  # NEW FILE
  - macro-brain/src/training/train.py
Context_Bindings:
  - context/tech-stack
  - context/conventions
```

## Objective

Create a custom `TacticalExtractor` (CNN for spatial grids + MLP for summary vector) and update the training script for MultiDiscrete MaskablePPO.

## Strict Instructions

### 1. Create `macro-brain/src/models/__init__.py`

```python
from src.models.feature_extractor import TacticalExtractor

__all__ = ["TacticalExtractor"]
```

### 2. Create `macro-brain/src/models/feature_extractor.py`

```python
"""Custom CNN+MLP feature extractor for tactical observations.

SB3's default CombinedExtractor cannot efficiently route our mixed Dict
observation space (8 × 50×50 grids + 12-dim summary). This custom extractor:
  1. Stacks 8 grid channels into (B, 8, 50, 50) tensor → CNN → 128-dim
  2. Passes 12-dim summary → MLP → 64-dim
  3. Concatenates → linear → features_dim

The combined embedding feeds into MaskablePPO's Actor and Critic heads.
"""

import torch
import torch.nn as nn
import gymnasium as gym
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor


class TacticalExtractor(BaseFeaturesExtractor):
    """CNN branch for spatial grids + MLP branch for summary."""
    
    def __init__(self, observation_space: gym.spaces.Dict, features_dim: int = 256):
        # Must call super with the final features_dim
        super().__init__(observation_space, features_dim)
        
        n_channels = 8  # ch0..ch7
        grid_h, grid_w = 50, 50
        
        # CNN branch: (B, 8, 50, 50) → 128-dim
        self.cnn = nn.Sequential(
            nn.Conv2d(n_channels, 32, kernel_size=5, stride=2, padding=2),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.Flatten(),
        )
        
        # Calculate CNN output size by forward pass with dummy input
        with torch.no_grad():
            dummy = torch.zeros(1, n_channels, grid_h, grid_w)
            cnn_out_size = self.cnn(dummy).shape[1]
        
        self.cnn_linear = nn.Sequential(
            nn.Linear(cnn_out_size, 128),
            nn.ReLU(),
        )
        
        # MLP branch: 12-dim summary → 64-dim
        summary_dim = observation_space["summary"].shape[0]  # 12
        self.mlp = nn.Sequential(
            nn.Linear(summary_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
        )
        
        # Combiner: 128 + 64 = 192 → features_dim
        self.combiner = nn.Sequential(
            nn.Linear(128 + 64, features_dim),
            nn.ReLU(),
        )
    
    def forward(self, observations: dict[str, torch.Tensor]) -> torch.Tensor:
        # Stack grid channels: (B, 8, 50, 50)
        grids = torch.stack(
            [observations[f"ch{i}"] for i in range(8)], dim=1
        )
        
        cnn_out = self.cnn_linear(self.cnn(grids))
        mlp_out = self.mlp(observations["summary"])
        
        combined = torch.cat([cnn_out, mlp_out], dim=1)
        return self.combiner(combined)
```

### 3. Update `macro-brain/src/training/train.py`

Key changes:

#### a. Import the extractor
```python
from src.models.feature_extractor import TacticalExtractor
```

#### b. Update `make_env` for new profile
```python
def make_env(profile, args):
    def _init():
        env_config = {
            "profile": profile,
            "curriculum_stage": 1,
        }
        env = SwarmEnv(config=env_config)
        env = ActionMasker(env, lambda e: e.action_masks())
        return env
    return _init
```

#### c. Update model creation with custom policy kwargs
```python
policy_kwargs = {
    "features_extractor_class": TacticalExtractor,
    "features_extractor_kwargs": {"features_dim": 256},
}

model = MaskablePPO(
    "MultiInputPolicy",
    vec_env,
    verbose=1,
    tensorboard_log=str(run.tensorboard_dir),
    policy_kwargs=policy_kwargs,
    learning_rate=3e-4,
    n_steps=2048,
    batch_size=64,
    n_epochs=10,
    gamma=0.99,
    gae_lambda=0.95,
    clip_range=0.2,
    ent_coef=0.01,
)
```

#### d. Update default profile path
```python
parser.add_argument("--profile", type=str,
    default="profiles/tactical_curriculum.json")
```

#### e. Update EpisodeLogCallback for 8 actions
```python
episode_logger = EpisodeLogCallback(
    log_path=str(run.episode_log_path),
    num_actions=8,  # was 3
)
```

## Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: unit
  Test_Stack: pytest (macro-brain)
  Acceptance_Criteria:
    - "TacticalExtractor forward pass with dummy Dict input produces (B, 256) tensor"
    - "TacticalExtractor handles 8 channels × 50×50 grids correctly"
    - "TacticalExtractor handles 12-dim summary correctly"
    - "CNN output size computed dynamically (no hardcoded magic numbers)"
    - "train.py creates MaskablePPO with MultiInputPolicy + TacticalExtractor"
    - "train.py default profile is tactical_curriculum.json"
    - "No import errors when running `python -c 'from src.models import TacticalExtractor'`"
  Suggested_Test_Commands:
    - "cd macro-brain && python -m pytest tests/test_feature_extractor.py -v"
    - "cd macro-brain && python -c 'from src.models import TacticalExtractor; print(\"OK\")'"
```

---

## Shared Contracts

_See `implementation_plan.md` for full contract definitions._

