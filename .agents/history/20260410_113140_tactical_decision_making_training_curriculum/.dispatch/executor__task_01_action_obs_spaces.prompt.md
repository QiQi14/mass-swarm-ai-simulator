# AGENT ROLE: EXECUTION SPECIALIST

You are an **Execution Specialist** in a multi-agent DAG workflow.
You have been assigned ONE specific task. You implement it with surgical precision.

---

## Your Assignment

| Field   | Value |
|---------|-------|
| Task ID | `task_01_action_obs_spaces` |
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

1. **Create** `tasks_pending/task_01_action_obs_spaces_changelog.md`
2. **Include in the changelog:**
   - **Touched Files:** A bulleted list of every file you created or modified.
   - **Contract Fulfillment:** Brief confirmation of the interfaces/DTOs you implemented.
   - **Deviations/Notes:** Any edge cases you handled or deviations from the brief the QA agent should verify.
3. **Then and only then** run:
   ```bash
   ./task_tool.sh done task_01_action_obs_spaces
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

- `./.agents/context/architecture.md`
- `./.agents/context/ipc-protocol.md`

---

## Task Brief

# Task 01: Action & Observation Space Refactor

```yaml
Task_ID: task_01_action_obs_spaces
Execution_Phase: 1
Model_Tier: standard
Dependencies: []
Target_Files:
  - macro-brain/src/env/spaces.py
Context_Bindings:
  - context/architecture
  - context/ipc-protocol
```

## Objective

Refactor `spaces.py` to define the new MultiDiscrete action space and 8-channel observation space for the tactical curriculum.

## Strict Instructions

### 1. Action Space: `MultiDiscrete([8, 2500])`

Replace `make_action_space()`:

```python
def make_action_space(num_actions: int = 8, max_grid_cells: int = 2500) -> spaces.MultiDiscrete:
    """Create MultiDiscrete action space: [action_type, flat_spatial_coord].
    
    Component 0: Action type (8 discrete actions)
    Component 1: Flattened grid coordinate (50×50 = 2500 cells)
        Decode: grid_x = val % 50, grid_y = val // 50
    """
    return spaces.MultiDiscrete([num_actions, max_grid_cells])
```

### 2. Observation Space: 8 grids (50×50) + 12-dim summary

Replace `make_observation_space()`:

```python
def make_observation_space(
    grid_width: int = 50,
    grid_height: int = 50,
) -> spaces.Dict:
    """Fixed 50×50 observation space. 8 grid channels + 12-dim summary.
    
    Channels:
      ch0: brain density
      ch1: enemy faction 1 density (fog-gated + LKP)
      ch2: enemy faction 2 density (fog-gated + LKP)
      ch3: sub-factions aggregated
      ch4: terrain (0=pass, 1=wall; padding=1.0)
      ch5: fog explored (0=unexplored, 1=explored; padding=1.0)
      ch6: fog visible (0=hidden, 1=visible; padding=1.0)
      ch7: threat density (weighted enemy density)
    """
    obs = {}
    for ch in range(8):
        obs[f"ch{ch}"] = spaces.Box(
            0.0, 1.0, shape=(grid_height, grid_width), dtype=np.float32
        )
    obs["summary"] = spaces.Box(0.0, 1.0, shape=(12,), dtype=np.float32)
    return spaces.Dict(obs)
```

### 3. Update Constants

Remove the old action index constants (ACTION_IDLE, ACTION_HOLD, etc.) and the Stage 1 constants. Replace with:

```python
# 8-action vocabulary for tactical curriculum
ACTION_HOLD = 0
ACTION_ATTACK_COORD = 1
ACTION_DROP_PHEROMONE = 2
ACTION_DROP_REPELLENT = 3
ACTION_SPLIT_TO_COORD = 4
ACTION_MERGE_BACK = 5
ACTION_RETREAT = 6
ACTION_LURE = 7

ACTION_NAMES = [
    "Hold", "AttackCoord", "DropPheromone", "DropRepellent",
    "SplitToCoord", "MergeBack", "Retreat", "Lure",
]

# Which actions use spatial coordinates (component 1)
SPATIAL_ACTIONS = {
    ACTION_ATTACK_COORD, ACTION_DROP_PHEROMONE, ACTION_DROP_REPELLENT,
    ACTION_SPLIT_TO_COORD, ACTION_RETREAT, ACTION_LURE,
}

# Grid constants — observation always 50×50 regardless of map size
MAX_GRID_WIDTH = 50
MAX_GRID_HEIGHT = 50
MAX_GRID_CELLS = MAX_GRID_WIDTH * MAX_GRID_HEIGHT  # 2500
NUM_CHANNELS = 8
SUMMARY_DIM = 12
```

### 4. Add Coordinate Helpers

```python
def decode_spatial(flat_index: int, grid_width: int = MAX_GRID_WIDTH) -> tuple[int, int]:
    """Decode flattened spatial coordinate to (grid_x, grid_y)."""
    grid_x = flat_index % grid_width
    grid_y = flat_index // grid_width
    return grid_x, grid_y

def grid_to_world(grid_x: int, grid_y: int, cell_size: float = 20.0,
                  offset_x: float = 0.0, offset_y: float = 0.0) -> tuple[float, float]:
    """Convert grid cell to world coordinates (cell center).
    
    offset_x/y: padding offset for center-padded maps.
    """
    world_x = (grid_x - offset_x) * cell_size + cell_size / 2.0
    world_y = (grid_y - offset_y) * cell_size + cell_size / 2.0
    return world_x, world_y

def make_coordinate_mask(
    active_grid_w: int, active_grid_h: int,
    max_grid_w: int = MAX_GRID_WIDTH, max_grid_h: int = MAX_GRID_HEIGHT,
) -> np.ndarray:
    """Create coordinate mask for the active arena within the padded tensor.
    
    Active arena is centered in the max grid. Only active cells are True.
    """
    mask = np.zeros(max_grid_w * max_grid_h, dtype=bool)
    pad_x = (max_grid_w - active_grid_w) // 2
    pad_y = (max_grid_h - active_grid_h) // 2
    for gy in range(active_grid_h):
        row = pad_y + gy
        start = row * max_grid_w + pad_x
        mask[start : start + active_grid_w] = True
    return mask
```

### 5. Remove old `make_action_names()` 

Replace it with a simpler version that uses the new `ACTION_NAMES` list:

```python
def make_action_names() -> dict[int, str]:
    return {i: name for i, name in enumerate(ACTION_NAMES)}
```

### 6. Preserve all docstrings

Keep the module-level docstring but update it to describe the new tactical curriculum spaces. Remove references to "Stage 1 action constants" and the old 9-action default names dict.

## Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: unit
  Test_Stack: pytest (macro-brain)
  Acceptance_Criteria:
    - "make_action_space() returns MultiDiscrete with nvec=[8, 2500]"
    - "make_observation_space() returns Dict with 8 Box(50,50) + 1 Box(12)"
    - "decode_spatial(125) returns (25, 2) for grid_width=50"
    - "decode_spatial(0) returns (0, 0)"
    - "decode_spatial(2499) returns (49, 49)"
    - "make_coordinate_mask(25, 25) has exactly 625 True entries centered"
    - "grid_to_world(0, 0, cell_size=20) returns (10.0, 10.0)"
    - "SPATIAL_ACTIONS contains exactly actions 1,2,3,4,6,7"
  Suggested_Test_Commands:
    - "cd macro-brain && python -m pytest tests/test_spaces.py -v"
```

---

## Shared Contracts

_See `implementation_plan.md` for full contract definitions._

