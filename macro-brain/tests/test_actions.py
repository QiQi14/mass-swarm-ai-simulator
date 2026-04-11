import numpy as np
import pytest
from src.env.actions import (
    multidiscrete_to_directives,
    _next_sub_faction_id,
)
from src.env.spaces import (
    ACTION_HOLD, ACTION_ATTACK_COORD, ACTION_DROP_PHEROMONE,
    ACTION_DROP_REPELLENT, ACTION_SPLIT_TO_COORD, ACTION_MERGE_BACK,
    ACTION_RETREAT, ACTION_SCOUT, MAX_GRID_WIDTH
)

def test_hold_action():
    # Hold action ignores coordinate, returns Hold directive
    action = np.array([ACTION_HOLD, 125])
    directives, _ = multidiscrete_to_directives(action, brain_faction=0, active_sub_factions=[])
    assert len(directives) == 1
    assert directives[0]["directive"] == "Hold"
    assert directives[0]["faction_id"] == 0

def test_attack_coord():
    # AttackCoord returns UpdateNav with Waypoint target at correct world coords
    # flat_coord=125 -> grid_x=25, grid_y=2, pad_offset_x/y=0 -> world_x=510, world_y=50
    action = np.array([ACTION_ATTACK_COORD, 125])
    directives, _ = multidiscrete_to_directives(action, brain_faction=0, active_sub_factions=[])
    assert len(directives) == 1
    assert directives[0]["directive"] == "UpdateNavigation"
    assert directives[0]["follower_faction"] == 0
    assert directives[0]["target"]["type"] == "Waypoint"
    assert directives[0]["target"]["x"] == 510.0
    assert directives[0]["target"]["y"] == 50.0

def test_drop_pheromone():
    # DropPheromone returns SetZoneModifier with cost=-50
    action = np.array([ACTION_DROP_PHEROMONE, 125])
    directives, _ = multidiscrete_to_directives(action, brain_faction=0, active_sub_factions=[])
    assert len(directives) == 1
    assert directives[0]["directive"] == "SetZoneModifier"
    assert directives[0]["cost_modifier"] == -50.0

def test_drop_repellent():
    # DropRepellent returns SetZoneModifier with cost=+200
    action = np.array([ACTION_DROP_REPELLENT, 125])
    directives, _ = multidiscrete_to_directives(action, brain_faction=0, active_sub_factions=[])
    assert len(directives) == 1
    assert directives[0]["directive"] == "SetZoneModifier"
    assert directives[0]["cost_modifier"] == 200.0

def test_split_to_coord():
    # SplitToCoord returns 2 directives: SplitFaction + UpdateNav for sub
    action = np.array([ACTION_SPLIT_TO_COORD, 125])
    directives, _ = multidiscrete_to_directives(action, brain_faction=0, active_sub_factions=[100])
    assert len(directives) == 2
    assert directives[0]["directive"] == "SplitFaction"
    assert directives[0]["new_sub_faction"] == 101  # next_sub_faction_id avoids 100
    assert directives[1]["directive"] == "UpdateNavigation"
    assert directives[1]["follower_faction"] == 101

def test_merge_back_with_active_subs():
    # MergeBack with active subs returns MergeFaction directive
    action = np.array([ACTION_MERGE_BACK, 125])
    directives, _ = multidiscrete_to_directives(action, brain_faction=0, active_sub_factions=[100, 101])
    assert len(directives) == 1
    assert directives[0]["directive"] == "MergeFaction"
    assert directives[0]["source_faction"] == 100
    assert directives[0]["target_faction"] == 0

def test_merge_back_with_no_subs():
    # MergeBack with NO subs returns Hold (fallback)
    action = np.array([ACTION_MERGE_BACK, 125])
    directives, _ = multidiscrete_to_directives(action, brain_faction=0, active_sub_factions=[])
    assert len(directives) == 1
    assert directives[0]["directive"] == "Hold"

def test_scout():
    # Scout returns SplitFaction + UpdateNav directives (no aggro masks)
    action = np.array([ACTION_SCOUT, 125])
    directives, _ = multidiscrete_to_directives(
        action, brain_faction=0, active_sub_factions=[],
    )
    assert len(directives) == 2
    assert directives[0]["directive"] == "SplitFaction"
    assert directives[0]["percentage"] == 0.10  # scout_percentage default
    assert directives[1]["directive"] == "UpdateNavigation"
    assert directives[1]["target"]["type"] == "Waypoint"

def test_next_sub_faction_id():
    # _next_sub_faction_id avoids collisions with active subs
    assert _next_sub_faction_id(0, []) == 100
    assert _next_sub_faction_id(0, [100]) == 101
    assert _next_sub_faction_id(0, [100, 102]) == 101
    assert _next_sub_faction_id(0, [100, 101, 102]) == 103

def test_coordinate_decode():
    # Coordinate decode: flat_coord=125 -> grid(25,2) -> world(510, 50) with cell_size=20
    action = np.array([ACTION_ATTACK_COORD, 125])
    directives, _ = multidiscrete_to_directives(action, brain_faction=0, active_sub_factions=[])
    assert directives[0]["target"]["x"] == 510.0
    assert directives[0]["target"]["y"] == 50.0

def test_multidiscrete_negative_path():
    # Negative path: unknown action type falls back to Hold
    action = np.array([999, 125])
    directives, _ = multidiscrete_to_directives(action, brain_faction=0, active_sub_factions=[])
    assert len(directives) == 1
    assert directives[0]["directive"] == "Hold"
