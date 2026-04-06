"""
SwarmEnv — Gymnasium environment for Mass-Swarm AI Simulator.

Communicates with the Rust Micro-Core via ZMQ REP socket.

## SAFETY INVARIANTS (v3 Patches)
P6: Dynamic epicenter from density centroid (not hardcoded)
P7: Sub-faction state read from Rust snapshot (single source of truth)
P8: ZMQ timeout → episode truncation; Tick swallowing for interventions
"""

import json
import numpy as np
import zmq
import gymnasium as gym

from src.env.spaces import (
    make_observation_space, make_action_space,
    ACTION_HOLD, ACTION_UPDATE_NAV, ACTION_FRENZY, ACTION_RETREAT,
    ACTION_ZONE_MODIFIER, ACTION_SPLIT_FACTION, ACTION_MERGE_FACTION,
    ACTION_SET_AGGRO_MASK, GRID_WIDTH, GRID_HEIGHT,
)
from src.utils.vectorizer import vectorize_snapshot


class SwarmEnv(gym.Env):
    """Gymnasium environment wrapping the Rust simulation via ZMQ."""

    metadata = {"render_modes": []}

    def __init__(self, config: dict | None = None):
        super().__init__()
        config = config or {}
        self.bind_address = config.get("bind_address", "tcp://*:5555")
        self.max_steps = config.get("max_steps", 200)
        self.brain_faction = config.get("brain_faction", 0)
        self.enemy_faction = config.get("enemy_faction", 1)
        self.world_width = config.get("world_width", 1000.0)
        self.world_height = config.get("world_height", 1000.0)
        self.zmq_timeout_ms = config.get("zmq_timeout_ms", 10000)
        self.curriculum_stage = config.get("curriculum_stage", 1)

        self.observation_space = make_observation_space()
        self.action_space = make_action_space()

        self._active_sub_factions: list[int] = []
        self._last_aggro_state: bool = True
        self._last_snapshot: dict | None = None
        self._step_count: int = 0

        self._ctx = zmq.Context()
        self._socket: zmq.Socket | None = None
        self._connect()

    def _connect(self):
        """Create and bind the REP socket with timeout."""
        if self._socket is not None:
            self._socket.close()
        self._socket = self._ctx.socket(zmq.REP)
        self._socket.setsockopt(zmq.RCVTIMEO, self.zmq_timeout_ms)
        self._socket.setsockopt(zmq.SNDTIMEO, self.zmq_timeout_ms)
        self._socket.setsockopt(zmq.LINGER, 0)
        self._socket.bind(self.bind_address)

    def _disconnect(self):
        """Close and unbind the socket."""
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def action_masks(self) -> np.ndarray:
        mask = np.ones(8, dtype=bool)
        if self.curriculum_stage == 1:
            mask[4:8] = False  # Lock terrain-dependent actions
        else:
            if not self._active_sub_factions:
                mask[6] = False  # MergeFaction
                mask[7] = False  # SetAggroMask
        return mask

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._step_count = 0
        self._active_sub_factions = []
        self._last_aggro_state = True
        self._last_snapshot = None

        try:
            raw = self._socket.recv_string()
        except zmq.error.Again:
            print("[SwarmEnv] ZMQ Timeout during reset. Rust not running.")
            self._disconnect()
            self._connect()
            return self.observation_space.sample(), {}

        # Cycle 1: send ResetEnvironment
        terrain = None
        if self.curriculum_stage >= 2:
            from src.utils.terrain_generator import generate_random_terrain
            terrain = generate_random_terrain(seed=self.np_random.integers(0, 2**31))

        self._socket.send_string(json.dumps({
            "type": "reset_environment",
            "terrain": terrain,
            "spawns": [
                {"faction_id": 0, "count": 150, "x": 200.0, "y": 500.0, "spread": 80.0},
                {"faction_id": 1, "count": 150, "x": 800.0, "y": 500.0, "spread": 80.0},
            ]
        }))

        # Cycle 2: recv fresh post-reset snapshot → send Hold
        try:
            raw = self._socket.recv_string()
        except zmq.error.Again:
            print("[SwarmEnv] ZMQ Timeout during reset post-reset snapshot. Rust not running.")
            self._disconnect()
            self._connect()
            return self.observation_space.sample(), {}

        snapshot = json.loads(raw)
        self._last_snapshot = snapshot

        self._active_sub_factions = snapshot.get("active_sub_factions", [])

        self._socket.send_string(json.dumps(
            {"type": "macro_directive", "directive": "Hold"}
        ))

        obs = vectorize_snapshot(snapshot, self.brain_faction, self.enemy_faction)
        return obs, {}

    def step(self, action: int):
        self._step_count += 1

        snapshot = None
        while True:
            try:
                raw = self._socket.recv_string()
            except zmq.error.Again:
                print("[SwarmEnv] ZMQ Timeout. Rust Core paused/crashed. Truncating episode.")
                self._disconnect()
                self._connect()
                return (
                    self.observation_space.sample(),
                    0.0,
                    False,       # terminated
                    True,        # truncated
                    {"error": "ZMQ_TIMEOUT"},
                )

            snapshot = json.loads(raw)
            intervention = snapshot.get("intervention_active", False)

            if intervention:
                self._socket.send_string(json.dumps(
                    {"type": "macro_directive", "directive": "Hold"}
                ))
                continue
            else:
                break

        self._active_sub_factions = snapshot.get("active_sub_factions", [])
        prev_snapshot = self._last_snapshot
        self._last_snapshot = snapshot

        directive = self._action_to_directive(action)
        self._socket.send_string(json.dumps(directive))

        obs = vectorize_snapshot(snapshot, self.brain_faction, self.enemy_faction)

        reward = self._compute_reward(snapshot, prev_snapshot)

        own_count = snapshot.get("summary", {}).get("faction_counts", {}).get(
            str(self.brain_faction), 0
        )
        enemy_count = snapshot.get("summary", {}).get("faction_counts", {}).get(
            str(self.enemy_faction), 0
        )
        terminated = own_count == 0 or enemy_count == 0
        truncated = self._step_count >= self.max_steps

        info = {
            "tick": snapshot.get("tick", 0),
            "own_count": own_count,
            "enemy_count": enemy_count,
            "sub_factions": len(self._active_sub_factions),
        }

        return obs, reward, terminated, truncated, info

    def _action_to_directive(self, action: int) -> dict:
        """Map discrete action index to MacroDirective JSON."""
        if action == ACTION_HOLD:
            return {"type": "macro_directive", "directive": "Hold"}

        elif action == ACTION_UPDATE_NAV:
            return {
                "type": "macro_directive",
                "directive": "UpdateNavigation",
                "follower_faction": self.brain_faction,
                "target": {"type": "Faction", "faction_id": self.enemy_faction},
            }

        elif action == ACTION_FRENZY:
            return {
                "type": "macro_directive",
                "directive": "TriggerFrenzy",
                "faction": self.brain_faction,
                "speed_multiplier": 1.5,
                "duration_ticks": 120,
            }

        elif action == ACTION_RETREAT:
            return {
                "type": "macro_directive",
                "directive": "Retreat",
                "faction": self.brain_faction,
                "retreat_x": 50.0,
                "retreat_y": 50.0,
            }

        elif action == ACTION_ZONE_MODIFIER:
            cx, cy = self._get_density_centroid(self.brain_faction)
            return {
                "type": "macro_directive",
                "directive": "SetZoneModifier",
                "target_faction": self.brain_faction,
                "x": cx,
                "y": cy,
                "radius": 100.0,
                "cost_modifier": -50.0,
            }

        elif action == ACTION_SPLIT_FACTION:
            cx, cy = self._get_density_centroid(self.brain_faction)
            next_id = (max(self._active_sub_factions) + 1
                       if self._active_sub_factions else 101)

            return {
                "type": "macro_directive",
                "directive": "SplitFaction",
                "source_faction": self.brain_faction,
                "new_sub_faction": next_id,
                "percentage": 0.3,
                "epicenter": [cx + 100.0, cy + 100.0],
            }

        elif action == ACTION_MERGE_FACTION:
            if self._active_sub_factions:
                sf = self._active_sub_factions[-1]
                return {
                    "type": "macro_directive",
                    "directive": "MergeFaction",
                    "source_faction": sf,
                    "target_faction": self.brain_faction,
                }
            return {"type": "macro_directive", "directive": "Hold"}

        elif action == ACTION_SET_AGGRO_MASK:
            if self._active_sub_factions:
                sf = self._active_sub_factions[-1]
                self._last_aggro_state = not self._last_aggro_state
                return {
                    "type": "macro_directive",
                    "directive": "SetAggroMask",
                    "source_faction": sf,
                    "target_faction": self.enemy_faction,
                    "allow_combat": self._last_aggro_state,
                }
            return {"type": "macro_directive", "directive": "Hold"}

        return {"type": "macro_directive", "directive": "Hold"}

    def _get_density_centroid(self, faction: int) -> tuple[float, float]:
        if self._last_snapshot is None:
            return self.world_width / 2.0, self.world_height / 2.0

        density_maps = self._last_snapshot.get("density_maps", {})
        key = str(faction)
        if key not in density_maps:
            return self.world_width / 2.0, self.world_height / 2.0

        flat = np.array(density_maps[key], dtype=np.float32)
        if len(flat) != GRID_WIDTH * GRID_HEIGHT:
            return self.world_width / 2.0, self.world_height / 2.0

        grid = flat.reshape(GRID_HEIGHT, GRID_WIDTH)
        total = grid.sum()
        if total < 0.01:
            return self.world_width / 2.0, self.world_height / 2.0

        rows, cols = np.indices(grid.shape)
        cy_cell = (rows * grid).sum() / total
        cx_cell = (cols * grid).sum() / total

        cell_w = self.world_width / GRID_WIDTH
        cell_h = self.world_height / GRID_HEIGHT
        return float(cx_cell * cell_w), float(cy_cell * cell_h)

    def _compute_reward(self, snapshot: dict, prev_snapshot: dict | None) -> float:
        from src.env.rewards import compute_shaped_reward
        return compute_shaped_reward(
            snapshot=snapshot,
            prev_snapshot=prev_snapshot,
            brain_faction=self.brain_faction,
            enemy_faction=self.enemy_faction
        )

    def close(self):
        self._disconnect()
        self._ctx.term()
