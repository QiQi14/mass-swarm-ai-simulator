"""Heuristic bot controller for training opponents.

All bot decision-making lives here — NOT in the Rust Micro-Core.
The bot controller reads the state snapshot and produces MacroDirective
JSON dicts, identical in format to what the RL brain produces.

## PATCH 3: Hysteresis (Anti-Jitter)
The Adaptive strategy uses mode-locking to prevent oscillation.

Strategies:
  Charge       — always navigate toward enemy faction
  HoldPosition — retreat to a fixed waypoint (defensive)
  Adaptive     — charge when healthy, retreat when losing (with hysteresis)
  Mixed        — randomly select one strategy per episode
  Patrol       — alternate between waypoints (vertical/horizontal patrol)
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

    # Hysteresis constant for Adaptive strategy
    MIN_LOCK_STEPS: int = 15

    def __init__(self):
        self._faction_id: int = 1
        self._target_faction: int = 0
        self._strategy: BotStrategyDef | None = None
        self._starting_count: int = 50
        self._active_strategy: BotStrategyDef | None = None

        # Adaptive hysteresis state
        self._current_mode: str = "charge"
        self._mode_lock_remaining: int = 0

        # Patrol state
        self._patrol_waypoint_idx: int = 0

    def configure(
        self,
        behavior: BotStageBehaviorDef,
        target_faction: int,
        starting_count: int,
        rng=None,
    ) -> None:
        """Reconfigure for a new episode. Called during SwarmEnv.reset()."""
        self._faction_id = behavior.faction_id
        self._target_faction = target_faction
        self._strategy = behavior.strategy
        self._starting_count = starting_count

        # Reset hysteresis
        self._current_mode = "charge"
        self._mode_lock_remaining = 0

        # Reset patrol to first waypoint
        self._patrol_waypoint_idx = 0

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
            # Send Idle so entities stay at their spawn spread.
            # Retreat would converge all entities to a single point.
            return _hold()

        elif strategy.type == "Adaptive":
            return self._compute_adaptive(snapshot, strategy)

        elif strategy.type == "Patrol":
            return self._compute_patrol(snapshot, strategy)

        # Fallback
        return _hold()

    def _compute_adaptive(self, snapshot: dict, strategy) -> dict:
        """Adaptive strategy with mode-locking to prevent jitter."""
        if self._mode_lock_remaining > 0:
            self._mode_lock_remaining -= 1

        current_count = _get_faction_count(snapshot, self._faction_id)
        fraction = current_count / max(self._starting_count, 1)
        desired_mode = (
            "retreat" if fraction < strategy.retreat_health_fraction
            else "charge"
        )

        if self._mode_lock_remaining <= 0 and desired_mode != self._current_mode:
            self._current_mode = desired_mode
            self._mode_lock_remaining = self.MIN_LOCK_STEPS

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

    def _compute_patrol(self, snapshot: dict, strategy) -> dict:
        """Patrol strategy: alternate between waypoints.

        Uses Retreat directives to move toward the current waypoint.
        When the faction's centroid is within waypoint_threshold of the
        target, advance to the next waypoint in the list (wrapping).
        """
        waypoints = strategy.waypoints or []
        if not waypoints:
            return _hold()

        wp = waypoints[self._patrol_waypoint_idx % len(waypoints)]
        wp_x = wp["x"]
        wp_y = wp["y"]

        # Check if we've reached the current waypoint
        centroid = _get_faction_centroid(snapshot, self._faction_id)
        if centroid is not None:
            cx, cy = centroid
            dist = ((cx - wp_x) ** 2 + (cy - wp_y) ** 2) ** 0.5
            if dist < strategy.waypoint_threshold:
                self._patrol_waypoint_idx = (
                    (self._patrol_waypoint_idx + 1) % len(waypoints)
                )
                wp = waypoints[self._patrol_waypoint_idx]
                wp_x = wp["x"]
                wp_y = wp["y"]

        return _retreat(self._faction_id, wp_x, wp_y)


# ── Directive Builders ──────────────────────────────────────

def _hold() -> dict:
    return {"directive": "Idle"}


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


def _get_faction_centroid(snapshot: dict, faction_id: int):
    """Estimate faction centroid from density map.

    Returns (x, y) in world coordinates, or None if no entities.
    """
    import numpy as np
    density_maps = snapshot.get("density_maps", {})
    key = str(faction_id)
    if key not in density_maps:
        return None

    flat = density_maps[key]
    if not flat or sum(flat) < 0.01:
        return None

    # Get grid dimensions from flat array length (assume square 50x50)
    grid_size = len(flat)
    side = int(grid_size ** 0.5)
    if side * side != grid_size:
        return None

    arr = np.array(flat, dtype=np.float32).reshape(side, side)
    total = arr.sum()
    if total < 0.01:
        return None

    rows, cols = np.indices(arr.shape)
    cy_grid = float((rows * arr).sum() / total)
    cx_grid = float((cols * arr).sum() / total)

    # Convert grid coords to world coords
    # Assuming cell_size=20, world_size=1000
    cell_size = 1000.0 / side
    return (cx_grid * cell_size + cell_size / 2, cy_grid * cell_size + cell_size / 2)
