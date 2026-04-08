"""SwarmEnv — Gymnasium environment for Mass-Swarm AI Simulator.

All game parameters come from the GameProfile contract.
No hardcoded constants — swap the profile to train a different game.

Communicates with the Rust Micro-Core via ZMQ REP socket.

## SAFETY INVARIANTS (v3 Patches)
P6: Dynamic epicenter from density centroid (not hardcoded)
P7: Sub-faction state read from Rust snapshot (single source of truth)
P8: ZMQ timeout → episode truncation; Tick swallowing for interventions
"""

from __future__ import annotations

import json
import numpy as np
import zmq
import gymnasium as gym

from src.config.game_profile import GameProfile, load_profile
from src.env.spaces import (
    make_observation_space, make_action_space,
    ACTION_HOLD, ACTION_UPDATE_NAV, ACTION_ACTIVATE_BUFF, ACTION_RETREAT,
    ACTION_ZONE_MODIFIER, ACTION_SPLIT_FACTION, ACTION_MERGE_FACTION,
    ACTION_SET_AGGRO_MASK,
)
from src.env.bot_controller import BotController
from src.utils.vectorizer import vectorize_snapshot


class SwarmEnv(gym.Env):
    """Gymnasium environment wrapping the Rust simulation via ZMQ.

    All game parameters (factions, combat rules, abilities, rewards,
    actions, observation dimensions) are read from the GameProfile.
    """

    metadata = {"render_modes": []}

    def __init__(self, config: dict | None = None):
        super().__init__()
        config = config or {}

        # ── Load Game Profile ───────────────────────────────────
        profile_path = config.get("profile_path", "profiles/default_swarm_combat.json")
        if "profile" in config and isinstance(config["profile"], GameProfile):
            self.profile = config["profile"]
        else:
            self.profile = load_profile(profile_path)

        # ── Derived from profile ────────────────────────────────
        self.brain_faction = self.profile.brain_faction.id
        self.enemy_faction = self.profile.bot_factions[0].id
        self.world_width = self.profile.world.width
        self.world_height = self.profile.world.height
        self.grid_width = self.profile.world.grid_width
        self.grid_height = self.profile.world.grid_height
        self.max_steps = self.profile.training.max_steps
        self.starting_entities = float(self.profile.brain_faction.default_count)

        # ── ZMQ config (not game-specific) ──────────────────────
        self.bind_address = config.get("bind_address", "tcp://*:5555")
        self.zmq_timeout_ms = config.get("zmq_timeout_ms", 10000)
        self.curriculum_stage = config.get("curriculum_stage", 1)

        # ── Spaces from profile ─────────────────────────────────
        self.observation_space = make_observation_space(
            grid_width=self.grid_width,
            grid_height=self.grid_height,
            num_density_channels=self.profile.training.observation_channels - 1,
        )
        self.action_space = make_action_space(
            num_actions=self.profile.num_actions,
        )

        self._active_sub_factions: list[int] = []
        self._last_aggro_state: bool = True
        self._last_snapshot: dict | None = None
        self._step_count: int = 0

        self._bot_controller = BotController()

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
        """Progressive action unlocking per curriculum stage.

        Reads unlock_stage from the profile's action definitions.
        Runtime masking: Merge/Aggro disabled when no sub-factions exist.
        """
        mask = np.zeros(self.profile.num_actions, dtype=bool)

        for action_def in self.profile.actions:
            if action_def.unlock_stage <= self.curriculum_stage:
                mask[action_def.index] = True

        # Runtime: can't merge/aggro without sub-factions
        if not self._active_sub_factions:
            if ACTION_MERGE_FACTION < len(mask):
                mask[ACTION_MERGE_FACTION] = False
            if ACTION_SET_AGGRO_MASK < len(mask):
                mask[ACTION_SET_AGGRO_MASK] = False

        return mask

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._step_count = 0
        self._active_sub_factions = []
        self._last_aggro_state = True
        self._last_snapshot = None

        try:
            self._socket.recv_string()
        except zmq.Again:
            return self.observation_space.sample(), {}

        # Cycle 1: send ResetEnvironment with profile-derived payloads
        from src.utils.terrain_generator import generate_terrain_for_stage
        from src.training.curriculum import get_spawns_for_stage

        terrain = generate_terrain_for_stage(
            self.curriculum_stage,
            seed=int(self.np_random.integers(0, 2**31)),
        )
        spawns = get_spawns_for_stage(
            self.curriculum_stage,
            rng=self.np_random,
            profile=self.profile,
        )

        # Include combat rules and ability config from profile
        self._socket.send_string(json.dumps({
            "type": "reset_environment",
            "terrain": terrain,
            "spawns": spawns,
            "combat_rules": self.profile.combat_rules_payload(),
            "ability_config": self.profile.ability_config_payload(),
            "movement_config": self.profile.movement_config_payload(),
            "max_density": self.profile.training.max_density,
            "terrain_thresholds": self.profile.terrain_thresholds_payload(),
            "removal_rules": self.profile.removal_rules_payload(),
            "navigation_rules": self.profile.navigation_rules_payload(),
            "bot_behaviors": self.profile.bot_behaviors_payload(self.curriculum_stage),
        }))

        bot_behavior = self.profile.get_bot_behavior_for_stage(
            self.enemy_faction, self.curriculum_stage
        )
        self._bot_controller.configure(
            behavior=bot_behavior,
            target_faction=self.brain_faction,
            starting_count=int(self.profile.bot_factions[0].default_count),
            rng=self.np_random,
        )

        # Cycle 2: recv fresh post-reset snapshot → send Hold
        try:
            raw_snapshot = self._socket.recv_string()
        except zmq.Again:
            return self.observation_space.sample(), {}

        snapshot = json.loads(raw_snapshot)
        self._last_snapshot = snapshot

        # P7: Read sub-faction state from Rust (single source of truth)
        self._active_sub_factions = snapshot.get("active_sub_factions", [])

        obs = vectorize_snapshot(snapshot, self.brain_faction)
        hold_batch = {
            "type": "macro_directives",
            "directives": [{"directive": "Hold"}, {"directive": "Hold"}]
        }
        self._socket.send_string(json.dumps(hold_batch))
        return obs, {}

    def step(self, action: int):
        self._step_count += 1

        # Cycle 1: recv snapshot
        try:
            raw_snapshot = self._socket.recv_string()
        except zmq.Again:
            obs = self.observation_space.sample()
            return obs, 0.0, False, True, {"zmq_timeout": True}

        snapshot = json.loads(raw_snapshot)
        prev_snapshot = self._last_snapshot
        self._last_snapshot = snapshot

        # P7: Sync sub-factions from Rust snapshot
        self._active_sub_factions = snapshot.get("active_sub_factions", [])

        # Build and send directive
        brain_directive = self._action_to_directive(action)
        bot_directive = self._bot_controller.compute_directive(snapshot)
        bot_directive = self._validate_bot_directive(bot_directive)

        batch = {
            "type": "macro_directives",
            "directives": [brain_directive, bot_directive],
        }

        # P8: Tick swallowing for engine interventions
        while True:
            self._socket.send_string(json.dumps(batch))
            try:
                maybe_tick = self._socket.recv_string()
            except zmq.Again:
                obs = self.observation_space.sample()
                return obs, 0.0, False, True, {"zmq_timeout": True}
            parsed = json.loads(maybe_tick)
            if parsed.get("type") == "state_snapshot":
                snapshot = parsed
                self._last_snapshot = snapshot
                self._active_sub_factions = snapshot.get("active_sub_factions", [])
                break
            batch = {
                "type": "macro_directives",
                "directives": [{"directive": "Hold"}, {"directive": "Hold"}]
            }

        obs = vectorize_snapshot(snapshot, self.brain_faction)
        reward = self._compute_reward(snapshot, prev_snapshot)
        flanking = self._compute_flanking(snapshot)

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
            "flanking_bonus": flanking,
        }

        return obs, reward, terminated, truncated, info

    def _validate_bot_directive(self, directive: dict) -> dict:
        """PATCH 2: Prevent bot from hijacking brain faction.

        Checks all faction-referencing fields in the directive.
        If ANY field targets the brain faction, the entire directive
        is replaced with Hold and a warning is logged.
        """
        import logging
        faction_fields = [
            "follower_faction", "faction", "source_faction", "target_faction"
        ]
        brain_id = self.profile.brain_faction.id

        for field in faction_fields:
            if directive.get(field) == brain_id:
                logging.getLogger(__name__).warning(
                    f"Bot directive tried to control brain faction {brain_id} "
                    f"via '{field}' — BLOCKED. Directive: {directive}"
                )
                return {"directive": "Hold"}

        return directive

    def _action_to_directive(self, action: int) -> dict:
        """Map discrete action index to MacroDirective JSON.

        Buff parameters come from profile.abilities.activate_buff.
        """
        activate_buff = self.profile.abilities.activate_buff
        
        from src.env.actions import (
            build_hold_directive, build_update_nav_directive,
            build_activate_buff_directive, build_retreat_directive,
            build_set_zone_modifier_directive, build_split_faction_directive,
            build_merge_faction_directive, build_set_aggro_mask_directive
        )

        if action == ACTION_HOLD:
            return build_hold_directive()

        elif action == ACTION_UPDATE_NAV:
            return build_update_nav_directive(self.brain_faction, self.enemy_faction)

        elif action == ACTION_ACTIVATE_BUFF:
            return build_activate_buff_directive(self.brain_faction, activate_buff)

        elif action == ACTION_RETREAT:
            cx, cy = self._get_density_centroid(self.brain_faction)
            ex, ey = self._get_density_centroid(self.enemy_faction)

            if cx is None or ex is None:
                return build_hold_directive()

            dx = cx - ex
            dy = cy - ey
            length = (dx**2 + dy**2)**0.5

            if length < 0.001:
                dx, dy = 1.0, 0.0
            else:
                dx, dy = dx / length, dy / length

            retreat_x = max(50.0, min(self.world_width - 50.0, cx + dx * 200.0))
            retreat_y = max(50.0, min(self.world_height - 50.0, cy + dy * 200.0))

            return build_retreat_directive(self.brain_faction, retreat_x, retreat_y)

        elif action == ACTION_ZONE_MODIFIER:
            cx, cy = self._get_density_centroid(self.brain_faction)
            return build_set_zone_modifier_directive(self.brain_faction, cx, cy)

        elif action == ACTION_SPLIT_FACTION:
            cx, cy = self._get_density_centroid(self.brain_faction)
            next_id = (max(self._active_sub_factions) + 1
                       if self._active_sub_factions else 101)

            return build_split_faction_directive(
                self.brain_faction, next_id, 0.3, [cx + 100.0, cy + 100.0]
            )

        elif action == ACTION_MERGE_FACTION:
            if self._active_sub_factions:
                sf = self._active_sub_factions[-1]
                return build_merge_faction_directive(sf, self.brain_faction)
            return build_hold_directive()

        elif action == ACTION_SET_AGGRO_MASK:
            if self._active_sub_factions:
                sf = self._active_sub_factions[-1]
                self._last_aggro_state = not self._last_aggro_state
                return build_set_aggro_mask_directive(sf, self.enemy_faction, self._last_aggro_state)
            return build_hold_directive()

        return build_hold_directive()

    def _get_density_centroid(self, faction: int) -> tuple[float, float]:
        from src.env.analytics import get_density_centroid
        return get_density_centroid(
            self._last_snapshot, faction,
            self.world_width, self.world_height,
            self.grid_width, self.grid_height,
        )

    def _compute_flanking(self, snapshot: dict) -> float:
        from src.env.analytics import compute_flanking
        return compute_flanking(
            snapshot, self.brain_faction, self.enemy_faction,
            self._active_sub_factions, self.grid_width, self.grid_height,
        )

    def _compute_reward(self, snapshot: dict, prev_snapshot: dict | None) -> float:
        from src.env.rewards import compute_shaped_reward
        return compute_shaped_reward(
            snapshot=snapshot,
            prev_snapshot=prev_snapshot,
            brain_faction=self.brain_faction,
            enemy_faction=self.enemy_faction,
            reward_weights=self.profile.training.rewards,
            starting_entities=self.starting_entities,
        )

    def close(self):
        self._disconnect()
        self._ctx.term()
