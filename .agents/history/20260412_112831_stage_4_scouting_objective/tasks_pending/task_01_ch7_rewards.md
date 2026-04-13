---
Task_ID: "task_01_ch7_rewards"
Execution_Phase: 1
Model_Tier: "standard"
Target_Files:
  - "macro-brain/src/utils/vectorizer.py"
  - "macro-brain/src/env/rewards.py"
Dependencies: []
Context_Bindings:
  - "context/training-curriculum"
  - "context/engine-mechanics"
Strict_Instructions: |
  1. In `macro-brain/src/utils/vectorizer.py`:
     - Update the `vectorize_snapshot` signature to add: `active_objective_ping: tuple[float, float] | None = None` and `ping_intensity: float = 1.0`.
     - Update the 'ch7: System objective signal' section. Currently it is a placeholder. Replace it to:
       ```python
       if active_objective_ping is not None:
           px, py = active_objective_ping
           grid_x = int(px / cell_size) + pad_x
           grid_y = int(py / cell_size) + pad_y
           
           for dy in range(-2, 3):
               for dx in range(-2, 3):
                   gx, gy = grid_x + dx, grid_y + dy
                   if 0 <= gx < MAX_GRID and 0 <= gy < MAX_GRID:
                       dist = (dx**2 + dy**2)**0.5
                       val = max(0.0, ping_intensity - dist / 3.0)
                       channels[7][gy, gx] = max(channels[7][gy, gx], val)
       ```
  2. In `macro-brain/src/env/rewards.py`:
     - Under '5. EXPLORATION', change `if stage in (2, 7, 8)` to `if stage in (2, 4, 7, 8)`.
     - In `compute_shaped_reward`, under the `2. COMBAT TRADING (Aggression Incentive)` section block, right after `enemies_killed` and `own_lost` are defined with `max(0, ...)`, inject the following:
       ```python
       if stage == 4:
           own_lost = 0  # Eliminate the dead penalty for Stage 4
       ```
       This must happen before the `reward += own_lost * reward_weights.death_penalty` calculation.
Verification_Strategy:
  Test_Type: "unit"
  Test_Stack: "pytest"
  Acceptance_Criteria:
    - "vectorize_snapshot completes without errors when active_objective_ping is passed"
    - "rewards.py ignores own_lost penalty when stage == 4"
  Suggested_Test_Commands:
    - "cd macro-brain && python -m pytest tests/"
Live_System_Impact: "additive"
---
