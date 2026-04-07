from typing import Any
from dataclasses import asdict
from src.config.definitions import ActivateBuffDef

def build_hold_directive() -> dict[str, Any]:
    return {"type": "macro_directive", "directive": "Hold"}

def build_update_nav_directive(follower_faction: int, enemy_faction: int) -> dict[str, Any]:
    return {
        "type": "macro_directive",
        "directive": "UpdateNavigation",
        "follower_faction": follower_faction,
        "target": {"type": "Faction", "faction_id": enemy_faction},
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
