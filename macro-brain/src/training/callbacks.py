import os
import csv
from collections import deque
from datetime import datetime
from typing import TYPE_CHECKING
from stable_baselines3.common.callbacks import BaseCallback

if TYPE_CHECKING:
    from src.config.game_profile import GameProfile

# Must match curriculum.py
ACTION_NAMES = ["Hold", "AttackA", "AttackB"]


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
        return True


class EpisodeLogCallback(BaseCallback):
    """Per-episode logging for Stage 1 Tactical Training.

    Tracks rolling reward for graduation condition:
    - Rolling avg reward > threshold for N consecutive episodes
    """

    WINDOW = 100  # Rolling window for stats
    GRADUATION_STREAK = 20  # Consecutive episodes above threshold

    def __init__(self, log_path: str = "./episode_log.csv",
                 num_actions: int = 3, verbose: int = 1):
        super().__init__(verbose)
        self.log_path = log_path
        self.num_actions = num_actions
        self.episode_count = 0
        self.episode_reward = 0.0
        self.episode_steps = 0
        self.action_counts = [0] * num_actions
        self._file = None
        self._writer = None

        # Rolling deques
        self._results = deque(maxlen=self.WINDOW)
        self._survivors = deque(maxlen=self.WINDOW)
        self._episode_lengths = deque(maxlen=self.WINDOW)
        self._rewards = deque(maxlen=self.WINDOW)
        self._debuff_applied = deque(maxlen=self.WINDOW)

        # Graduation streak tracking
        self._consecutive_above_threshold = 0

    def _on_training_start(self) -> None:
        os.makedirs(os.path.dirname(self.log_path) or ".", exist_ok=True)
        self._file = open(self.log_path, "w", newline="")
        self._writer = csv.writer(self._file)
        header = [
            "episode", "timestep", "result", "own_alive", "enemy_alive",
            "patrol_alive", "target_alive",
            "ep_steps", "ep_reward",
        ]
        for i in range(self.num_actions):
            name = ACTION_NAMES[i] if i < len(ACTION_NAMES) else f"act_{i}"
            header.append(f"act_{name}")
        header.extend([
            "debuff_applied", "group_a_engaged",
            "win_rate_100", "avg_survivors_100", "avg_ep_len_100",
            "avg_reward_100", "graduation_streak",
            "stage", "timestamp",
        ])
        self._writer.writerow(header)
        self._file.flush()

    def _on_step(self) -> bool:
        # Track actions
        actions = self.locals.get("actions", None)
        if actions is not None and len(actions) > 0:
            act = int(actions[0])
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
            patrol = info.get("patrol_count", -1)
            target = info.get("target_count", -1)
            debuff = info.get("debuff_applied", False)
            engaged = info.get("group_a_engaged", False)

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

            row = [
                self.episode_count,
                self.num_timesteps,
                result,
                own,
                enemy,
                patrol,
                target,
                self.episode_steps,
                f"{self.episode_reward:.4f}",
                *self.action_counts,
                int(debuff),
                int(engaged),
                f"{win_rate:.3f}",
                f"{avg_survivors:.1f}",
                f"{avg_ep_len:.1f}",
                f"{avg_reward:.4f}",
                self._consecutive_above_threshold,
                stage,
                datetime.now().strftime("%H:%M:%S"),
            ]
            self._writer.writerow(row)
            self._file.flush()

            if self.verbose >= 1:
                act_str = " ".join(
                    f"{ACTION_NAMES[i] if i < len(ACTION_NAMES) else f'A{i}'}:{self.action_counts[i]}"
                    for i in range(self.num_actions)
                )
                debuff_str = "🎯" if debuff else "  "
                print(
                    f"[Ep {self.episode_count:>4}] {result:<7} | "
                    f"Own:{own:>2} Ene:{enemy:>2} (P:{patrol:>2} T:{target:>2}) | "
                    f"Steps:{self.episode_steps:>3} | "
                    f"Rew:{self.episode_reward:>+8.2f} | "
                    f"WR100:{win_rate:.0%} | "
                    f"Surv:{avg_survivors:.1f} | "
                    f"AvgR:{avg_reward:.2f} | "
                    f"{debuff_str} | {act_str}"
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
    """Stage 1 graduation: rolling avg reward > threshold for N consecutive episodes.

    Simplified from the multi-stage mastery system — only checks one condition.
    """

    def __init__(
        self,
        episode_logger: EpisodeLogCallback | None = None,
        profile: 'GameProfile' | None = None,
        reward_threshold: float = 12.0,
        streak_required: int = 20,
        verbose: int = 1,
    ):
        super().__init__(verbose)
        self.episode_logger = episode_logger
        self.profile = profile
        self.reward_threshold = reward_threshold
        self.streak_required = streak_required
        self._last_checked_episode = 0
        self._consecutive_above = 0

    def _on_step(self) -> bool:
        if self.episode_logger is None:
            return True

        current_ep = self.episode_logger.episode_count
        if current_ep == self._last_checked_episode:
            return True
        self._last_checked_episode = current_ep

        # Check rolling average reward
        avg_reward = self.episode_logger.rolling_avg_reward
        if avg_reward >= self.reward_threshold:
            self._consecutive_above += 1
        else:
            self._consecutive_above = 0

        # Update the episode logger's streak counter for CSV logging
        self.episode_logger._consecutive_above_threshold = self._consecutive_above

        if self._consecutive_above >= self.streak_required:
            if self.verbose >= 1:
                print(
                    f"\n{'='*60}\n"
                    f"🎓 STAGE 1 GRADUATED!\n"
                    f"   Episode:   {current_ep}\n"
                    f"   Timesteps: {self.num_timesteps}\n"
                    f"   Avg Reward: {avg_reward:.2f} >= {self.reward_threshold}\n"
                    f"   Streak:     {self._consecutive_above} >= {self.streak_required}\n"
                    f"{'='*60}\n"
                )
            # Reset streak after graduation (prevents repeated printing)
            self._consecutive_above = 0

        return True
