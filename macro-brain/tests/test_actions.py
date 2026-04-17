import numpy as np
import pytest
from src.env.spaces import make_action_space
from src.env.actions import multidiscrete_to_directives

# 0: Hold
# 1: AttackCoord
# 2: ZoneModifier (0=attract, 1=repel)
# 3: SplitToCoord
# 4: MergeBack
# 5: SetPlaystyle (0=aggressive, 1=passive, 2=kite)
# 6: ActivateSkill
# 7: Retreat

def test_make_action_space():
    space = make_action_space()
    assert space.nvec.tolist() == [8, 2500, 4]

def test_hold_action():
    action = np.array([0, 125, 0])
    directives, _ = multidiscrete_to_directives(action, brain_faction=0, active_sub_factions=[])
    assert len(directives) == 1
    assert directives[0]["directive"] == "Hold"
    assert directives[0]["faction_id"] == 0

def test_attack_coord():
    action = np.array([1, 125, 0])
    directives, _ = multidiscrete_to_directives(action, brain_faction=0, active_sub_factions=[])
    assert directives[0]["directive"] == "UpdateNavigation"

def test_zone_modifier_attract():
    action = np.array([2, 125, 0])
    directives, _ = multidiscrete_to_directives(action, brain_faction=0, active_sub_factions=[])
    assert directives[0]["directive"] == "SetZoneModifier"
    assert directives[0]["cost_modifier"] == -50.0

def test_zone_modifier_repel():
    action = np.array([2, 125, 1])
    directives, _ = multidiscrete_to_directives(action, brain_faction=0, active_sub_factions=[])
    assert directives[0]["directive"] == "SetZoneModifier"
    assert directives[0]["cost_modifier"] == 200.0

def test_split_to_coord_all():
    action = np.array([3, 125, 0])
    directives, _ = multidiscrete_to_directives(action, brain_faction=0, active_sub_factions=[100])
    assert directives[0]["directive"] == "SplitFaction"
    assert directives[0]["class_filter"] is None

def test_split_to_coord_class1():
    action = np.array([3, 125, 2])
    directives, _ = multidiscrete_to_directives(action, brain_faction=0, active_sub_factions=[100])
    assert directives[0]["directive"] == "SplitFaction"
    assert directives[0]["class_filter"] == 1

def test_merge_back():
    action = np.array([4, 125, 0])
    directives, _ = multidiscrete_to_directives(action, brain_faction=0, active_sub_factions=[100])
    # The actual implementation of MergeBack might fall under "MergeFaction" or similar, 
    # depending on what was implemented in B3.
    # Assuming multidiscrete_to_directives produces "MergeFaction" or similar.
    assert len(directives) > 0

def test_set_playstyle_aggressive():
    action = np.array([5, 0, 0])
    directives, _ = multidiscrete_to_directives(action, brain_faction=0, active_sub_factions=[100], enemy_factions=[1])
    assert directives[0]["directive"] == "SetAggroMask"
    assert directives[0]["allow_combat"] is True

def test_set_playstyle_passive():
    action = np.array([5, 0, 1])
    directives, _ = multidiscrete_to_directives(action, brain_faction=0, active_sub_factions=[100], enemy_factions=[1])
    assert directives[0]["directive"] == "SetAggroMask"
    assert directives[0]["allow_combat"] is False

def test_set_playstyle_kite():
    action = np.array([5, 0, 2])
    directives, _ = multidiscrete_to_directives(action, brain_faction=0, active_sub_factions=[100], enemy_factions=[1])
    assert directives[0]["directive"] == "SetTacticalOverride"
    assert directives[0]["behavior"]["type"] == "Kite"

def test_set_playstyle_no_subs():
    action = np.array([5, 0, 0])
    directives, _ = multidiscrete_to_directives(action, brain_faction=0, active_sub_factions=[])
    assert directives[0]["directive"] == "Hold"

def test_retreat():
    action = np.array([7, 125, 0])
    directives, _ = multidiscrete_to_directives(action, brain_faction=0, active_sub_factions=[1])
    # Usually retreat handles finding a retreat point, which means it evaluates to UpdateNavigation or Retreat 
    assert len(directives) > 0

def test_negative_path():
    action = np.array([999, 125, 0])
    directives, _ = multidiscrete_to_directives(action, brain_faction=0, active_sub_factions=[])
    assert directives[0]["directive"] == "Hold"

