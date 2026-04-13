from typing import Any
from dataclasses import asdict
import numpy as np
from src.config.definitions import ActivateBuffDef
from src.env.spaces import (
    ACTION_HOLD, ACTION_ATTACK_COORD, ACTION_DROP_PHEROMONE,
    ACTION_DROP_REPELLENT, ACTION_SPLIT_TO_COORD, ACTION_MERGE_BACK,
    ACTION_RETREAT, ACTION_SCOUT, SPATIAL_ACTIONS,
    decode_spatial, grid_to_world, MAX_GRID_WIDTH,
)

def build_idle_directive() -> dict[str, Any]:
    return {"type": "macro_directive", "directive": "Idle"}

def build_hold_directive(faction: int) -> dict[str, Any]:
    return {"type": "macro_directive", "directive": "Hold", "faction_id": faction}

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

def build_activate_buff_directive(faction: int, activate_buff: ActivateBuffDef) -> dict[str, Any]:
    return {
        "type": "macro_directive",
        "directive": "ActivateBuff",
        "faction": faction,
        "modifiers": [asdict(m) for m in activate_buff.modifiers],
        "duration_ticks": activate_buff.duration_ticks,
        "targets": [],
    }

def build_retreat_directive(faction: int, retreat_x: float, retreat_y: float) -> dict[str, Any]:
    return {
        "type": "macro_directive",
        "directive": "Retreat",
        "faction": faction,
        "retreat_x": float(retreat_x),
        "retreat_y": float(retreat_y),
    }

def build_set_zone_modifier_directive(faction: int, x: float, y: float, radius: float = 100.0, cost_modifier: float = -50.0) -> dict[str, Any]:
    return {
        "type": "macro_directive",
        "directive": "SetZoneModifier",
        "target_faction": faction,
        "x": float(x),
        "y": float(y),
        "radius": float(radius),
        "cost_modifier": float(cost_modifier),
    }

def build_split_faction_directive(source_faction: int, new_sub_faction: int, percentage: float, epicenter: list[float]) -> dict[str, Any]:
    return {
        "type": "macro_directive",
        "directive": "SplitFaction",
        "source_faction": source_faction,
        "new_sub_faction": new_sub_faction,
        "percentage": percentage,
        "epicenter": epicenter,
    }

def build_merge_faction_directive(source_faction: int, target_faction: int) -> dict[str, Any]:
    return {
        "type": "macro_directive",
        "directive": "MergeFaction",
        "source_faction": source_faction,
        "target_faction": target_faction,
    }

def build_set_aggro_mask_directive(source_faction: int, target_faction: int, allow_combat: bool) -> dict[str, Any]:
    return {
        "type": "macro_directive",
        "directive": "SetAggroMask",
        "source_faction": source_faction,
        "target_faction": target_faction,
        "allow_combat": allow_combat,
    }


def multidiscrete_to_directives(
    action: np.ndarray,
    brain_faction: int,
    active_sub_factions: list[int],
    cell_size: float = 20.0,
    pad_offset_x: float = 0.0,
    pad_offset_y: float = 0.0,
    split_percentage: float = 0.30,
    scout_percentage: float = 0.10,
    last_nav_directive: dict | None = None,
) -> tuple[list[dict], dict | None]:
    """Map MultiDiscrete [action_type, flat_coord] to directive list.
    
    Args:
        action: numpy array of shape (2,) — [action_idx, flat_coord].
        brain_faction: Brain faction ID.
        active_sub_factions: Currently active sub-faction IDs.
        cell_size: World units per grid cell.
        pad_offset_x: Grid padding offset X (for center-padded maps).
        pad_offset_y: Grid padding offset Y.
        split_percentage: Fraction of swarm to split off (SplitToCoord).
        scout_percentage: Fraction of swarm for scout group.
        last_nav_directive: Cached last AttackCoord/Retreat directive for replay.
    
    Returns:
        Tuple of (directives, updated_last_nav_directive).
        The caller caches the second element for the next step.
    """
    action_type = int(action[0])
    flat_coord = int(action[1])
    
    # Decode spatial coordinate (ignored for non-spatial actions)
    grid_x, grid_y = decode_spatial(flat_coord, MAX_GRID_WIDTH)
    world_x, world_y = grid_to_world(grid_x, grid_y, cell_size, pad_offset_x, pad_offset_y)
    
    directives = []
    updated_nav = last_nav_directive  # default: no change
    
    if action_type == ACTION_HOLD:
        # Non-spatial: ignore coordinate
        directives.append(build_hold_directive(brain_faction))
        updated_nav = None  # Clear cache — Hold means stop
    
    elif action_type == ACTION_ATTACK_COORD:
        nav = build_update_nav_directive(
            brain_faction,
            target_waypoint=(world_x, world_y),
        )
        directives.append(nav)
        updated_nav = nav
    
    elif action_type == ACTION_DROP_PHEROMONE:
        directives.append(build_set_zone_modifier_directive(
            brain_faction, world_x, world_y,
            radius=100.0, cost_modifier=-50.0,
        ))
        # Replay last navigation so the swarm keeps moving
        if last_nav_directive is not None:
            directives.append(last_nav_directive)
    
    elif action_type == ACTION_DROP_REPELLENT:
        directives.append(build_set_zone_modifier_directive(
            brain_faction, world_x, world_y,
            radius=100.0, cost_modifier=200.0,  # +200 per conventions.md
        ))
        # Replay last navigation so the swarm keeps moving
        if last_nav_directive is not None:
            directives.append(last_nav_directive)
    
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
        nav = build_retreat_directive(
            brain_faction, world_x, world_y,
        )
        directives.append(nav)
        updated_nav = nav
    
    elif action_type == ACTION_SCOUT:
        # Scout: split a small recon group and send to target coordinate.
        # Atomic primitive — just split + navigate, no aggro mask manipulation.
        # The model learns to combine Scout + AttackCoord + Retreat for tactics.
        scout_sub = _next_sub_faction_id(brain_faction, active_sub_factions)
        directives.append(build_split_faction_directive(
            brain_faction, scout_sub, scout_percentage,
            epicenter=[world_x, world_y],
        ))
        # Navigate scout group to target coord for vision
        directives.append(build_update_nav_directive(
            scout_sub,
            target_waypoint=(world_x, world_y),
        ))
    
    else:
        directives.append(build_hold_directive(brain_faction))
    
    return directives, updated_nav


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
