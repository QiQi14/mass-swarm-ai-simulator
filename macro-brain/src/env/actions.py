from typing import Any
from dataclasses import asdict
import numpy as np
from src.config.definitions import ActivateBuffDef, SkillDef
from src.env.spaces import (
    ACTION_HOLD, ACTION_ATTACK_COORD, ACTION_ZONE_MODIFIER,
    ACTION_SPLIT_TO_COORD, ACTION_MERGE_BACK, ACTION_SET_PLAYSTYLE,
    ACTION_ACTIVATE_SKILL, ACTION_RETREAT, SPATIAL_ACTIONS,
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

def build_split_faction_directive(source_faction: int, new_sub_faction: int, percentage: float, epicenter: list[float], class_filter: int | None = None) -> dict[str, Any]:
    return {
        "type": "macro_directive",
        "directive": "SplitFaction",
        "source_faction": source_faction,
        "new_sub_faction": new_sub_faction,
        "percentage": percentage,
        "epicenter": epicenter,
        "class_filter": class_filter,
    }

def build_set_tactical_override_directive(faction: int, behavior: dict | None) -> dict[str, Any]:
    return {
        "type": "macro_directive",
        "directive": "SetTacticalOverride",
        "faction": faction,
        "behavior": behavior,
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

def build_retreat_directive(faction: int, retreat_x: float, retreat_y: float) -> dict[str, Any]:
    """Build Retreat directive — tactical withdrawal to coordinate.
    
    The Rust executor handles MacroDirective::Retreat, which sets a
    waypoint target pointing AWAY from the enemy. After the flow field
    fix, this routes around walls correctly.
    """
    return {
        "type": "macro_directive",
        "directive": "Retreat",
        "faction": faction,
        "retreat_x": float(retreat_x),
        "retreat_y": float(retreat_y),
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
    skills: list[SkillDef] | None = None,
    enemy_factions: list[int] | None = None,
    last_nav_directive: dict | None = None,
) -> tuple[list[dict], dict | None]:
    """Map MultiDiscrete [action_type, flat_coord, modifier] to directive list."""
    action_type = int(action[0])
    flat_coord = int(action[1])
    modifier = int(action[2]) if len(action) > 2 else 0
    
    grid_x, grid_y = decode_spatial(flat_coord, MAX_GRID_WIDTH)
    world_x, world_y = grid_to_world(grid_x, grid_y, cell_size, pad_offset_x, pad_offset_y)
    
    directives = []
    updated_nav = last_nav_directive
    
    if action_type == ACTION_HOLD:
        directives.append(build_hold_directive(brain_faction))
        updated_nav = None
        
    elif action_type == ACTION_ATTACK_COORD:
        nav = build_update_nav_directive(brain_faction, target_waypoint=(world_x, world_y))
        directives.append(nav)
        updated_nav = nav
        
    elif action_type == ACTION_ZONE_MODIFIER:
        if modifier == 0:
            directives.append(build_set_zone_modifier_directive(
                brain_faction, world_x, world_y, radius=100.0, cost_modifier=-50.0
            ))
        else: # modifier == 1
            directives.append(build_set_zone_modifier_directive(
                brain_faction, world_x, world_y, radius=100.0, cost_modifier=200.0
            ))
        if last_nav_directive is not None:
            directives.append(last_nav_directive)
            
    elif action_type == ACTION_SPLIT_TO_COORD:
        next_sub = _next_sub_faction_id(brain_faction, active_sub_factions)
        class_filter = None if modifier == 0 else modifier - 1
        directives.append(build_split_faction_directive(
            brain_faction, next_sub, split_percentage,
            epicenter=[world_x, world_y], class_filter=class_filter
        ))
        directives.append(build_update_nav_directive(next_sub, target_waypoint=(world_x, world_y)))
        
    elif action_type == ACTION_MERGE_BACK:
        if active_sub_factions:
            directives.append(build_merge_faction_directive(active_sub_factions[0], brain_faction))
        else:
            directives.append(build_hold_directive(brain_faction))
            
    elif action_type == ACTION_SET_PLAYSTYLE:
        if not active_sub_factions:
            directives.append(build_hold_directive(brain_faction))
        else:
            sub = active_sub_factions[-1]
            known_enemies = enemy_factions or []
            if modifier == 0:
                for efid in known_enemies:
                    directives.append(build_set_aggro_mask_directive(sub, efid, allow_combat=True))
                directives.append(build_set_tactical_override_directive(sub, None))
            elif modifier == 1:
                for efid in known_enemies:
                    directives.append(build_set_aggro_mask_directive(sub, efid, allow_combat=False))
            elif modifier == 2:
                directives.append(build_set_tactical_override_directive(sub, {"type": "Kite", "trigger_radius": 80.0, "weight": 5.0}))
            elif modifier == 3:
                directives.append(build_set_tactical_override_directive(sub, None))
                for efid in known_enemies:
                    directives.append(build_set_aggro_mask_directive(sub, efid, allow_combat=True))
                    
    elif action_type == ACTION_ACTIVATE_SKILL:
        if skills and modifier < len(skills):
            from src.config.definitions import ActivateBuffDef
            import uuid
            activate_buff = ActivateBuffDef(
                buff_id=str(uuid.uuid4()),
                modifiers=[skills[modifier]],
                duration_ticks=300
            )
            directives.append(build_activate_buff_directive(brain_faction, activate_buff))
            
    elif action_type == ACTION_RETREAT:
        directives.append(build_retreat_directive(brain_faction, world_x, world_y))
        updated_nav = None
        
    else:
        directives.append(build_hold_directive(brain_faction))
        
    return directives, updated_nav

def _next_sub_faction_id(brain_faction: int, active_subs: list[int]) -> int:
    """Allocate next available sub-faction ID."""
    base = (brain_faction + 1) * 100
    for offset in range(100):
        candidate = base + offset
        if candidate not in active_subs:
            return candidate
    return base + len(active_subs)
