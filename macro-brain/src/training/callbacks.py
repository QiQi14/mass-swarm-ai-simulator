import os
import csv
from collections import deque
from datetime import datetime
from typing import TYPE_CHECKING
from stable_baselines3.common.callbacks import BaseCallback

if TYPE_CHECKING:
    from src.config.game_profile import GameProfile

# Must match curriculum.py
ACTION_NAMES = [
    "Hold", "AttackCoord", "DropPheromone", "DropRepellent",
    "SplitToCoord", "MergeBack", "Retreat", "Scout",
]


class EnvStatCallback(BaseCallback):
    def _on_step(self) -> bool:
        infos = self.locals.get("infos", [])
        if infos:
            info = infos[0]
            if "own_count" in info:
                self.logger.record("env/own_count", info["own_count"])
            if "enemy_count" in info:
                self.logger.record("env/enemy_count", info["enemy_count"])
            if "patrol_count" in info:
                self.logger.record("env/patrol_count", info["patrol_count"])
            if "target_count" in info:
                self.logger.record("env/target_count", info["target_count"])
            if "debuff_applied" in info:
                self.logger.record("env/debuff_applied", int(info["debuff_applied"]))
            if "fog_explored_pct" in info:
                self.logger.record("env/fog_explored_pct", info["fog_explored_pct"])
            if "flanking_score" in info:
                self.logger.record("env/flanking_score", info["flanking_score"])
            if "lure_success" in info:
                self.logger.record("env/lure_success", int(info["lure_success"]))
        return True


class EpisodeLogCallback(BaseCallback):
    """Per-episode logging for Stage 1 Tactical Training.

    Tracks rolling reward for graduation condition:
    - Rolling avg reward > threshold for N consecutive episodes
    """

    WINDOW = 300  # Rolling window for stats (must be >= graduation window)
    GRADUATION_STREAK = 20  # Consecutive episodes above threshold

    def __init__(self, log_path: str = "./episode_log.csv",
                 num_actions: int = 8, verbose: int = 1):
        super().__init__(verbose)
        self.log_path = log_path
        self._log_dir = os.path.dirname(log_path) or "."
        self.num_actions = num_actions
        self.episode_count = 0
        self.episode_reward = 0.0
        self.episode_steps = 0
        self.action_counts = [0] * num_actions
        self._file = None
        self._writer = None
        self._current_stage = 0

        # Rolling deques
        self._results = deque(maxlen=self.WINDOW)
        self._survivors = deque(maxlen=self.WINDOW)
        self._episode_lengths = deque(maxlen=self.WINDOW)
        self._rewards = deque(maxlen=self.WINDOW)
        self._debuff_applied = deque(maxlen=self.WINDOW)
        self._lure_successes = deque(maxlen=self.WINDOW)
        self._flanking_scores = deque(maxlen=self.WINDOW)

        # Graduation streak tracking
        self._consecutive_above_threshold = 0

    def _on_training_start(self) -> None:
        # Get initial stage from env
        if self.training_env and hasattr(self.training_env, 'envs'):
            env = self.training_env.envs[0].unwrapped
            if hasattr(env, 'curriculum_stage'):
                self._current_stage = env.curriculum_stage
        self._open_log_file(self._current_stage)

    def _open_log_file(self, stage: int):
        """Open a new CSV log file for the given stage.
        
        Columns are dynamic — only stage-relevant fields are included.
        """
        # Close previous file if open
        if self._file is not None:
            self._file.flush()
            self._file.close()
            self._file = None
            self._writer = None

        os.makedirs(self._log_dir, exist_ok=True)
        stage_path = os.path.join(self._log_dir, f"episode_log_stage{stage}.csv")
        self._file = open(stage_path, "w", newline="")
        self._writer = csv.writer(self._file)

        # Build dynamic column spec for this stage
        self._stage_columns = self._build_stage_columns(stage)
        self._writer.writerow([col[0] for col in self._stage_columns])
        self._file.flush()
        self._current_stage = stage
        if self.verbose >= 1:
            print(f"📝 Episode log: {stage_path}")

    def _build_stage_columns(self, stage: int) -> list[tuple[str, str]]:
        """Build the list of (column_name, data_key) for a given stage.
        
        Only includes columns relevant to the stage:
        - Stage 0: 1v1, no trap/target/debuff/fog/flanking/lure
        - Stage 1+: trap/target/debuff when multi-faction
        - Stage 2,7,8: fog_explored_pct
        - Stage 5+: flanking_score
        - Stage 6+: scout usage
        """
        cols = [
            ("episode", "episode"),
            ("timestep", "timestep"),
            ("result", "result"),
            ("own_alive", "own"),
            ("enemy_alive", "enemy"),
        ]
        
        # Per-faction breakdown only when multiple enemy factions present
        if stage >= 1:
            cols.append(("trap_alive", "trap"))
            cols.append(("target_alive", "target"))
        
        cols.append(("ep_steps", "ep_steps"))
        cols.append(("ep_reward", "ep_reward"))
        
        # Only include unlocked actions
        unlocked = self._get_unlocked_actions(stage)
        for i, unlocked_flag in enumerate(unlocked):
            if unlocked_flag:
                name = ACTION_NAMES[i] if i < len(ACTION_NAMES) else f"act_{i}"
                cols.append((f"act_{name}", f"act_{i}"))
        
        # Stage-specific tactical columns
        if stage >= 1:
            cols.append(("debuff_applied", "debuff"))
            cols.append(("trap_engaged", "engaged"))
        if stage in (2, 7, 8):
            cols.append(("fog_explored_pct", "fog_pct"))
        if stage >= 5:
            cols.append(("flanking_score", "fln_score"))

        
        # Rolling stats (always)
        cols.extend([
            ("win_rate", "win_rate"),
            ("avg_survivors", "avg_survivors"),
            ("avg_ep_len", "avg_ep_len"),
            ("avg_reward", "avg_reward"),
            ("graduation_streak", "grad_streak"),
            ("stage", "stage"),
            ("timestamp", "timestamp"),
        ])
        return cols

    @staticmethod
    def _get_unlocked_actions(stage: int) -> list[bool]:
        """Which actions are unlocked at a given stage."""
        unlock = [True, True, False, False, False, False, False, False]
        if stage >= 4:
            unlock[2] = unlock[3] = True
        if stage >= 5:
            unlock[4] = unlock[5] = True
        if stage >= 6:
            unlock[6] = unlock[7] = True
        return unlock

    def _on_step(self) -> bool:
        # Track actions
        actions = self.locals.get("actions", None)
        if actions is not None and len(actions) > 0:
            # MultiDiscrete: actions[0] = [action_type, flat_coord]
            act_array = actions[0]
            act = int(act_array[0]) if hasattr(act_array, '__len__') else int(act_array)
            if 0 <= act < self.num_actions:
                self.action_counts[act] += 1

        # Track rewards
        rewards = self.locals.get("rewards", [])
        dones = self.locals.get("dones", [])
        infos = self.locals.get("infos", [])

        if rewards is not None and len(rewards) > 0:
            self.episode_reward += float(rewards[0])

        self.episode_steps += 1

        if dones is not None and len(dones) > 0 and dones[0]:
            self.episode_count += 1
            info = infos[0] if infos else {}
            own = info.get("own_count", -1)
            enemy = info.get("enemy_count", -1)
            patrol = info.get("trap_count", -1)
            target = info.get("target_count", -1)
            debuff = info.get("debuff_applied", False)
            engaged = info.get("trap_engaged", False)
            fog_pct = info.get("fog_explored_pct", 0.0)
            fln_score = info.get("flanking_score", 0.0)
            lure_ok = info.get("lure_success", False)

            # Determine result
            if own == 0 and enemy > 0:
                result = "LOSS"
            elif enemy == 0 and own > 0:
                result = "WIN"
            elif own == 0 and enemy == 0:
                result = "DRAW"
            else:
                result = "TIMEOUT"

            # Update rolling stats
            self._results.append(1 if result == "WIN" else 0)
            self._survivors.append(own if result == "WIN" else 0)
            self._episode_lengths.append(self.episode_steps)
            self._rewards.append(self.episode_reward)
            self._debuff_applied.append(1 if debuff else 0)
            self._lure_successes.append(1 if lure_ok else 0)
            self._flanking_scores.append(fln_score)

            # Compute rolling metrics
            win_rate = sum(self._results) / len(self._results) if self._results else 0
            win_survivors = [s for s in self._survivors if s > 0]
            avg_survivors = sum(win_survivors) / len(win_survivors) if win_survivors else 0
            avg_ep_len = sum(self._episode_lengths) / len(self._episode_lengths)
            avg_reward = sum(self._rewards) / len(self._rewards) if self._rewards else 0

            # Get curriculum stage
            stage = 1
            if self.training_env and hasattr(self.training_env, 'envs'):
                env = self.training_env.envs[0].unwrapped
                if hasattr(env, 'curriculum_stage'):
                    stage = env.curriculum_stage

            # Build row data dict
            data = {
                "episode": self.episode_count,
                "timestep": self.num_timesteps,
                "result": result,
                "own": own,
                "enemy": enemy,
                "trap": patrol,
                "target": target,
                "ep_steps": self.episode_steps,
                "ep_reward": f"{self.episode_reward:.4f}",
                "debuff": int(debuff),
                "engaged": int(engaged),
                "fog_pct": f"{fog_pct:.3f}",
                "fln_score": f"{fln_score:.3f}",
                "lure_ok": int(lure_ok),
                "win_rate": f"{win_rate:.3f}",
                "avg_survivors": f"{avg_survivors:.1f}",
                "avg_ep_len": f"{avg_ep_len:.1f}",
                "avg_reward": f"{avg_reward:.4f}",
                "grad_streak": self._consecutive_above_threshold,
                "stage": stage,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            }
            # Add action counts
            for i in range(self.num_actions):
                data[f"act_{i}"] = self.action_counts[i]

            # Write only the columns defined for this stage
            row = [data.get(col[1], "") for col in self._stage_columns]
            self._writer.writerow(row)
            self._file.flush()

            # Atomic dump of latest status for UI
            import json
            import os
            status_path = os.path.join(os.path.dirname(self.log_path), "training_status.json")
            try:
                with open(status_path, "w") as f:
                    json.dump({
                        "stage": stage,
                        "episode": self.episode_count,
                        "win_rate": f"{win_rate:.3f}",
                        "grad_streak": self._consecutive_above_threshold
                    }, f)
            except Exception:
                pass

            if self.verbose >= 1:
                # Only show unlocked actions in console
                unlocked = self._get_unlocked_actions(stage)
                act_str = " ".join(
                    f"{ACTION_NAMES[i]}:{self.action_counts[i]}"
                    for i in range(self.num_actions)
                    if unlocked[i]
                )
                # Stage-specific detail string
                detail = ""
                if stage >= 1:
                    detail += f" (P:{patrol:>2} T:{target:>2})"
                if debuff:
                    detail += " 🎯"
                print(
                    f"[Ep {self.episode_count:>4}] {result:<7} | "
                    f"Own:{own:>2} Ene:{enemy:>2}{detail} | "
                    f"Steps:{self.episode_steps:>3} | "
                    f"Rew:{self.episode_reward:>+8.2f} | "
                    f"WR:{win_rate:.0%} | "
                    f"Surv:{avg_survivors:.1f} | "
                    f"{act_str}"
                )

            # Reset per-episode accumulators
            self.episode_reward = 0.0
            self.episode_steps = 0
            self.action_counts = [0] * self.num_actions

        return True

    # ── Public Properties ───────────────────────────────────────

    @property
    def rolling_win_rate(self) -> float:
        return sum(self._results) / len(self._results) if self._results else 0.0

    @property
    def rolling_avg_survivors(self) -> float:
        win_survivors = [s for s in self._survivors if s > 0]
        return sum(win_survivors) / len(win_survivors) if win_survivors else 0.0

    @property
    def rolling_avg_reward(self) -> float:
        return sum(self._rewards) / len(self._rewards) if self._rewards else 0.0

    def _on_training_end(self) -> None:
        if self._file:
            self._file.close()


class CurriculumCallback(BaseCallback):
    """Sub-stage graduation: advances curriculum when win rate threshold is met.

    Monitors rolling win rate from the EpisodeLogCallback:
    - Win rate >= threshold for N consecutive checks → graduate to next sub-stage
    - Updates the env's curriculum_stage so spawns change on next reset
    - Resets rolling stats to give the model a clean slate at each new stage

    Sub-stage progression: 1 → 2 → 3 (max)
    """

    def __init__(
        self,
        episode_logger: EpisodeLogCallback | None = None,
        profile: 'GameProfile' | None = None,
        win_rate_threshold: float = 0.80,
        streak_required: int = 50,
        max_substage: int = 9,
        verbose: int = 1,
        checkpoint_dir: str | None = None,
    ):
        super().__init__(verbose)
        self.episode_logger = episode_logger
        self.profile = profile
        self.win_rate_threshold = win_rate_threshold
        self.streak_required = streak_required
        self.max_substage = max_substage
        self.checkpoint_dir = checkpoint_dir
        self._last_checked_episode = 0
        self._consecutive_above = 0

    def _on_step(self) -> bool:
        if self.episode_logger is None:
            return True

        current_ep = self.episode_logger.episode_count
        if current_ep == self._last_checked_episode:
            return True
        self._last_checked_episode = current_ep

        # Need at least 200 episodes for stable win rate
        if len(self.episode_logger._results) < 200:
            return True

        # Check rolling win rate (over last 200 episodes)
        results = list(self.episode_logger._results)
        recent = results[-200:]
        win_rate = sum(recent) / len(recent)
        
        # Determine current stage requirements
        current_stage = 1
        if self.training_env and hasattr(self.training_env, 'envs'):
            env = self.training_env.envs[0].unwrapped
            if hasattr(env, 'curriculum_stage'):
                current_stage = env.curriculum_stage

        # Stage specific win rate thresholds
        target_wr = self.win_rate_threshold
        if current_stage == 8:
            target_wr = 0.75
            
        req_streak = self.streak_required
        if current_stage == 9:
            req_streak = 500

        # Stage specific additional constraints
        extra_criteria_met = True
        
        if current_stage == 5:
            fln_scores = list(self.episode_logger._flanking_scores)[-200:]
            if not fln_scores or (sum(fln_scores) / len(fln_scores)) <= 0.3:
                extra_criteria_met = False
                
        
                
        # BUG FIX: Also require the last episode to be a WIN.
        # Previously, TIMEOUT episodes did not reset the streak if the
        # rolling win rate stayed above threshold, causing premature graduation.
        last_result_is_win = bool(results[-1]) if results else False

        if win_rate >= target_wr and extra_criteria_met and last_result_is_win:
            self._consecutive_above += 1
        else:
            self._consecutive_above = 0

        # Update the episode logger's streak counter for CSV logging
        self.episode_logger._consecutive_above_threshold = self._consecutive_above

        if self._consecutive_above >= req_streak:
            self._graduate()

        return True

    def _graduate(self):
        """Advance to the next sub-stage."""
        # Get current stage from the env
        current_stage = 1
        env = None
        if self.training_env and hasattr(self.training_env, 'envs'):
            env = self.training_env.envs[0].unwrapped
            if hasattr(env, 'curriculum_stage'):
                current_stage = env.curriculum_stage

        if current_stage >= self.max_substage:
            if self.verbose >= 1:
                print(
                    f"\n{'='*60}\n"
                    f"🏆 ALL SUB-STAGES COMPLETE! (Stage {current_stage})\n"
                    f"   Episode:  {self.episode_logger.episode_count}\n"
                    f"   Win Rate: {self.episode_logger.rolling_win_rate:.0%}\n"
                    f"{'='*60}\n"
                )
            self._consecutive_above = 0
            return

        next_stage = current_stage + 1

        if self.verbose >= 1:
            print(
                f"\n{'='*60}\n"
                f"🎓 SUB-STAGE {current_stage} → {next_stage} GRADUATED!\n"
                f"   Episode:   {self.episode_logger.episode_count}\n"
                f"   Timesteps: {self.num_timesteps}\n"
                f"   Win Rate:  {self.episode_logger.rolling_win_rate:.0%}\n"
                f"{'='*60}\n"
            )

        if self.checkpoint_dir is not None and self.model is not None:
            save_path = f"{self.checkpoint_dir}/stage_{current_stage}_graduated.zip"
            self.model.save(save_path)
            if self.verbose >= 1:
                print(f"💾 Checkpoint saved: {save_path}")

        # Advance the env's curriculum stage
        if env is not None:
            env.curriculum_stage = next_stage

        # Rotate to a new per-stage episode log file
        if self.episode_logger is not None:
            self.episode_logger._open_log_file(next_stage)

        # Reset rolling stats for clean measurement at new stage
        self.episode_logger._results.clear()
        self.episode_logger._survivors.clear()
        self.episode_logger._episode_lengths.clear()
        self.episode_logger._rewards.clear()
        self.episode_logger._debuff_applied.clear()
        self.episode_logger._lure_successes.clear()
        self.episode_logger._flanking_scores.clear()
        self._consecutive_above = 0
        self.episode_logger._consecutive_above_threshold = 0

