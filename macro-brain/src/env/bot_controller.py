"""Heuristic bot controller for training opponents.

All bot decision-making lives here — NOT in the Rust Micro-Core.
The bot controller reads the state snapshot and produces MacroDirective
JSON dicts, identical in format to what the RL brain produces.

## PATCH 3: Hysteresis (Anti-Jitter)
The Adaptive strategy uses mode-locking to prevent oscillation.
Once the bot transitions (charge→retreat or retreat→charge), it locks
into that state for MIN_LOCK_STEPS evaluations. Without this, tied
battles cause frame-by-frame oscillation that destroys training gradients.

Strategies:
  Charge       — always navigate toward enemy faction
  HoldPosition — retreat to a fixed waypoint (defensive)
  Adaptive     — charge when healthy, retreat when losing (with hysteresis)
  Mixed        — randomly select one strategy per episode
"""

from __future__ import annotations

import random
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.config.definitions import BotStageBehaviorDef, BotStrategyDef


class BotController:
    """Stateful heuristic bot that produces directives each step.

    Created once per SwarmEnv. Reconfigured on reset() when
    the curriculum stage changes.
    """

    # ── PATCH 3: Hysteresis constant ────────────────────────
    # At 2 Hz AI eval rate (every 30 ticks), 15 steps = ~7.5 seconds
    # This prevents jitter during balanced battles.
    MIN_LOCK_STEPS: int = 15

    def __init__(self):
        self._faction_id: int = 1
        self._target_faction: int = 0
        self._strategy: BotStrategyDef | None = None
        self._starting_count: int = 50
        self._active_strategy: BotStrategyDef | None = None  # resolved for Mixed

        # ── PATCH 3: Hysteresis state ───────────────────────
        self._current_mode: str = "charge"     # "charge" or "retreat"
        self._mode_lock_remaining: int = 0     # steps until mode can change

    def configure(
        self,
        behavior: BotStageBehaviorDef,
        target_faction: int,
        starting_count: int,
        rng=None,
    ) -> None:
        """Reconfigure for a new episode. Called during SwarmEnv.reset().

        Resets ALL state including hysteresis lock.
        """
        self._faction_id = behavior.faction_id
        self._target_faction = target_faction
        self._strategy = behavior.strategy
        self._starting_count = starting_count

        # Reset hysteresis
        self._current_mode = "charge"
        self._mode_lock_remaining = 0

        # For Mixed: select one strategy at episode start
        if behavior.strategy.type == "Mixed" and behavior.strategy.strategies:
            if rng is None:
                rng = random
            idx = rng.randint(0, len(behavior.strategy.strategies) - 1)
            self._active_strategy = behavior.strategy.strategies[idx]
        else:
            self._active_strategy = behavior.strategy

    def compute_directive(self, snapshot: dict) -> dict[str, Any]:
        """Compute the bot's directive based on current game state.

        Returns a MacroDirective JSON dict (inner format, no "type" wrapper).
        The SwarmEnv wraps all directives in the batch payload.
        """
        if self._active_strategy is None:
            return _hold()

        strategy = self._active_strategy

        if strategy.type == "Charge":
            return _update_nav(
                self._faction_id,
                {"type": "Faction", "faction_id": strategy.target_faction},
            )

        elif strategy.type == "HoldPosition":
            return _retreat(self._faction_id, strategy.x, strategy.y)

        elif strategy.type == "Adaptive":
            return self._compute_adaptive(snapshot, strategy)

        # Fallback
        return _hold()

    # ── PATCH 3: Adaptive with Hysteresis ───────────────────

    def _compute_adaptive(self, snapshot: dict, strategy) -> dict:
        """Adaptive strategy with mode-locking to prevent jitter.

        State machine:
          1. If mode_lock_remaining > 0, stay in current mode
          2. Else, evaluate health fraction:
             - Below threshold → switch to retreat, lock for MIN_LOCK_STEPS
             - Above threshold → switch to charge, lock for MIN_LOCK_STEPS
          3. Only transitions lock; staying in the same mode does NOT reset lock
        """
        # Tick down lock
        if self._mode_lock_remaining > 0:
            self._mode_lock_remaining -= 1

        # Evaluate health
        current_count = _get_faction_count(snapshot, self._faction_id)
        fraction = current_count / max(self._starting_count, 1)
        desired_mode = (
            "retreat" if fraction < strategy.retreat_health_fraction
            else "charge"
        )

        # Only switch if lock has expired AND mode actually changes
        if self._mode_lock_remaining <= 0 and desired_mode != self._current_mode:
            self._current_mode = desired_mode
            self._mode_lock_remaining = self.MIN_LOCK_STEPS

        # Execute current mode
        if self._current_mode == "retreat":
            return _retreat(
                self._faction_id,
                strategy.retreat_x,
                strategy.retreat_y,
            )
        else:
            return _update_nav(
                self._faction_id,
                {"type": "Faction", "faction_id": strategy.target_faction},
            )


# ── Directive Builders ──────────────────────────────────────

def _hold() -> dict:
    return {"directive": "Hold"}


def _update_nav(follower_faction: int, target: dict) -> dict:
    return {
        "directive": "UpdateNavigation",
        "follower_faction": follower_faction,
        "target": target,
    }


def _retreat(faction: int, x: float, y: float) -> dict:
    return {
        "directive": "Retreat",
        "faction": faction,
        "retreat_x": float(x),
        "retreat_y": float(y),
    }


def _get_faction_count(snapshot: dict, faction_id: int) -> int:
    """Read faction entity count from snapshot summary."""
    counts = snapshot.get("summary", {}).get("faction_counts", {})
    return counts.get(str(faction_id), counts.get(faction_id, 0))
