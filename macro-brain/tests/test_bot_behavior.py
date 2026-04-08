import pytest
from src.config.definitions import BotStrategyDef, BotStageBehaviorDef

def test_charge_to_dict():
    strat = BotStrategyDef("Charge", target_faction=0)
    assert strat.to_dict() == {"type": "Charge", "target_faction": 0}

def test_hold_position_to_dict():
    strat = BotStrategyDef("HoldPosition", x=100.0, y=200.0)
    assert strat.to_dict() == {"type": "HoldPosition", "x": 100.0, "y": 200.0}

def test_adaptive_to_dict():
    strat = BotStrategyDef("Adaptive", target_faction=0, retreat_health_fraction=0.5, retreat_x=10.0, retreat_y=20.0)
    assert strat.to_dict() == {
        "type": "Adaptive",
        "target_faction": 0,
        "retreat_health_fraction": 0.5,
        "retreat_x": 10.0,
        "retreat_y": 20.0
    }

def test_mixed_to_dict():
    strat1 = BotStrategyDef("Charge", target_faction=0)
    strat2 = BotStrategyDef("HoldPosition", x=100.0, y=200.0)
    strat = BotStrategyDef("Mixed", strategies=[strat1, strat2])
    
    expected = {
        "type": "Mixed",
        "strategies": [
            {"type": "Charge", "target_faction": 0},
            {"type": "HoldPosition", "x": 100.0, "y": 200.0}
        ]
    }
    assert strat.to_dict() == expected


from src.config.game_profile import load_profile

def test_profile_loads_and_parses_bot_behaviors():
    profile = load_profile("profiles/default_swarm_combat.json")
    assert hasattr(profile, "bot_stage_behaviors")
    assert len(profile.bot_stage_behaviors) == 5

    # Check stage 1
    payload1 = profile.bot_behaviors_payload(1)
    assert len(payload1) == 1
    assert payload1[0]["strategy"]["type"] == "Charge"

    # Check stage 3
    payload3 = profile.bot_behaviors_payload(3)
    assert len(payload3) == 1
    assert payload3[0]["strategy"]["type"] == "HoldPosition"

    # Check stage 5
    payload5 = profile.bot_behaviors_payload(5)
    assert len(payload5) == 1
    assert payload5[0]["strategy"]["type"] == "Mixed"
    assert len(payload5[0]["strategy"]["strategies"]) == 3

def test_backward_compatibility():
    # Remove bot_stage_behaviors to act as an old profile
    profile = load_profile("profiles/default_swarm_combat.json")
    profile.bot_stage_behaviors.clear()
    
    # Should fallback to Charge
    payload = profile.bot_behaviors_payload(1)
    assert len(payload) == 1
    assert payload[0]["strategy"]["type"] == "Charge"
    assert payload[0]["strategy"]["target_faction"] == profile.brain_faction.id
