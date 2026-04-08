"""SwarmEnv — Gymnasium environment for Stage 1 Tactical Training.

3-Faction tactical scenario:
  Faction 0 (Brain): RL-controlled swarm
  Faction 1 (Patrol): Bot-controlled patrol group
  Faction 2 (Target): Bot-controlled stationary target

Debuff Mechanic: If the brain reaches the target without engaging
the patrol group, the target receives -50% HP via ActivateBuff.

Communicates with the Rust Micro-Core via ZMQ REP socket.
"""

from __future__ import annotations

import json
import logging
import numpy as np
import zmq
import gymnasium as gym

from src.config.game_profile import GameProfile, load_profile
from src.env.spaces import make_observation_space, make_action_space
from src.env.bot_controller import BotController
from src.utils.vectorizer import vectorize_snapshot

logger = logging.getLogger(__name__)


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder for numpy data types."""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


class SwarmEnv(gym.Env):
    """Gymnasium environment wrapping the Rust simulation via ZMQ.

    Supports multi-faction scenarios with multiple bot controllers.
    """

    metadata = {"render_modes": []}

    def __init__(self, config: dict | None = None):
        super().__init__()
        config = config or {}

        # ── Load Game Profile ───────────────────────────────────
        profile_path = config.get("profile_path", "profiles/stage1_tactical.json")
        if "profile" in config and isinstance(config["profile"], GameProfile):
            self.profile = config["profile"]
        else:
            self.profile = load_profile(profile_path)

        # ── Derived from profile ────────────────────────────────
        self.brain_faction = self.profile.brain_faction.id
        self.enemy_faction_ids = [f.id for f in self.profile.bot_factions]
        self.world_width = self.profile.world.width
        self.world_height = self.profile.world.height
        self.grid_width = self.profile.world.grid_width
        self.grid_height = self.profile.world.grid_height
        self.max_steps = self.profile.training.max_steps
        self.starting_entities = float(self.profile.brain_faction.default_count)

        # ── ZMQ config ──────────────────────────────────────────
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
        self._last_snapshot: dict | None = None
        self._step_count: int = 0

        # ── Multi-bot controllers (one per bot faction) ─────────
        self._bot_controllers: dict[int, BotController] = {}

        # ── Debuff tracking ─────────────────────────────────────
        self._group_a_engaged = False  # Has brain fought patrol group?
        self._debuff_applied = False   # Was debuff sent this episode?
        self._patrol_faction = 1       # Faction ID of patrol group
        self._target_faction = 2       # Faction ID of target group
        self._patrol_starting_count = 0

        self._ctx = zmq.Context()
        self._socket: zmq.Socket | None = None
        self._connect()

    def _connect(self):
        if self._socket is not None:
            self._socket.close()
        self._socket = self._ctx.socket(zmq.REP)
        self._socket.setsockopt(zmq.RCVTIMEO, self.zmq_timeout_ms)
        self._socket.setsockopt(zmq.SNDTIMEO, self.zmq_timeout_ms)
        self._socket.setsockopt(zmq.LINGER, 0)
        self._socket.bind(self.bind_address)
        self._need_initial_recv = True

    def _disconnect(self):
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def _exchange(self, msg: str) -> str | None:
        if getattr(self, "_need_initial_recv", True):
            try:
                self._socket.recv_string()
            except zmq.Again:
                return None
            self._need_initial_recv = False

        try:
            self._socket.send_string(msg)
            return self._socket.recv_string()
        except (zmq.Again, zmq.error.ZMQError):
            self._connect()
            return None

    def action_masks(self) -> np.ndarray:
        """All actions always available in Stage 1 Tactical."""
        mask = np.ones(self.profile.num_actions, dtype=bool)
        return mask

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._step_count = 0
        self._active_sub_factions = []
        self._last_snapshot = None
        self._group_a_engaged = False
        self._debuff_applied = False

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

        # Track patrol starting count from spawns
        self._patrol_starting_count = sum(
            s["count"] for s in spawns if s["faction_id"] == self._patrol_faction
        )

        # Stage 1 Tactical navigation rules:
        # - Patrol (faction 1) chases Brain (faction 0) — they're the obstacle
        # - Target (faction 2) stays stationary — no nav rule
        # - Brain (faction 0) has no auto-nav — action space controls targeting
        tactical_nav_rules = [
            {
                "follower_faction": self._patrol_faction,
                "target": {"type": "Faction", "faction_id": self.brain_faction},
            }
        ]

        payload = {
            "type": "reset_environment",
            "terrain": terrain,
            "spawns": spawns,
            "combat_rules": self.profile.combat_rules_payload(),
            "ability_config": self.profile.ability_config_payload(),
            "movement_config": self.profile.movement_config_payload(),
            "max_density": self.profile.training.max_density,
            "terrain_thresholds": self.profile.terrain_thresholds_payload(),
            "removal_rules": self.profile.removal_rules_payload(),
            "navigation_rules": tactical_nav_rules,
        }

        # Configure bot controllers for each bot faction
        self._bot_controllers = {}
        for bot_faction in self.profile.bot_factions:
            behavior = self.profile.get_bot_behavior_for_stage(
                bot_faction.id, self.curriculum_stage
            )
            controller = BotController()
            controller.configure(
                behavior=behavior,
                target_faction=self.brain_faction,
                starting_count=bot_faction.default_count,
                rng=self.np_random,
            )
            self._bot_controllers[bot_faction.id] = controller

        reply = self._exchange(json.dumps(payload, cls=NumpyEncoder))
        if reply is None:
            return self.observation_space.sample(), {}

        snapshot = json.loads(reply)
        self._last_snapshot = snapshot
        self._active_sub_factions = snapshot.get("active_sub_factions", [])

        obs = vectorize_snapshot(
            snapshot, self.brain_faction,
            enemy_factions=self.enemy_faction_ids,
        )
        return obs, {}

    def step(self, action: int):
        self._step_count += 1
        prev_snapshot = self._last_snapshot

        # Build brain directive
        brain_directive = self._action_to_directive(action)
        if isinstance(brain_directive, dict):
            brain_directive = [brain_directive]

        # Build bot directives (one per bot faction)
        bot_directives = []
        for fid, controller in self._bot_controllers.items():
            if self._last_snapshot:
                d = controller.compute_directive(self._last_snapshot)
            else:
                d = {"directive": "Idle"}
            bot_directives.append(d)

        batch = {
            "type": "macro_directives",
            "directives": brain_directive + bot_directives,
        }

        # ZMQ exchange with tick swallowing
        while True:
            reply = self._exchange(json.dumps(batch, cls=NumpyEncoder))
            if reply is None:
                obs = self.observation_space.sample()
                return obs, 0.0, False, True, {"zmq_timeout": True}

            parsed = json.loads(reply)
            if parsed.get("type") == "state_snapshot":
                snapshot = parsed
                self._last_snapshot = snapshot
                self._active_sub_factions = snapshot.get("active_sub_factions", [])
                break

            # Tick swallowing: send idle directives
            batch = {
                "type": "macro_directives",
                "directives": [{"directive": "Idle"}] * (1 + len(self._bot_controllers)),
            }

        # ── Check debuff condition ──────────────────────────────
        self._check_debuff_condition(snapshot)

        obs = vectorize_snapshot(
            snapshot, self.brain_faction,
            enemy_factions=self.enemy_faction_ids,
        )
        reward = self._compute_reward(snapshot, prev_snapshot)

        # Win: ALL enemy factions eliminated
        total_enemy = self._get_total_enemy_count(snapshot)
        own_count = self._get_own_count(snapshot)
        terminated = own_count == 0 or total_enemy == 0
        truncated = self._step_count >= self.max_steps

        info = {
            "tick": snapshot.get("tick", 0),
            "own_count": own_count,
            "enemy_count": total_enemy,
            "patrol_count": self._get_faction_count(snapshot, self._patrol_faction),
            "target_count": self._get_faction_count(snapshot, self._target_faction),
            "debuff_applied": self._debuff_applied,
            "group_a_engaged": self._group_a_engaged,
        }

        return obs, reward, terminated, truncated, info

    def _check_debuff_condition(self, snapshot: dict):
        """Track patrol engagement and apply debuff when conditions are met.

        Debuff triggers when brain attacks the target WITHOUT having
        engaged the patrol group first.

        Engagement detection uses faction_avg_stats (average HP) instead
        of entity counts. Entity counts have a "death delay" — entities
        take ~4 seconds to die, so the brain could clip the patrol,
        exchange fire, and reach the target before any patrol units die.
        Average HP updates instantly on any damage taken.
        """
        if self._debuff_applied:
            return

        # Check if patrol has been engaged via average HP drop
        avg_stats = snapshot.get("summary", {}).get("faction_avg_stats", {})
        group_a_hp = 100.0
        patrol_key = str(self._patrol_faction)
        if patrol_key in avg_stats:
            hp_list = avg_stats[patrol_key]
            group_a_hp = hp_list[0] if hp_list else 100.0

        if group_a_hp < 99.9:
            self._group_a_engaged = True

        # If brain hasn't engaged patrol, check if brain is approaching target
        if not self._group_a_engaged:
            brain_centroid = self._get_density_centroid(snapshot, self.brain_faction)
            target_centroid = self._get_density_centroid(snapshot, self._target_faction)

            if brain_centroid is not None and target_centroid is not None:
                bx, by = brain_centroid
                tx, ty = target_centroid
                dist = ((bx - tx) ** 2 + (by - ty) ** 2) ** 0.5

                if dist < 200.0:
                    # Brain reached target without engaging patrol → apply debuff
                    self._debuff_applied = True
                    self._apply_target_debuff()

    def _apply_target_debuff(self):
        """Send ActivateBuff to halve target group's HP.

        Uses the activate_buff config from the profile which is
        pre-configured with a 0.5x HP multiplier.
        """
        from dataclasses import asdict
        activate_buff = self.profile.abilities.activate_buff
        debuff_directive = {
            "type": "macro_directive",
            "directive": "ActivateBuff",
            "faction": self._target_faction,
            "modifiers": [asdict(m) for m in activate_buff.modifiers],
            "duration_ticks": activate_buff.duration_ticks,
            "targets": [],
        }
        logger.info(
            "🎯 Debuff applied! Brain reached Target without engaging Patrol. "
            "Target HP halved."
        )
        # The debuff will be sent as part of the next step's batch
        self._pending_debuff = debuff_directive

    def _action_to_directive(self, action: int) -> dict | list[dict]:
        """Map Stage 1 tactical actions to directives.

        0 = Hold (active brake — stops swarm movement)
        1 = Attack Group A (Navigate → faction 1)
        2 = Attack Group B (Navigate → faction 2)
        """
        from src.env.actions import build_hold_directive, build_update_nav_directive

        # Include pending debuff if any
        directives = []

        if hasattr(self, '_pending_debuff') and self._pending_debuff is not None:
            directives.append(self._pending_debuff)
            self._pending_debuff = None

        if action == 0:  # Hold (active brake)
            directives.append(build_hold_directive(self.brain_faction))
        elif action == 1:  # Attack Group A (Patrol)
            directives.append(build_update_nav_directive(self.brain_faction, self._patrol_faction))
        elif action == 2:  # Attack Group B (Target)
            directives.append(build_update_nav_directive(self.brain_faction, self._target_faction))
        else:
            directives.append(build_hold_directive(self.brain_faction))

        return directives if len(directives) > 1 else directives[0]

    def _get_density_centroid(self, snapshot: dict, faction: int):
        """Get faction density centroid in world coordinates."""
        from src.env.analytics import get_density_centroid
        return get_density_centroid(
            snapshot, faction,
            self.world_width, self.world_height,
            self.grid_width, self.grid_height,
        )

    def _get_faction_count(self, snapshot: dict, faction_id: int) -> int:
        counts = snapshot.get("summary", {}).get("faction_counts", {})
        return counts.get(str(faction_id), counts.get(faction_id, 0))

    def _get_own_count(self, snapshot: dict) -> int:
        return self._get_faction_count(snapshot, self.brain_faction)

    def _get_total_enemy_count(self, snapshot: dict) -> int:
        return sum(
            self._get_faction_count(snapshot, fid)
            for fid in self.enemy_faction_ids
        )

    def _compute_reward(self, snapshot: dict, prev_snapshot: dict | None) -> float:
        from src.env.rewards import compute_shaped_reward
        return compute_shaped_reward(
            snapshot=snapshot,
            prev_snapshot=prev_snapshot,
            brain_faction=self.brain_faction,
            enemy_faction=self.enemy_faction_ids,
            reward_weights=self.profile.training.rewards,
            starting_entities=self.starting_entities,
        )

    def close(self):
        self._disconnect()
        self._ctx.term()
