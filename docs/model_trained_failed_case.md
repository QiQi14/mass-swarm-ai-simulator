# Stage 1 — Target Selection: Training Results & Walkthrough

## Training Summary

| Metric | Value |
|--------|-------|
| Total episodes | 3,642 |
| Total timesteps | 1,001,449 |
| Overall win rate | 45.0% |
| Peak rolling-100 win rate | **73.0%** (episode 2576) |
| Final rolling-100 win rate | **12.0%** (collapsed) |
| Training time | ~5.5 hours |

## Win Rate Progression

```
Ep   200: 48%  ██████████████████████████████████████████████████
Ep   400: 57%  ██████████████████████████████████████████████████████████
Ep   800: 50%  ██████████████████████████████████████████████████████
Ep  1400: 56%  ████████████████████████████████████████████████████████
Ep  1800: 58%  ██████████████████████████████████████████████████████████
Ep  2200: 64%  █████████████████████████████████████████████████████████████████
Ep  2600: 69%  ██████████████████████████████████████████████████████████████████████
Ep  2800: 70%  ██████████████████████████████████████████████████████████████████████   ← PEAK
Ep  3000: 33%  ██████████████████████████████████  ← COLLAPSE
Ep  3200:  9%  █████████
Ep  3600: 11%  ███████████
```

## Entropy Collapse Diagnosis

The model **collapsed to 100% AttackFurthest** around episode 3000:

| Period | Hold | AttackNearest | AttackFurthest | Win Rate |
|--------|------|---------------|----------------|----------|
| Ep 500 | 11% | 63% | 26% | 48% |
| Ep 1500 | 3% | 68% | 29% | 56% |
| **Ep 2500** | **0%** | **38%** | **62%** | **69%** |
| Ep 3000 | 0% | 1% | **99%** | 33% |
| Ep 3500 | 0% | 0% | **100%** | 11% |

### Why This Happened

1. AttackFurthest targets the correct group (Target at FAR position) in **50% of episodes**
2. Those 50% produce wins (+15 reward) → strong positive signal
3. PPO's policy gradient pushes AttackFurthest probability higher
4. AttackNearest probability drops → fewer exploration samples → less counter-evidence
5. Entropy collapses → model becomes deterministic → can't adapt to the other 50%

### Root Cause

The model never learned to **read the density grid** to distinguish Target (20 units, less dense) from Trap (50 units, more dense). It learned a **positional bias** instead: "AttackFurthest often leads to Target → win." This is the naive strategy, not the conditional decision we wanted.

> [!WARNING]
> **The feature extractor did NOT learn density discrimination.** The model learned a spatial shortcut instead. This needs to be fixed before moving to Stage 2.

---

## Changes Made During This Session

### 1. Universal Action Set

```diff:swarm_env.py
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
    ACTION_IDLE, ACTION_HOLD, ACTION_UPDATE_NAV, ACTION_ACTIVATE_BUFF, ACTION_RETREAT,
    ACTION_ZONE_MODIFIER, ACTION_SPLIT_FACTION, ACTION_MERGE_FACTION,
    ACTION_SET_AGGRO_MASK,
)
from src.env.bot_controller import BotController
from src.utils.vectorizer import vectorize_snapshot


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
        self._need_initial_recv = True

    def _disconnect(self):
        """Close and unbind the socket."""
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def _exchange(self, msg: str) -> str | None:
        """bulletproof strict alternating REP cycle."""
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
            # Broken sequence. Recreate socket to heal.
            self._connect()
            return None

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
            "navigation_rules": self.profile.navigation_rules_payload(),
            "bot_behaviors": self.profile.bot_behaviors_payload(self.curriculum_stage),
        }

        bot_behavior = self.profile.get_bot_behavior_for_stage(
            self.enemy_faction, self.curriculum_stage
        )
        self._bot_controller.configure(
            behavior=bot_behavior,
            target_faction=self.brain_faction,
            starting_count=int(self.profile.bot_factions[0].default_count),
            rng=self.np_random,
        )

        reply = self._exchange(json.dumps(payload, cls=NumpyEncoder))
        if reply is None:
            return self.observation_space.sample(), {}

        snapshot = json.loads(reply)
        self._last_snapshot = snapshot

        # P7: Read sub-faction state from Rust (single source of truth)
        self._active_sub_factions = snapshot.get("active_sub_factions", [])

        obs = vectorize_snapshot(snapshot, self.brain_faction)
        return obs, {}

    def step(self, action: int):
        self._step_count += 1

        prev_snapshot = self._last_snapshot

        # Build and send directive
        brain_directives = self._action_to_directive(action)
        if isinstance(brain_directives, dict):
            brain_directives = [brain_directives]
            
        bot_directive = self._bot_controller.compute_directive(self._last_snapshot) if self._last_snapshot else {"directive": "Hold"}
        bot_directive = self._validate_bot_directive(bot_directive)

        batch = {
            "type": "macro_directives",
            "directives": brain_directives + [bot_directive],
        }

        # P8: Tick swallowing for engine interventions
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

    def _action_to_directive(self, action: int) -> dict | list[dict]:
        """Map discrete action index to MacroDirective JSON.

        Buff parameters come from profile.abilities.activate_buff.
        """
        activate_buff = self.profile.abilities.activate_buff
        
        from src.env.actions import (
            build_idle_directive, build_hold_directive, build_update_nav_directive,
            build_activate_buff_directive, build_retreat_directive,
            build_set_zone_modifier_directive, build_split_faction_directive,
            build_merge_faction_directive, build_set_aggro_mask_directive
        )

        if action == ACTION_IDLE:
            return build_idle_directive()

        elif action == ACTION_HOLD:
            return build_hold_directive(self.brain_faction)

        elif action == ACTION_UPDATE_NAV:
            return build_update_nav_directive(self.brain_faction, self.enemy_faction)

        elif action == ACTION_ACTIVATE_BUFF:
            return [build_activate_buff_directive(f, activate_buff) 
                    for f in [self.brain_faction] + self._active_sub_factions]

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
===
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
```

Replaced hardcoded `AttackA`/`AttackB` (faction-specific) with `AttackNearest`/`AttackFurthest` (distance-based, universal). Dynamic targeting computed from density centroids each step.

### 2. Position Randomization

```diff:curriculum.py
"""Mastery-Based Curriculum Learning with Demotion Safety Net.

All curriculum thresholds and spawn configurations are read from the
GameProfile contract. No hardcoded stage configs — swap the profile
to change the curriculum.

Implements the "Proof of Mechanic Mastery" transition matrix to prevent
the Lazy Agent / Deathball Fallacy — where an agent gets promoted by
brute-forcing wins without learning the new mechanics.

Each stage transition requires:
  1. Statistical win rate threshold
  2. Decisive victory proof (avg survivors)
  3. Mechanic usage proof (action distribution checks)
  4. Minimum episode count for statistical significance

Demotion: If win rate drops below the floor for N episodes after promotion,
the agent is demoted to rebuild confidence (prevents Catastrophic Forgetting).
"""

from __future__ import annotations

import random
from collections import deque
from typing import TYPE_CHECKING

from stable_baselines3.common.callbacks import BaseCallback

if TYPE_CHECKING:
    from src.config.game_profile import GameProfile


# Action names — stable protocol indices (used by callbacks for display)
ACTION_NAMES = [
    "Hold", "Navigate", "Frenzy", "Retreat",
    "ZoneModifier", "SplitFaction", "MergeFaction", "SetAggroMask"
]


# ── Spawn Configurations ────────────────────────────────────────────
# All spawn generators accept an optional `profile` to read entity
# counts and stats. Falls back to hardcoded defaults if no profile.

def _faction_stats(profile: GameProfile | None, faction_id: int) -> list[dict]:
    """Get stat initializer from profile or default 100 HP."""
    if profile is not None:
        for f in profile.factions:
            if f.id == faction_id:
                return [{"index": 0, "value": f.stats.hp}]
    return [{"index": 0, "value": 100.0}]


def _faction_count(profile: GameProfile | None, faction_id: int) -> int:
    """Get default entity count from profile or 50."""
    if profile is not None:
        for f in profile.factions:
            if f.id == faction_id:
                return f.default_count
    return 50


def get_stage1_spawns(profile: GameProfile | None = None):
    """Asymmetric geometry: Teach Defeat in Detail (Lanchester's Square Law)

    Swarm spawns as one large group centrally.
    Defenders spawn as two separated groups (top and bottom corners).
    If Swarm holds or charges the middle, both enemy groups converge and overwhelm.
    If Swarm navigates to intercept one group early, it wins decisively via focus-fire.
    """
    brain_count = _faction_count(profile, 0)
    bot_count = _faction_count(profile, 1)

    half_bot = bot_count // 2

    return [
        {"faction_id": 0, "count": brain_count, "x": 250.0, "y": 500.0, "spread": 60.0,
         "stats": _faction_stats(profile, 0)},
        {"faction_id": 1, "count": half_bot, "x": 750.0, "y": 200.0, "spread": 40.0,
         "stats": _faction_stats(profile, 1)},
        {"faction_id": 1, "count": bot_count - half_bot, "x": 750.0, "y": 800.0, "spread": 40.0,
         "stats": _faction_stats(profile, 1)},
    ]


def get_stage2_spawns(rng=None, profile: GameProfile | None = None):
    """Scattered defenders: 2-3 groups in randomized positions.

    Forces the model to learn:
      - Target prioritization (which cluster to attack first)
      - Army concentration (don't split your force equally)
      - Retreat timing (disengage from one group to hit another)
    """
    if rng is None:
        rng = random

    brain_count = _faction_count(profile, 0)
    bot_count = _faction_count(profile, 1)

    swarm_y = rng.uniform(300.0, 700.0)
    spawns = [
        {"faction_id": 0, "count": brain_count, "x": 200.0, "y": swarm_y, "spread": 60.0,
         "stats": _faction_stats(profile, 0)},
    ]

    # Scatter defenders into 2-3 groups
    num_groups = rng.choice([2, 3])
    counts = _split_count(bot_count, num_groups)
    positions = _generate_scattered_positions(num_groups, rng)

    for count, (px, py) in zip(counts, positions):
        spawns.append({
            "faction_id": 1, "count": count,
            "x": px, "y": py, "spread": 40.0,
            "stats": _faction_stats(profile, 1),
        })

    return spawns


def get_stage3_spawns(rng=None, profile: GameProfile | None = None):
    """Stage 3: Both factions on opposite sides of the wall.

    Swarm spawns on the left. Defenders spawn on the right as 2 groups
    (one above, one below the wall's gap). Forces the agent to learn
    SplitFaction to attack both groups simultaneously.
    """
    if rng is None:
        rng = random

    brain_count = _faction_count(profile, 0)
    bot_count = _faction_count(profile, 1)

    swarm_y = rng.uniform(350.0, 650.0)
    spawns = [
        {"faction_id": 0, "count": brain_count, "x": 200.0, "y": swarm_y, "spread": 60.0,
         "stats": _faction_stats(profile, 0)},
    ]

    # Defenders: 2 groups on the right side
    half = bot_count // 2
    positions = [
        (rng.uniform(600.0, 850.0), rng.uniform(200.0, 400.0)),
        (rng.uniform(600.0, 850.0), rng.uniform(600.0, 800.0)),
    ]
    counts = [half, bot_count - half]

    for count, (px, py) in zip(counts, positions):
        spawns.append({
            "faction_id": 1, "count": count,
            "x": px, "y": py, "spread": 40.0,
            "stats": _faction_stats(profile, 1),
        })

    return spawns


def get_stage4_spawns(rng=None, profile: GameProfile | None = None):
    """Stage 4: Fully randomized positions on opposite sides.

    Both factions can spawn anywhere in their half of the map.
    Defenders split into 2-4 groups at random.
    """
    if rng is None:
        rng = random

    brain_count = _faction_count(profile, 0)
    bot_count = _faction_count(profile, 1)

    swarm_x = rng.uniform(100.0, 300.0)
    swarm_y = rng.uniform(150.0, 850.0)
    spawns = [
        {"faction_id": 0, "count": brain_count, "x": swarm_x, "y": swarm_y, "spread": 60.0,
         "stats": _faction_stats(profile, 0)},
    ]

    num_groups = rng.choice([2, 3, 4])
    counts = _split_count(bot_count, num_groups)
    positions = _generate_scattered_positions(num_groups, rng)

    for count, (px, py) in zip(counts, positions):
        spawns.append({
            "faction_id": 1, "count": count,
            "x": px, "y": py, "spread": 40.0,
            "stats": _faction_stats(profile, 1),
        })

    return spawns


def get_stage5_spawns(rng=None, profile: GameProfile | None = None):
    """Stage 5: Fully random spawns for both factions.

    Both factions can appear anywhere. Multiple groups per faction.
    Forces the agent to handle arbitrary starting conditions.
    """
    if rng is None:
        rng = random

    brain_count = _faction_count(profile, 0)
    bot_count = _faction_count(profile, 1)

    # Brain: 1-2 spawn groups, random positions
    brain_groups = rng.choice([1, 2])
    brain_counts = _split_count(brain_count, brain_groups)
    spawns = []
    for count in brain_counts:
        spawns.append({
            "faction_id": 0,
            "count": count,
            "x": rng.uniform(100.0, 900.0),
            "y": rng.uniform(100.0, 900.0),
            "spread": 60.0,
            "stats": _faction_stats(profile, 0),
        })

    # Bot: 2-4 spawn groups, random positions
    bot_groups = rng.choice([2, 3, 4])
    bot_counts = _split_count(bot_count, bot_groups)
    positions = _generate_scattered_positions(bot_groups, rng)
    for count, (px, py) in zip(bot_counts, positions):
        spawns.append({
            "faction_id": 1, "count": count,
            "x": px, "y": py, "spread": 40.0,
            "stats": _faction_stats(profile, 1),
        })

    return spawns


def _split_count(total, num_groups):
    """Split total into num_groups with minimum 5 per group."""
    min_per = max(1, total // (num_groups * 2))
    counts = [min_per] * num_groups
    remaining = total - sum(counts)
    for _ in range(remaining):
        counts[random.randint(0, num_groups - 1)] += 1
    return counts


def _generate_scattered_positions(num_groups, rng):
    """Generate scattered positions for defender groups."""
    positions = []
    min_spacing = 200.0

    for _ in range(num_groups):
        for _attempt in range(50):
            x = rng.uniform(550.0, 900.0)
            y = rng.uniform(150.0, 850.0)
            too_close = any(
                ((x - px) ** 2 + (y - py) ** 2) ** 0.5 < min_spacing
                for px, py in positions
            )
            if not too_close:
                positions.append((x, y))
                break
        else:
            positions.append((rng.uniform(550.0, 900.0), rng.uniform(150.0, 850.0)))

    return positions


def get_spawns_for_stage(
    stage: int,
    rng=None,
    profile: GameProfile | None = None,
):
    """Dispatch to the correct spawn generator based on curriculum stage."""
    if stage <= 1:
        return get_stage1_spawns(profile=profile)
    elif stage == 2:
        return get_stage2_spawns(rng=rng, profile=profile)
    elif stage == 3:
        return get_stage3_spawns(rng=rng, profile=profile)
    elif stage == 4:
        return get_stage4_spawns(rng=rng, profile=profile)
    else:  # Stage 5+
        return get_stage5_spawns(rng=rng, profile=profile)

===
"""Stage 1 Curriculum — Target Selection Training.

Brain (50) vs Trap (50) vs Target (20).
Positions randomized each episode to prevent memorization.
Kill Target (smaller) first → Trap gets -50% HP debuff → easy cleanup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from numpy.random import Generator
    from src.config.game_profile import GameProfile


# Action names for Stage 1 (3-action space)
ACTION_NAMES = ["Hold", "AttackNearest", "AttackFurthest"]

# Two candidate spawn positions (distances differ from center)
# Brain spawns at center (500, 500).
# "Near" position: 200 units from center
# "Far" position: 350 units from center
POSITION_NEAR = (700.0, 500.0)   # right of center, 200 units away
POSITION_FAR  = (500.0, 150.0)   # above center, 350 units away


def _faction_stats(profile: GameProfile | None, faction_id: int) -> list[dict]:
    """Get stat initializer from profile or default 100 HP."""
    if profile is not None:
        for f in profile.factions:
            if f.id == faction_id:
                return [{"index": 0, "value": f.stats.hp}]
    return [{"index": 0, "value": 100.0}]


def _faction_count(profile: GameProfile | None, faction_id: int) -> int:
    """Get default entity count from profile or defaults."""
    if profile is not None:
        for f in profile.factions:
            if f.id == faction_id:
                return f.default_count
    return 50


def get_stage1_spawns(
    profile: GameProfile | None = None,
    rng: Generator | None = None,
):
    """Stage 1 Target Selection: randomized 3-faction spawn layout.

    Brain (faction 0): center, always at (500, 500).
    Trap  (faction 1): 50 units, randomized to NEAR or FAR position.
    Target(faction 2): 20 units, gets the OTHER position.

    50% of episodes: Target is nearest → AttackNearest is correct
    50% of episodes: Target is furthest → AttackFurthest is correct

    This forces the model to READ the density grid to identify the
    smaller cluster, not memorize a fixed position.
    """
    brain_count = _faction_count(profile, 0)
    trap_count = _faction_count(profile, 1)
    target_count = _faction_count(profile, 2)

    # Randomize positions
    if rng is not None and rng.random() < 0.5:
        trap_pos = POSITION_NEAR
        target_pos = POSITION_FAR
    else:
        trap_pos = POSITION_FAR
        target_pos = POSITION_NEAR

    return [
        {"faction_id": 0, "count": brain_count,
         "x": 500.0, "y": 500.0, "spread": 60.0,
         "stats": _faction_stats(profile, 0)},
        {"faction_id": 1, "count": trap_count,
         "x": trap_pos[0], "y": trap_pos[1], "spread": 60.0,
         "stats": _faction_stats(profile, 1)},
        {"faction_id": 2, "count": target_count,
         "x": target_pos[0], "y": target_pos[1], "spread": 40.0,
         "stats": _faction_stats(profile, 2)},
    ]


def get_spawns_for_stage(
    stage: int,
    rng=None,
    profile: GameProfile | None = None,
):
    """Dispatch to the correct spawn generator based on curriculum stage."""
    return get_stage1_spawns(profile=profile, rng=rng)

```

Each episode randomly swaps Trap and Target between NEAR (700,500) and FAR (500,150) positions. Forces model to read density grid, not memorize positions.

### 3. Approach Reward (Anti-Toggle Fix)

Added per-step reward for closing distance to nearest enemy. Fixed the toggle exploit where the model zig-zagged between groups to avoid combat while collecting minimal time penalties.

```python
def _compute_approach_reward(self, snapshot):
    """delta = prev_distance - current_distance; reward = delta * 0.02"""
```

### 4. Debuff Condition Fix

Old: `target_count == 0 AND NOT trap_engaged` → never fired (random exploration always clips trap)
New: `target_count == 0 AND trap_count >= 50%` → fires when brain primarily targeted the weaker group

### 5. DPS Debuff (Critical Fix)

```diff:stage1_tactical.json
===
{
  "meta": {
    "name": "Stage 1 — Target Selection",
    "version": "2.0.0",
    "description": "Feature extractor training: learn to read density grids and select correct target. Brain vs Trap (50) vs Target (20). Kill smaller group first = debuff on larger."
  },
  "world": {
    "width": 1000.0,
    "height": 1000.0,
    "grid_width": 50,
    "grid_height": 50,
    "cell_size": 20.0
  },
  "factions": [
    {
      "id": 0,
      "name": "Brain",
      "role": "brain",
      "stats": { "hp": 100.0 },
      "default_count": 50
    },
    {
      "id": 1,
      "name": "Trap",
      "role": "bot",
      "stats": { "hp": 100.0 },
      "default_count": 50
    },
    {
      "id": 2,
      "name": "Target",
      "role": "bot",
      "stats": { "hp": 100.0 },
      "default_count": 20
    }
  ],
  "combat": {
    "rules": [
      {
        "source_faction": 0,
        "target_faction": 1,
        "range": 25.0,
        "effects": [{ "stat_index": 0, "delta_per_second": -25.0 }]
      },
      {
        "source_faction": 1,
        "target_faction": 0,
        "range": 25.0,
        "effects": [{ "stat_index": 0, "delta_per_second": -25.0 }]
      },
      {
        "source_faction": 0,
        "target_faction": 2,
        "range": 25.0,
        "effects": [{ "stat_index": 0, "delta_per_second": -25.0 }]
      },
      {
        "source_faction": 2,
        "target_faction": 0,
        "range": 25.0,
        "effects": [{ "stat_index": 0, "delta_per_second": -25.0 }]
      }
    ]
  },
  "movement": {
    "max_speed": 60.0,
    "steering_factor": 5.0,
    "separation_radius": 6.0,
    "separation_weight": 1.5,
    "flow_weight": 1.0
  },
  "terrain_thresholds": {
    "impassable_threshold": 65535,
    "destructible_min": 60001
  },
  "removal_rules": [
    { "stat_index": 0, "threshold": 0.0, "condition": "LessOrEqual" }
  ],
  "abilities": {
    "buff_cooldown_ticks": 180,
    "movement_speed_stat": 1,
    "combat_damage_stat": 2,
    "activate_buff": {
      "modifiers": [
        { "stat_index": 0, "modifier_type": "Multiplier", "value": 0.25 },
        { "stat_index": 2, "modifier_type": "Multiplier", "value": 0.25 }
      ],
      "duration_ticks": 9999
    }
  },
  "actions": [
    { "index": 0, "name": "Hold", "unlock_stage": 1 },
    { "index": 1, "name": "AttackNearest", "unlock_stage": 1 },
    { "index": 2, "name": "AttackFurthest", "unlock_stage": 1 }
  ],
  "training": {
    "max_density": 50.0,
    "max_steps": 500,
    "ai_eval_interval_ticks": 30,
    "observation_channels": 5,
    "rewards": {
      "time_penalty_per_step": -0.01,
      "kill_reward": 0.05,
      "death_penalty": -0.03,
      "win_terminal": 10.0,
      "loss_terminal": -10.0,
      "survival_bonus_multiplier": 5.0
    },
    "curriculum": [
      {
        "stage": 1,
        "description": "Target selection: kill smaller group first to debuff larger group",
        "graduation": {
          "win_rate": 0.80,
          "avg_survivors": 15.0,
          "min_episodes": 50
        },
        "demotion": null
      }
    ]
  },
  "bot_stage_behaviors": [
    {
      "stage": 1,
      "faction_id": 1,
      "strategy": {
        "type": "HoldPosition",
        "x": 500.0,
        "y": 200.0
      },
      "eval_interval_ticks": 60
    },
    {
      "stage": 1,
      "faction_id": 2,
      "strategy": {
        "type": "HoldPosition",
        "x": 700.0,
        "y": 500.0
      },
      "eval_interval_ticks": 60
    }
  ]
}
```

**Found that damage came from interaction rules, not entity stats** → buff system couldn't reduce DPS. The engine already had `combat_damage_stat` wiring (stat_index 2) but we weren't using it. Added `stat_index: 2, Multiplier: 0.25` to debuff, reducing trap damage by 75% alongside 75% HP reduction.

---

## Bugs Found & Fixed

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| **Toggle exploit** | PPO discounts distant terminal penalties (γ^500 ≈ 0.007) | Added approach reward (+0.02/unit closer) |
| **Debuff never fires** | Engagement tracking too sensitive (any HP loss = engaged) | Changed to count-based threshold (≥50% trap alive) |
| **Brain loses with debuff** | HP debuff doesn't reduce DPS (damage from interaction rules) | Added `combat_damage_stat` debuff (stat_index 2) |
| **Entropy collapse** | PPO converges to single action when one works 50% of time | **UNFIXED** — needs entropy coefficient tuning or curriculum change |

---

## Files Modified

| File | Change |
|------|--------|
| [stage1_tactical.json](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/macro-brain/profiles/stage1_tactical.json) | Trap=50, Target=20, dual HP+DPS debuff (0.25x), actions renamed |
| [curriculum.py](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/macro-brain/src/training/curriculum.py) | Position randomization (NEAR/FAR 50/50 swap) |
| [swarm_env.py](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/macro-brain/src/env/swarm_env.py) | Dynamic nearest/furthest targeting, approach reward, simplified debuff |
| [callbacks.py](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/macro-brain/src/training/callbacks.py) | Updated action names and info keys |
| [spaces.py](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/macro-brain/src/env/spaces.py) | Renamed action constants |

---

## Proposed Next Steps

> [!IMPORTANT]
> The entropy collapse is the primary blocker. Options:

1. **Increase entropy coefficient** in PPO config (`ent_coef=0.05` or higher) — penalizes deterministic policies, forces exploration
2. **Asymmetric distances** — make NEAR and FAR distances very different (e.g., 100 vs 400) so the density signal is unmistakable
3. **Remove position randomization** — always place Target at NEAR position, so the model learns "attack nearest = always correct" first. Then introduce randomization in Stage 1B.
4. **Add density signal to summary observation** — explicitly provide "nearest enemy density" and "furthest enemy density" as scalar inputs so the model doesn't need CNN to extract this
5. **Curriculum redesign** — instead of randomizing, use a fixed layout where the correct answer is always the same, then vary the layout in Stage 2
