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
        self._trap_engaged = False     # Has brain fought trap group?
        self._debuff_applied = False   # Was debuff sent this episode?
        self._trap_faction = 1         # Faction ID of trap group (50 units)
        self._target_faction = 2       # Faction ID of target group (20 units)
        self._trap_starting_count = 0

        # ── Approach reward tracking ────────────────────────────
        self._prev_min_enemy_dist: float | None = None

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
        self._trap_engaged = False
        self._debuff_applied = False
        self._prev_min_enemy_dist = None

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

        # Track trap starting count from spawns
        self._trap_starting_count = sum(
            s["count"] for s in spawns if s["faction_id"] == self._trap_faction
        )

        # Stage 1 Tactical navigation rules:
        # NO nav rules at all. Each faction's movement is controlled by:
        # - Brain: action space (Hold/AttackA/AttackB directives)
        # - Patrol: bot controller Retreat directives (vertical patrol)
        # - Target: bot controller Idle (stays at spawn)
        # Combat is still proximity-based via combat_rules (nav ≠ combat).
        tactical_nav_rules = []

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

        # ── Approach reward (anti-toggle) ───────────────────────
        # Small per-step reward for getting closer to nearest enemy.
        # Toggling between targets = net zero progress = no reward.
        # Committing to one target = consistent positive signal.
        approach_reward = self._compute_approach_reward(snapshot)
        reward += approach_reward

        # Win: ALL enemy factions eliminated
        total_enemy = self._get_total_enemy_count(snapshot)
        own_count = self._get_own_count(snapshot)

        # Guard: first step after reset may have stale snapshot data
        # from the Rust side. Don't terminate on step 1.
        if self._step_count <= 1:
            terminated = False
        else:
            terminated = own_count == 0 or total_enemy == 0
        truncated = self._step_count >= self.max_steps

        # Timeout penalty: treat timeout as a loss to prevent
        # "kill patrol + hold until timeout" exploit.
        # Without this: timeout ≈ -4.0      loss ≈ -11.0 (model avoids target)
        # With this:    timeout ≈ -14.0      loss ≈ -11.0 (model must fight target)
        if truncated and not terminated:
            reward += self.profile.training.rewards.loss_terminal

        info = {
            "tick": snapshot.get("tick", 0),
            "own_count": own_count,
            "enemy_count": total_enemy,
            "trap_count": self._get_faction_count(snapshot, self._trap_faction),
            "target_count": self._get_faction_count(snapshot, self._target_faction),
            "debuff_applied": self._debuff_applied,
            "trap_engaged": self._trap_engaged,
        }

        return obs, reward, terminated, truncated, info

    def _check_debuff_condition(self, snapshot: dict):
        """Apply debuff when Target is eliminated while Trap is still alive.

        Simple rule: if target_count == 0 and trap is still mostly alive,
        the brain chose the correct target first → reward with debuff.

        Previous design tracked "engagement" (any HP loss on trap) but
        this was too strict — random exploration always clips the trap
        briefly, permanently setting trap_engaged=True.

        The new rule captures the real objective: "kill the small group
        first, then the big group collapses."
        """
        # Track trap engagement for logging (not for debuff gating)
        avg_stats = snapshot.get("summary", {}).get("faction_avg_stats", {})
        trap_key = str(self._trap_faction)
        if trap_key in avg_stats:
            hp_list = avg_stats[trap_key]
            trap_hp = hp_list[0] if hp_list else 100.0
            if trap_hp < 99.9:
                self._trap_engaged = True

        trap_count = self._get_faction_count(snapshot, self._trap_faction)
        if trap_count < self._trap_starting_count:
            self._trap_engaged = True

        # Only apply debuff once
        if self._debuff_applied:
            return

        # Debuff fires when: Target eliminated AND Trap still has
        # at least half its starting units alive (didn't primarily fight trap)
        target_count = self._get_faction_count(snapshot, self._target_faction)
        trap_threshold = self._trap_starting_count * 0.5  # at least half alive

        if target_count == 0 and trap_count >= trap_threshold:
            self._debuff_applied = True
            self._apply_trap_debuff()

    def _apply_trap_debuff(self):
        """Send ActivateBuff to halve the Trap group's HP.

        Uses the activate_buff config from the profile which is
        pre-configured with a 0.5x HP multiplier.
        """
        from dataclasses import asdict
        activate_buff = self.profile.abilities.activate_buff
        debuff_directive = {
            "type": "macro_directive",
            "directive": "ActivateBuff",
            "faction": self._trap_faction,
            "modifiers": [asdict(m) for m in activate_buff.modifiers],
            "duration_ticks": activate_buff.duration_ticks,
            "targets": [],
        }
        logger.info(
            "🎯 Debuff applied! Brain killed Target first → Trap HP halved."
        )
        self._pending_debuff = debuff_directive

    def _get_enemy_factions_by_distance(self, snapshot: dict) -> list[int]:
        """Return enemy faction IDs sorted by distance from brain centroid.

        Nearest first, furthest last. Only includes alive factions.
        """
        brain_c = self._get_density_centroid(snapshot, self.brain_faction)
        if brain_c is None:
            return list(self.enemy_faction_ids)

        bx, by = brain_c
        distances = []
        for fid in self.enemy_faction_ids:
            count = self._get_faction_count(snapshot, fid)
            if count <= 0:
                continue
            ec = self._get_density_centroid(snapshot, fid)
            if ec is None:
                continue
            ex, ey = ec
            dist = ((bx - ex) ** 2 + (by - ey) ** 2) ** 0.5
            distances.append((fid, dist))

        distances.sort(key=lambda x: x[1])
        return [fid for fid, _ in distances]

    def _action_to_directive(self, action: int) -> dict | list[dict]:
        """Map Stage 1 actions to directives.

        0 = Hold (active brake — stops swarm movement)
        1 = Attack Nearest (navigate to closest alive enemy faction)
        2 = Attack Furthest (navigate to farthest alive enemy faction)
        """
        from src.env.actions import build_hold_directive, build_update_nav_directive

        # Include pending debuff if any
        directives = []

        if hasattr(self, '_pending_debuff') and self._pending_debuff is not None:
            directives.append(self._pending_debuff)
            self._pending_debuff = None

        if action == 0:  # Hold (active brake)
            directives.append(build_hold_directive(self.brain_faction))
        elif action == 1:  # Attack Nearest
            sorted_factions = self._get_enemy_factions_by_distance(
                self._last_snapshot or {}
            )
            target = sorted_factions[0] if sorted_factions else self._target_faction
            directives.append(build_update_nav_directive(self.brain_faction, target))
        elif action == 2:  # Attack Furthest
            sorted_factions = self._get_enemy_factions_by_distance(
                self._last_snapshot or {}
            )
            target = sorted_factions[-1] if sorted_factions else self._trap_faction
            directives.append(build_update_nav_directive(self.brain_faction, target))
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

    def _compute_approach_reward(self, snapshot: dict) -> float:
        """Reward for getting closer to the nearest enemy.

        Prevents the toggle exploit: zig-zagging between two targets
        produces net-zero distance change = zero approach reward.
        Committing to one target = consistent positive signal per step.

        Scale: 0.02 per world unit of distance closed.
        At movement speed 60 units/sec and 30 ticks/eval = 0.5 sec/step:
          max approach per step ≈ 30 units → max reward ≈ 0.6/step
          This dominates the -0.01 time penalty, making approach always
          better than standing still.
        """
        APPROACH_SCALE = 0.02  # reward per world unit closer

        brain_c = self._get_density_centroid(snapshot, self.brain_faction)
        if brain_c is None:
            return 0.0

        # Find minimum distance to any alive enemy faction
        bx, by = brain_c
        min_dist = float("inf")
        for fid in self.enemy_faction_ids:
            if self._get_faction_count(snapshot, fid) <= 0:
                continue
            ec = self._get_density_centroid(snapshot, fid)
            if ec is None:
                continue
            ex, ey = ec
            dist = ((bx - ex) ** 2 + (by - ey) ** 2) ** 0.5
            min_dist = min(min_dist, dist)

        if min_dist == float("inf"):
            self._prev_min_enemy_dist = None
            return 0.0

        # Compute delta (positive = approaching, negative = retreating)
        reward = 0.0
        if self._prev_min_enemy_dist is not None:
            delta = self._prev_min_enemy_dist - min_dist  # positive when closing
            reward = delta * APPROACH_SCALE

        self._prev_min_enemy_dist = min_dist
        return reward

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
