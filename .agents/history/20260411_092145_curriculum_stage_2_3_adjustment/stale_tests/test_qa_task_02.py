import pytest
import numpy as np

from src.utils.terrain_generator import generate_terrain_for_stage
from src.env.actions import multidiscrete_to_directives, ACTION_ATTACK_COORD, ACTION_DROP_REPELLENT, ACTION_DROP_PHEROMONE, ACTION_HOLD
from src.config.game_profile import load_profile

def test_qa_stage2_terrain():
    terrain = generate_terrain_for_stage(2)
    assert terrain is not None
    assert "hard_costs" in terrain
    assert "soft_costs" in terrain
    # Stage 2 dimensions: 30x30
    assert terrain["width"] == 30
    assert terrain["height"] == 30

def test_qa_stage3_terrain():
    terrain = generate_terrain_for_stage(3)
    assert terrain is not None
    assert max(terrain["hard_costs"]) == 100
    assert 40 in terrain["soft_costs"], "Should have soft_costs equal to 40 (danger zones)"

def test_qa_multidiscrete_returns_tuple():
    action = np.array([ACTION_DROP_REPELLENT, 5, 5])
    result = multidiscrete_to_directives(
        action, brain_faction=1, active_sub_factions=[], cell_size=10.0, pad_offset_x=0, pad_offset_y=0
    )
    assert isinstance(result, tuple)
    assert len(result) == 2
    directives, updated_nav = result
    assert isinstance(directives, list)
    assert updated_nav is None or isinstance(updated_nav, dict)

def test_qa_action_drop_repellent_cost():
    action = np.array([ACTION_DROP_REPELLENT, 5, 5])
    directives, _ = multidiscrete_to_directives(
        action, brain_faction=1, active_sub_factions=[], cell_size=10.0, pad_offset_x=0, pad_offset_y=0
    )
    # The last directive should be SetZoneModifier
    zone_dir = directives[-1]
    assert zone_dir["directive"] == "SetZoneModifier"
    assert zone_dir["cost_modifier"] == 200.0

def test_qa_nav_directive_replayed():
    # 1. AttackCoord
    action_attack = np.array([ACTION_ATTACK_COORD, 10, 10])
    directives1, updated_nav1 = multidiscrete_to_directives(
        action_attack, brain_faction=1, active_sub_factions=[], cell_size=10.0, pad_offset_x=0, pad_offset_y=0
    )
    assert updated_nav1 is not None

    # 2. DropPheromone, passing in the updated_nav1
    action_phero = np.array([ACTION_DROP_PHEROMONE, 5, 5])
    directives2, updated_nav2 = multidiscrete_to_directives(
        action_phero, brain_faction=1, active_sub_factions=[], cell_size=10.0, pad_offset_x=0, pad_offset_y=0,
        last_nav_directive=updated_nav1
    )
    
    # Assert that the updated_nav1 was replayed in directives2
    assert updated_nav1 in directives2
    assert updated_nav2 == updated_nav1

    # 3. Hold clears
    action_hold = np.array([ACTION_HOLD, 0, 0])
    directives3, updated_nav3 = multidiscrete_to_directives(
        action_hold, brain_faction=1, active_sub_factions=[], cell_size=10.0, pad_offset_x=0, pad_offset_y=0,
        last_nav_directive=updated_nav2
    )
    assert updated_nav3 is None

def test_qa_profile_loads_duration():
    p = load_profile("profiles/tactical_curriculum.json")
    assert p.abilities.zone_modifier_duration_ticks == 1500
