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
from src.env.spaces import (
    make_observation_space, make_action_space, MAX_GRID_WIDTH, MAX_GRID_HEIGHT,
    MAX_GRID_CELLS, SPATIAL_ACTIONS, ACTION_NAMES, make_coordinate_mask
)
from src.utils.lkp_buffer import LKPBuffer
from src.env.actions import multidiscrete_to_directives
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
        profile_path = config.get("profile_path", "profiles/tactical_curriculum.json")
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
        self.observation_space = make_observation_space()
        self.action_space = make_action_space(
            num_actions=8, max_grid_cells=MAX_GRID_CELLS
        )

        self._active_sub_factions: list[int] = []
        self._last_snapshot: dict | None = None
        self._step_count: int = 0
        self._last_nav_directive: dict | None = None
        
        self._lkp_buffer = LKPBuffer(grid_h=MAX_GRID_HEIGHT, grid_w=MAX_GRID_WIDTH, num_enemy_channels=2)
        self._prev_fog_explored: np.ndarray | None = None
        self._active_grid_w = MAX_GRID_WIDTH
        self._active_grid_h = MAX_GRID_HEIGHT
        self._pad_offset_x = 0
        self._pad_offset_y = 0
        self._cell_size = 20.0
        self._fog_enabled = False
        self._max_primary_stat = 100.0  # Auto-computed from spawns each episode
        self._primary_stat_index = 0    # Derived from removal rules each episode
        self._active_objective_fid = 1
        self._active_ping: tuple[float, float] | None = None
        self._ping_timer = 0
        self._ping_lifespan = 10
        


        # ── Multi-bot controllers (one per bot faction) ─────────
        self._bot_controllers: dict[int, BotController] = {}

        # ── Debuff tracking ─────────────────────────────────────
        self._trap_engaged = False     # Has brain fought trap group?
        self._debuff_applied = False   # Was debuff sent this episode?
        self._trap_faction = 1         # Faction ID of trap group (50 units)
        self._target_faction = 2       # Faction ID of target group (20 units)
        self._trap_starting_count = 0
        self._target_starting_count = 0

        # ── Approach reward tracking ────────────────────────────
        self._prev_min_enemy_dist: float | None = None

        # ── Active enemy factions for this episode ──────────────
        # Only factions actually spawned — prevents phantom rewards
        # from unspawned factions counting as "eliminated"
        self._active_enemy_factions: list[int] = []

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
        # Action type mask
        act_mask = np.ones(8, dtype=bool)
        
        if not self._active_sub_factions:
            act_mask[5] = False  # MergeBack
        if len(self._active_sub_factions) >= 2:
            act_mask[4] = False  # SplitToCoord
            act_mask[7] = False  # Scout
        
        # Stage-based action unlocking
        stage_config = self._get_stage_action_unlock()
        for i in range(8):
            if not stage_config[i]:
                act_mask[i] = False
        
        # Coordinate mask (only active arena cells)
        coord_mask = make_coordinate_mask(
            self._active_grid_w, self._active_grid_h,
            MAX_GRID_WIDTH, MAX_GRID_HEIGHT,
        )
        
        return np.concatenate([act_mask, coord_mask])

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._step_count = 0
        self._active_sub_factions = []
        self._last_snapshot = None
        self._last_nav_directive = None
        self._trap_engaged = False
        self._debuff_applied = False
        self._prev_min_enemy_dist = None
        
        self._lkp_buffer.reset()
        self._prev_fog_explored = None
        self._active_objective_fid = 1
        self._active_ping = None
        self._ping_timer = 0

        from src.utils.terrain_generator import generate_terrain_for_stage
        from src.training.curriculum import get_spawns_for_stage, get_map_config
        
        # Load stage map config from curriculum
        stage_map_config = get_map_config(self.curriculum_stage)
        self._active_grid_w = stage_map_config.active_grid_w
        self._active_grid_h = stage_map_config.active_grid_h
        self._cell_size = stage_map_config.cell_size
        self._fog_enabled = stage_map_config.fog_enabled
        self._pad_offset_x = (MAX_GRID_WIDTH - self._active_grid_w) // 2
        self._pad_offset_y = (MAX_GRID_HEIGHT - self._active_grid_h) // 2

        terrain = generate_terrain_for_stage(
            self.curriculum_stage,
            seed=int(self.np_random.integers(0, 2**31)),
        )
        spawns, role_meta = get_spawns_for_stage(
            self.curriculum_stage,
            rng=self.np_random,
            profile=self.profile,
        )
        
        self._trap_faction = role_meta.get("trap_faction", 1)
        self._target_faction = role_meta.get("target_faction", 2)

        # Track which enemy factions are ACTUALLY spawned this episode
        # Prevents phantom threat_priority_bonus from unspawned factions
        self._active_enemy_factions = [
            s["faction_id"] for s in spawns
            if s["faction_id"] != self.brain_faction
        ]

        # Track trap starting count from spawns
        self._trap_starting_count = sum(
            s["count"] for s in spawns if s["faction_id"] == self._trap_faction
        )
        self._target_starting_count = sum(
            s["count"] for s in spawns if s["faction_id"] == self._target_faction
        )

        # Stage 1 Tactical navigation rules:
        # NO nav rules at all. Each faction's movement is controlled by:
        # - Brain: action space (Hold/AttackA/AttackB directives)
        # - Patrol: bot controller Retreat directives (vertical patrol)
        # - Target: bot controller Idle (stays at spawn)
        # Combat is still proximity-based via combat_rules (nav ≠ combat).
        tactical_nav_rules = []

        # Derive primary stat index from removal rules (V-05 fix)
        # The stat that triggers death IS the primary resource to track.
        self._primary_stat_index = 0  # Default: stat[0]
        if self.profile.removal_rules:
            self._primary_stat_index = self.profile.removal_rules[0].stat_index

        # Auto-compute max primary stat from actual spawn stats
        self._max_primary_stat = max(
            (stat["value"] for spawn in spawns for stat in spawn.get("stats", [])
             if stat["index"] == self._primary_stat_index),
            default=100.0
        )

        payload = {
            "type": "reset_environment",
            "terrain": terrain,
            "spawns": spawns,
            "combat_rules": self.profile.combat_rules_payload(),
            "ability_config": self.profile.ability_config_payload(),
            "movement_config": self.profile.movement_config_payload(),
            "max_density": self.profile.training.max_density,
            "max_entity_ecp": self._max_primary_stat,
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

        # DEBUG: Log raw snapshot density data on first reset
        dm = snapshot.get("density_maps", {})
        ecp = snapshot.get("ecp_density_maps", {})
        ent_count = len(snapshot.get("entities", []))
        fc = snapshot.get("summary", {}).get("faction_counts", {})
        logger.info(
            f"🔎 Reset snapshot debug:\n"
            f"   tick={snapshot.get('tick', '?')}, entity_count={ent_count}\n"
            f"   faction_counts={fc}\n"
            f"   density_maps keys={list(dm.keys())}, sizes={[len(v) for v in dm.values()]}\n"
            f"   ecp_density_maps keys={list(ecp.keys())}, sizes={[len(v) for v in ecp.values()]}\n"
            f"   density_maps sums={dict((k, sum(v)) for k, v in dm.items())}\n"
            f"   ecp_density_maps sums={dict((k, sum(v)) for k, v in ecp.items())}"
        )

        obs = vectorize_snapshot(
            snapshot, self.brain_faction,
            enemy_factions=self.enemy_faction_ids,
            active_grid_w=self._active_grid_w,
            active_grid_h=self._active_grid_h,
            cell_size=self._cell_size,
            fog_enabled=self._fog_enabled,
            lkp_buffer=self._lkp_buffer,
            max_hp=self._max_primary_stat,
            summary_stat_index=self._primary_stat_index,
            active_sub_faction_ids=self._active_sub_factions,
        )
        return obs, {}

    def step(self, action: np.ndarray):
        self._step_count += 1
        prev_snapshot = self._last_snapshot

        # Build brain directive
        brain_directive, self._last_nav_directive = multidiscrete_to_directives(
            action,
            brain_faction=self.brain_faction,
            active_sub_factions=self._active_sub_factions,
            cell_size=self._cell_size,
            pad_offset_x=self._pad_offset_x,
            pad_offset_y=self._pad_offset_y,
            last_nav_directive=self._last_nav_directive,
        )
        if hasattr(self, '_pending_debuff') and self._pending_debuff is not None:
            brain_directive.insert(0, self._pending_debuff)
            self._pending_debuff = None
            


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

        ping_reward_delta = 0.0
        if self.curriculum_stage == 4:
            if self._active_ping is not None:
                self._ping_timer += 1
                brain_c = self._get_density_centroid(snapshot, self.brain_faction)
                if brain_c is not None:
                    dist = ((brain_c[0] - self._active_ping[0])**2 + (brain_c[1] - self._active_ping[1])**2)**0.5
                    if dist < 60.0:
                        ping_reward_delta += 1.0
                        self._active_ping = None
                if self._active_ping is not None and self._ping_timer >= self._ping_lifespan:
                    ping_reward_delta -= 1.0
                    self._active_ping = None
                    
            count = self._get_faction_count(snapshot, self._active_objective_fid)
            if count <= 0 and self._active_objective_fid == 1:
                self._active_objective_fid = 2
                self._active_ping = None
                
            if self._active_ping is None:
                c = self._get_density_centroid(snapshot, self._active_objective_fid)
                if c is not None:
                    px = np.clip(c[0] + self.np_random.uniform(-80, 80), 0, self.world_width)
                    py = np.clip(c[1] + self.np_random.uniform(-80, 80), 0, self.world_height)
                    self._active_ping = (float(px), float(py))
                    self._ping_timer = 0

        obs = vectorize_snapshot(
            snapshot, self.brain_faction,
            enemy_factions=self.enemy_faction_ids,
            active_grid_w=self._active_grid_w,
            active_grid_h=self._active_grid_h,
            cell_size=self._cell_size,
            fog_enabled=self._fog_enabled,
            lkp_buffer=self._lkp_buffer,
            max_hp=self._max_primary_stat,
            summary_stat_index=self._primary_stat_index,
            active_sub_faction_ids=self._active_sub_factions,
            active_objective_ping=self._active_ping if self.curriculum_stage == 4 else None,
            ping_intensity=max(0.0, 1.0 - (self._ping_timer / self._ping_lifespan)) if self.curriculum_stage == 4 else 1.0,
        )
        

            
        # Flanking score
        flanking_score = 0.0
        if self._active_sub_factions:
            sub_id = self._active_sub_factions[0]
            brain_c = self._get_density_centroid(snapshot, self.brain_faction)
            sub_c = self._get_density_centroid(snapshot, sub_id)
            
            # Find closest enemy to brain
            enemy_centroids = []
            for ef in self.enemy_faction_ids:
                if self._get_faction_count(snapshot, ef) > 0:
                    ec = self._get_density_centroid(snapshot, ef)
                    if ec: enemy_centroids.append((ef, ec))
            
            if enemy_centroids and brain_c:
                nearest = min(enemy_centroids, key=lambda x: (x[1][0]-brain_c[0])**2 + (x[1][1]-brain_c[1])**2)[1]
                from src.env.rewards import compute_flanking_score
                flanking_score = compute_flanking_score(brain_c, sub_c, nearest)

        reward = self._compute_reward(snapshot, prev_snapshot, obs, flanking_score)
        
        reward += ping_reward_delta

        # Store prev fog explored for next step's exploration reward
        if self._fog_enabled and "ch5" in obs:
            self._prev_fog_explored = obs["ch5"].copy()

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
            trap_hp = hp_list[self._primary_stat_index] if hp_list and len(hp_list) > self._primary_stat_index else 100.0
            if trap_hp < 99.9:
                self._trap_engaged = True

        trap_count = self._get_faction_count(snapshot, self._trap_faction)
        if trap_count < self._trap_starting_count:
            self._trap_engaged = True

        # Only apply debuff once
        if self._debuff_applied:
            return

        # Debuff fires when: Target mostly eliminated (>70% killed) AND Trap still has
        # at least half its starting units alive (didn't primarily fight trap)
        target_count = self._get_faction_count(snapshot, self._target_faction)
        trap_threshold = self._trap_starting_count * 0.5  # at least half alive
        target_threshold = self._target_starting_count * 0.3  # >70% killed

        if target_count <= target_threshold and trap_count >= trap_threshold:
            self._debuff_applied = True
            self._apply_trap_debuff()

    def _apply_trap_debuff(self):
        """Send ActivateBuff to reduce Trap group's damage output.

        Uses the activate_buff config from the profile which is
        pre-configured with a 0.25x damage multiplier.  Also notifies
        the trap's bot controller to switch from HoldPosition → Charge
        so the weakened trap rushes the brain (no retargeting needed).
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
            "🎯 Debuff applied! Brain killed Target first → Trap DPS quartered."
        )
        self._pending_debuff = debuff_directive

        # Notify trap bot controller to enrage (HoldPosition → Charge)
        trap_ctrl = self._bot_controllers.get(self._trap_faction)
        if trap_ctrl is not None:
            trap_ctrl._debuff_applied = True

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

    def _get_stage_action_unlock(self) -> list[bool]:
        """Which actions are unlocked at the current curriculum stage.

        Stage 0-1: Hold(0), AttackCoord(1)
        Stage 2:   +DropPheromone(2)
        Stage 3:   +DropRepellent(3)
        Stage 4:   +Scout(7)                    — 10% recon split
        Stage 5:   +SplitToCoord(4), +MergeBack(5) — 30% combat split
        Stage 6+:  +Retreat(6)                   — full 8-action vocabulary
        """
        s = self.curriculum_stage
        unlock = [True, True, False, False, False, False, False, False]
        if s >= 2:
            unlock[2] = True   # DropPheromone
        if s >= 3:
            unlock[3] = True   # DropRepellent
        if s >= 4:
            unlock[7] = True   # Scout
        if s >= 5:
            unlock[4] = unlock[5] = True  # SplitToCoord, MergeBack
        if s >= 6:
            unlock[6] = True   # Retreat
        return unlock



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



    def _compute_reward(self, snapshot: dict, prev_snapshot: dict | None, obs: dict, flanking_score: float) -> float:
        from src.env.rewards import compute_shaped_reward, threat_priority_bonus
        
        # Only evaluate threat priority when 2+ enemy factions are spawned.
        # Without this guard, unspawned factions (count=0) appear "dead",
        # triggering +2.0/step phantom bonus (e.g., Stage 0: +1000 free reward).
        threat_hit = False
        if len(self._active_enemy_factions) >= 2:
            threat_hit = threat_priority_bonus(
                snapshot, prev_snapshot, self._active_enemy_factions
            ) > 0.0
        
        return compute_shaped_reward(
            snapshot=snapshot,
            prev_snapshot=prev_snapshot,
            brain_faction=self.brain_faction,
            enemy_faction=self._active_enemy_factions,
            reward_weights=self.profile.training.rewards,
            starting_entities=self.starting_entities,
            stage=self.curriculum_stage,
            fog_explored=obs.get("ch5"),
            prev_fog_explored=self._prev_fog_explored,
            flanking_score=flanking_score,
            lure_success=False,
            threat_priority_hit=threat_hit,
        )

    def close(self):
        self._disconnect()
        self._ctx.term()
