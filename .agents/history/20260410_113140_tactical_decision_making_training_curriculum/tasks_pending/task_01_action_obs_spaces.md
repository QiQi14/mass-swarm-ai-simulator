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
