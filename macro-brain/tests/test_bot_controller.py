"""Tests for the stateless BotController heuristic."""

import pytest
from src.env.bot_controller import BotController, _get_faction_count, _hold, _update_nav, _retreat

class MockBotStrategyDef:
    def __init__(self, type, target_faction=None, x=None, y=None, retreat_health_fraction=None, retreat_x=None, retreat_y=None, strategies=None):
        self.type = type
        self.target_faction = target_faction
        self.x = x
        self.y = y
        self.retreat_health_fraction = retreat_health_fraction
        self.retreat_x = retreat_x
        self.retreat_y = retreat_y
        self.strategies = strategies

class MockBotStageBehaviorDef:
    def __init__(self, faction_id, strategy, stage=1, eval_interval_ticks=60):
        self.faction_id = faction_id
        self.strategy = strategy
        self.stage = stage
        self.eval_interval_ticks = eval_interval_ticks

def _make_snapshot(faction_counts: dict) -> dict:
    return {
        "summary": {
            "faction_counts": faction_counts
        }
    }

def test_charge_strategy():
    controller = BotController()
    strategy = MockBotStrategyDef("Charge", target_faction=0)
    behavior = MockBotStageBehaviorDef(faction_id=1, strategy=strategy)
    controller.configure(behavior, target_faction=0, starting_count=50)

    snapshot = _make_snapshot({"1": 50, "0": 50})
    directive = controller.compute_directive(snapshot)

    assert directive == {
        "directive": "UpdateNavigation",
        "follower_faction": 1,
        "target": {"type": "Faction", "faction_id": 0}
    }

def test_hold_position_strategy():
    controller = BotController()
    strategy = MockBotStrategyDef("HoldPosition", x=100.0, y=200.0)
    behavior = MockBotStageBehaviorDef(faction_id=1, strategy=strategy)
    controller.configure(behavior, target_faction=0, starting_count=50)

    snapshot = _make_snapshot({"1": 50, "0": 50})
    directive = controller.compute_directive(snapshot)

    assert directive == {
        "directive": "Idle"
    }

def test_adaptive_hysteresis():
    controller = BotController()
    strategy = MockBotStrategyDef(
        "Adaptive",
        target_faction=0,
        retreat_health_fraction=0.5,
        retreat_x=900.0,
        retreat_y=900.0
    )
    behavior = MockBotStageBehaviorDef(faction_id=1, strategy=strategy)
    controller.configure(behavior, target_faction=0, starting_count=50)

    # Initial state: charge
    directive = controller.compute_directive(_make_snapshot({"1": 50}))
    assert directive["directive"] == "UpdateNavigation"

    # Drop health below threshold (50 * 0.5 = 25)
    # The mode lock shouldn't be active since it wasn't triggered
    directive = controller.compute_directive(_make_snapshot({"1": 20}))
    assert directive["directive"] == "Retreat"
    
    # State is now 'retreat'. Lock is MIN_LOCK_STEPS (15)

    # Bring health above threshold immediately
    # Mode lock is active, so it should still retreat
    for _ in range(BotController.MIN_LOCK_STEPS - 1): # We used 1 step on the switch itself
        directive = controller.compute_directive(_make_snapshot({"1": 50}))
        assert directive["directive"] == "Retreat"

    # One more step unlocks it. It evaluates, sees health is good, and switches to charge.
    directive = controller.compute_directive(_make_snapshot({"1": 50}))
    assert directive["directive"] == "UpdateNavigation"

    # Now state is 'charge'. Lock is MIN_LOCK_STEPS. 
    # Drop health again
    for _ in range(BotController.MIN_LOCK_STEPS - 1):
        directive = controller.compute_directive(_make_snapshot({"1": 10}))
        assert directive["directive"] == "UpdateNavigation"

    # Unlock -> switch to retreat
    directive = controller.compute_directive(_make_snapshot({"1": 10}))
    assert directive["directive"] == "Retreat"


def test_hysteresis_reset_on_configure():
    controller = BotController()
    strategy = MockBotStrategyDef(
        "Adaptive",
        target_faction=0,
        retreat_health_fraction=0.5,
        retreat_x=900.0,
        retreat_y=900.0
    )
    behavior = MockBotStageBehaviorDef(faction_id=1, strategy=strategy)
    controller.configure(behavior, target_faction=0, starting_count=50)

    # Drop health to trigger lock to 'retreat'
    controller.compute_directive(_make_snapshot({"1": 20}))
    assert controller._current_mode == "retreat"
    assert controller._mode_lock_remaining == BotController.MIN_LOCK_STEPS
    
    # Configure should reset
    controller.configure(behavior, target_faction=0, starting_count=50)
    assert controller._current_mode == "charge"
    assert controller._mode_lock_remaining == 0


def test_mixed_strategy():
    controller = BotController()
    strategy1 = MockBotStrategyDef("Charge", target_faction=0)
    strategy2 = MockBotStrategyDef("HoldPosition", x=100.0, y=200.0)
    strategy = MockBotStrategyDef("Mixed", strategies=[strategy1, strategy2])
    behavior = MockBotStageBehaviorDef(faction_id=1, strategy=strategy)
    
    class FakeRng:
        def __init__(self, idx):
            self.idx = idx
        def randint(self, a, b):
            return self.idx

    controller.configure(behavior, target_faction=0, starting_count=50, rng=FakeRng(0))
    # It should have chosen strategy 0 (Charge)
    directive = controller.compute_directive(_make_snapshot({"1": 50}))
    assert directive["directive"] == "UpdateNavigation"

    controller.configure(behavior, target_faction=0, starting_count=50, rng=FakeRng(1))
    # It should have chosen strategy 1 (HoldPosition)
    directive = controller.compute_directive(_make_snapshot({"1": 50}))
    assert directive["directive"] == "Idle"

def test_builders():
    assert _hold() == {"directive": "Idle"}
    assert _update_nav(2, {"type": "Faction", "faction_id": 0}) == {
        "directive": "UpdateNavigation", "follower_faction": 2, "target": {"type": "Faction", "faction_id": 0}
    }
    assert _retreat(2, 50.0, 60.0) == {
        "directive": "Retreat", "faction": 2, "retreat_x": 50.0, "retreat_y": 60.0
    }

def test_get_faction_count():
    assert _get_faction_count({"summary": {"faction_counts": {"1": 42}}}, 1) == 42
    assert _get_faction_count({"summary": {"faction_counts": {1: 42}}}, 1) == 42
    assert _get_faction_count({"summary": {"faction_counts": {"0": 10}}}, 1) == 0
    assert _get_faction_count({}, 1) == 0

def test_fallback_hold():
    controller = BotController()
    # No configure call
    assert controller.compute_directive({}) == {"directive": "Idle"}

    # Invalid strategy type
    strategy = MockBotStrategyDef("Unknown")
    behavior = MockBotStageBehaviorDef(faction_id=1, strategy=strategy)
    controller.configure(behavior, target_faction=0, starting_count=50)
    assert controller.compute_directive({}) == {"directive": "Idle"}
