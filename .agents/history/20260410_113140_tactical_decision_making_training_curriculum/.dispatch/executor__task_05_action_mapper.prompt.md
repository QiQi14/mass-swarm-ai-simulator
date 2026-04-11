# AGENT ROLE: EXECUTION SPECIALIST

You are an **Execution Specialist** in a multi-agent DAG workflow.
You have been assigned ONE specific task. You implement it with surgical precision.

---

## Your Assignment

| Field   | Value |
|---------|-------|
| Task ID | `task_05_action_mapper` |
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

1. **Create** `tasks_pending/task_05_action_mapper_changelog.md`
2. **Include in the changelog:**
   - **Touched Files:** A bulleted list of every file you created or modified.
   - **Contract Fulfillment:** Brief confirmation of the interfaces/DTOs you implemented.
   - **Deviations/Notes:** Any edge cases you handled or deviations from the brief the QA agent should verify.
3. **Then and only then** run:
   ```bash
   ./task_tool.sh done task_05_action_mapper
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

- `./.agents/context/ipc-protocol.md`
- `./.agents/context/conventions.md`

---

## Task Brief

# Task 05: MultiDiscrete Action-to-Directive Mapper

```yaml
Task_ID: task_05_action_mapper
Execution_Phase: 2
Model_Tier: standard
Dependencies:
  - task_01_action_obs_spaces
Target_Files:
  - macro-brain/src/env/actions.py
Context_Bindings:
  - context/ipc-protocol
  - context/conventions
```

## Objective

Rewrite `actions.py` to map MultiDiscrete `[action_type, flat_coord]` outputs to MacroDirective JSON dicts. The function must decode the flattened spatial coordinate and ignore coordinates for non-spatial actions.

## Strict Instructions

### 1. Replace the module content

Keep existing directive builder functions (`build_hold_directive`, `build_update_nav_directive`, etc.) — they are still the low-level builders. Add a new top-level dispatcher.

### 2. Implement `multidiscrete_to_directives`

```python
from src.env.spaces import (
    ACTION_HOLD, ACTION_ATTACK_COORD, ACTION_DROP_PHEROMONE,
    ACTION_DROP_REPELLENT, ACTION_SPLIT_TO_COORD, ACTION_MERGE_BACK,
    ACTION_RETREAT, ACTION_LURE, SPATIAL_ACTIONS,
    decode_spatial, grid_to_world, MAX_GRID_WIDTH,
)


def multidiscrete_to_directives(
    action: np.ndarray,
    brain_faction: int,
    active_sub_factions: list[int],
    cell_size: float = 20.0,
    pad_offset_x: float = 0.0,
    pad_offset_y: float = 0.0,
    split_percentage: float = 0.30,
    lure_percentage: float = 0.15,
    lure_target_faction: int | None = None,
    lure_patrol_faction: int | None = None,
) -> list[dict]:
    """Map MultiDiscrete [action_type, flat_coord] to directive list.
    
    Args:
        action: numpy array of shape (2,) — [action_idx, flat_coord].
        brain_faction: Brain faction ID.
        active_sub_factions: Currently active sub-faction IDs.
        cell_size: World units per grid cell.
        pad_offset_x: Grid padding offset X (for center-padded maps).
        pad_offset_y: Grid padding offset Y.
        split_percentage: Fraction of swarm to split off (SplitToCoord).
        lure_percentage: Fraction of swarm for lure group.
        lure_target_faction: Faction ID of the target (HVT) for aggro mask.
        lure_patrol_faction: Faction ID of the patrol for aggro mask.
    
    Returns:
        List of MacroDirective dicts ready for ZMQ batch payload.
    """
    action_type = int(action[0])
    flat_coord = int(action[1])
    
    # Decode spatial coordinate (ignored for non-spatial actions)
    grid_x, grid_y = decode_spatial(flat_coord, MAX_GRID_WIDTH)
    world_x, world_y = grid_to_world(grid_x, grid_y, cell_size, pad_offset_x, pad_offset_y)
    
    directives = []
    
    if action_type == ACTION_HOLD:
        # Non-spatial: ignore coordinate
        directives.append(build_hold_directive(brain_faction))
    
    elif action_type == ACTION_ATTACK_COORD:
        directives.append(build_update_nav_directive(
            brain_faction,
            target_waypoint=(world_x, world_y),
        ))
    
    elif action_type == ACTION_DROP_PHEROMONE:
        directives.append(build_set_zone_modifier_directive(
            brain_faction, world_x, world_y,
            radius=100.0, cost_modifier=-50.0,
        ))
    
    elif action_type == ACTION_DROP_REPELLENT:
        directives.append(build_set_zone_modifier_directive(
            brain_faction, world_x, world_y,
            radius=100.0, cost_modifier=50.0,
        ))
    
    elif action_type == ACTION_SPLIT_TO_COORD:
        # Allocate next sub-faction ID
        next_sub = _next_sub_faction_id(brain_faction, active_sub_factions)
        directives.append(build_split_faction_directive(
            brain_faction, next_sub, split_percentage,
            epicenter=[world_x, world_y],
        ))
        # Navigate the new sub-faction to the target coord
        directives.append(build_update_nav_directive(
            next_sub,
            target_waypoint=(world_x, world_y),
        ))
    
    elif action_type == ACTION_MERGE_BACK:
        # Non-spatial: merge first active sub-faction back
        if active_sub_factions:
            directives.append(build_merge_faction_directive(
                active_sub_factions[0], brain_faction,
            ))
        else:
            directives.append(build_hold_directive(brain_faction))
    
    elif action_type == ACTION_RETREAT:
        directives.append(build_retreat_directive(
            brain_faction, world_x, world_y,
        ))
    
    elif action_type == ACTION_LURE:
        # Split a small lure group
        lure_sub = _next_sub_faction_id(brain_faction, active_sub_factions)
        directives.append(build_split_faction_directive(
            brain_faction, lure_sub, lure_percentage,
            epicenter=[world_x, world_y],
        ))
        # Navigate lure away from target
        directives.append(build_update_nav_directive(
            lure_sub,
            target_waypoint=(world_x, world_y),
        ))
        # Set aggro mask: lure fights patrol, ignores target
        if lure_patrol_faction is not None:
            directives.append(build_set_aggro_mask_directive(
                lure_sub, lure_patrol_faction, allow_combat=True,
            ))
        if lure_target_faction is not None:
            directives.append(build_set_aggro_mask_directive(
                lure_sub, lure_target_faction, allow_combat=False,
            ))
    
    else:
        directives.append(build_hold_directive(brain_faction))
    
    return directives


def _next_sub_faction_id(brain_faction: int, active_subs: list[int]) -> int:
    """Allocate next available sub-faction ID.
    
    Convention: sub-factions use brain_faction * 100 + offset.
    E.g., brain=0 → subs are 100, 101, 102...
    """
    base = (brain_faction + 1) * 100
    for offset in range(100):
        candidate = base + offset
        if candidate not in active_subs:
            return candidate
    return base + len(active_subs)
```

### 3. Update `build_update_nav_directive` for waypoint support

Add an alternative signature that accepts a waypoint tuple:

```python
def build_update_nav_directive(
    follower_faction: int,
    enemy_faction: int | None = None,
    target_waypoint: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """Build UpdateNavigation directive.
    
    Accepts either enemy_faction (Faction target) or target_waypoint (Waypoint target).
    """
    if target_waypoint is not None:
        target = {"type": "Waypoint", "x": target_waypoint[0], "y": target_waypoint[1]}
    else:
        target = {"type": "Faction", "faction_id": enemy_faction}
    return {
        "type": "macro_directive",
        "directive": "UpdateNavigation",
        "follower_faction": follower_faction,
        "target": target,
    }
```

### 4. Keep all existing builder functions

Do NOT delete: `build_idle_directive`, `build_hold_directive`, `build_activate_buff_directive`, `build_retreat_directive`, `build_set_zone_modifier_directive`, `build_split_faction_directive`, `build_merge_faction_directive`, `build_set_aggro_mask_directive`. They are used by the bot controller and other systems.

## Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: unit
  Test_Stack: pytest (macro-brain)
  Acceptance_Criteria:
    - "Hold action ignores coordinate, returns Hold directive"
    - "AttackCoord returns UpdateNav with Waypoint target at correct world coords"
    - "DropPheromone returns SetZoneModifier with cost=-50"
    - "DropRepellent returns SetZoneModifier with cost=+50"
    - "SplitToCoord returns 2 directives: SplitFaction + UpdateNav for sub"
    - "MergeBack with active subs returns MergeFaction directive"
    - "MergeBack with NO subs returns Hold (fallback)"
    - "Lure returns SplitFaction + UpdateNav + SetAggroMask directives"
    - "_next_sub_faction_id avoids collisions with active subs"
    - "Coordinate decode: flat_coord=125 → grid(25,2) → world(510, 50) with cell_size=20"
  Suggested_Test_Commands:
    - "cd macro-brain && python -m pytest tests/test_actions.py -v"
```

---

## Shared Contracts

_See `implementation_plan.md` for full contract definitions._

