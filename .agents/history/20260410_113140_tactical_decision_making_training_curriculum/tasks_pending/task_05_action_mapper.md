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
