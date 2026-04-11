# AGENT ROLE: EXECUTION SPECIALIST

You are an **Execution Specialist** in a multi-agent DAG workflow.
You have been assigned ONE specific task. You implement it with surgical precision.

---

## Your Assignment

| Field   | Value |
|---------|-------|
| Task ID | `task_06_swarm_env_refactor` |
| Feature | Tactical Decision-Making Training Curriculum |
| Tier    | advanced |

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

1. **Create** `tasks_pending/task_06_swarm_env_refactor_changelog.md`
2. **Include in the changelog:**
   - **Touched Files:** A bulleted list of every file you created or modified.
   - **Contract Fulfillment:** Brief confirmation of the interfaces/DTOs you implemented.
   - **Deviations/Notes:** Any edge cases you handled or deviations from the brief the QA agent should verify.
3. **Then and only then** run:
   ```bash
   ./task_tool.sh done task_06_swarm_env_refactor
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
- `./.agents/context/conventions.md`

---

## Task Brief

# Task 06: SwarmEnv Full Refactor

```yaml
Task_ID: task_06_swarm_env_refactor
Execution_Phase: 3
Model_Tier: advanced
Dependencies:
  - task_01_action_obs_spaces
  - task_02_reward_components
  - task_03_vectorizer_lkp
  - task_04_rust_fog_zmq
  - task_05_action_mapper
  - task_07_curriculum_stages
Target_Files:
  - macro-brain/src/env/swarm_env.py
Context_Bindings:
  - context/architecture
  - context/ipc-protocol
  - context/conventions
```

## Objective

Full refactor of `SwarmEnv` for the tactical curriculum: MultiDiscrete action space, LKP-integrated observation, center-padding, stage-aware masking, fog of war, lure/flank tracking, and patrol speed debuff.

## Strict Instructions

### 1. Update `__init__`

- Import new spaces: `from src.env.spaces import make_observation_space, make_action_space, MAX_GRID_WIDTH, MAX_GRID_HEIGHT, MAX_GRID_CELLS, SPATIAL_ACTIONS, ACTION_NAMES, make_coordinate_mask`
- Import LKP: `from src.utils.lkp_buffer import LKPBuffer`
- Import action mapper: `from src.env.actions import multidiscrete_to_directives`
- Action space: `self.action_space = make_action_space(num_actions=8, max_grid_cells=MAX_GRID_CELLS)`
- Observation space: `self.observation_space = make_observation_space()`
- Add `self._lkp_buffer = LKPBuffer(grid_h=MAX_GRID_HEIGHT, grid_w=MAX_GRID_WIDTH)`
- Add `self._prev_fog_explored: np.ndarray | None = None`
- Add stage-derived map config: `self._active_grid_w`, `self._active_grid_h`, `self._pad_offset_x`, `self._pad_offset_y`, `self._cell_size`, `self._fog_enabled`
- Add lure tracking: `self._lure_faction_id: int | None = None`, `self._lure_success: bool = False`

### 2. Update `action_masks()`

Return flattened mask for both components:

```python
def action_masks(self) -> np.ndarray:
    # Action type mask
    act_mask = np.ones(8, dtype=bool)
    
    if not self._active_sub_factions:
        act_mask[5] = False  # MergeBack
    if len(self._active_sub_factions) >= 2:
        act_mask[4] = False  # SplitToCoord
        act_mask[7] = False  # Lure
    
    # Stage-based action unlocking
    stage_config = self._get_stage_action_unlock()
    for i in range(8):
        if not stage_config[i]:
            act_mask[i] = False
    
    # Coordinate mask (only active arena cells)
    coord_mask = make_coordinate_mask(
        self._active_grid_w, self._active_grid_h,
        MAX_GRID_WIDTH, MAX_GRID_HEIGHT,
    )
    
    return np.concatenate([act_mask, coord_mask])
```

### 3. Update `reset()`

- Reset LKP buffer: `self._lkp_buffer.reset()`
- Reset fog state: `self._prev_fog_explored = None`
- Reset lure state: `self._lure_faction_id = None`, `self._lure_success = False`
- Load stage map config from curriculum (active grid size, cell size, fog toggle)
- Calculate padding offsets: `self._pad_offset_x = (MAX_GRID_WIDTH - active_grid_w) // 2`
- Pass fog toggle and appropriate spawns from `get_spawns_for_stage`

### 4. Update `step(action)`

- `action` is now `np.ndarray` of shape `(2,)` — `[action_type, flat_coord]`
- Call `multidiscrete_to_directives(action, ...)` instead of `_action_to_directive`
- Pass `fog_enabled`, `lkp_buffer`, `active_grid_w/h`, `pad_offset` to vectorizer
- Compute flanking score if sub-factions exist
- Detect lure success condition
- Pass all tactical signals to `compute_shaped_reward`
- Store `self._prev_fog_explored` for next step's exploration reward

### 5. Stage Action Unlock

```python
def _get_stage_action_unlock(self) -> list[bool]:
    """Which actions are unlocked at the current curriculum stage.
    
    Stage 1-3: Hold(0), AttackCoord(1)
    Stage 4:   +DropPheromone(2), +DropRepellent(3)  
    Stage 5:   +SplitToCoord(4), +MergeBack(5)
    Stage 6+:  +Retreat(6), +Lure(7) — all 8
    """
    s = self.curriculum_stage
    unlock = [True, True, False, False, False, False, False, False]
    if s >= 4:
        unlock[2] = unlock[3] = True
    if s >= 5:
        unlock[4] = unlock[5] = True
    if s >= 6:
        unlock[6] = unlock[7] = True
    return unlock
```

### 6. Lure Success Detection

```python
def _check_lure_success(self, snapshot: dict) -> bool:
    """Lure succeeds when HVT killed while patrol is >200 units away from HVT."""
    if self._lure_success:
        return True  # Already triggered
    if not self._lure_faction_id:
        return False
    
    target_count = self._get_faction_count(snapshot, self._target_faction)
    if target_count > 0:
        return False  # Target still alive
    
    # Check patrol distance from target spawn
    patrol_c = self._get_density_centroid(snapshot, self._trap_faction)
    target_spawn = self._target_spawn_pos
    if patrol_c is None or target_spawn is None:
        return False
    
    dist = ((patrol_c[0] - target_spawn[0])**2 + (patrol_c[1] - target_spawn[1])**2)**0.5
    return dist > 200.0
```

### 7. Remove old `_action_to_directive` method

Delete the old method entirely. Replace with call to `multidiscrete_to_directives`.

### 8. Remove old `_compute_approach_reward` method

The approach reward is now in `rewards.py` and called via `compute_shaped_reward`.

## Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: integration
  Test_Stack: pytest (macro-brain) + manual smoke
  Acceptance_Criteria:
    - "action_masks() returns array of length 8 + 2500 = 2508"
    - "action_masks() blocks MergeBack when no sub-factions"
    - "action_masks() blocks Split/Lure when >= 2 sub-factions"
    - "action_masks() blocks stage-locked actions correctly"
    - "Coordinate mask has correct number of active cells per stage"
    - "step() accepts np.array([action_type, flat_coord]) without crash"
    - "Fog-enabled stages produce LKP-processed observations"
    - "Lure success detects patrol distance > 200 from target"
    - "Reset clears LKP buffer and resets all tracking state"
    - "Observation dict has 8 ch* keys of shape (50,50) and summary of shape (12,)"
  Suggested_Test_Commands:
    - "cd macro-brain && python -m pytest tests/test_swarm_env.py -v"
```

---

## Shared Contracts

_See `implementation_plan.md` for full contract definitions._

