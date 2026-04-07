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
    "Hold", "Navigate", "Frenzy", "Retreat",
    "ZoneModifier", "SplitFaction", "MergeFaction", "SetAggroMask"
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
            if "sub_factions" in info:
                self.logger.record("env/sub_factions", info["sub_factions"])
        return True


class EpisodeLogCallback(BaseCallback):
    """Comprehensive per-episode logging with mastery metrics.

    Tracks everything the CurriculumCallback needs for
    Proof-of-Mechanic-Mastery transitions:
      - Rolling win rate
      - Rolling avg survivors (on wins only)
      - Rolling action usage (per-action fraction)
      - Rolling timeout rate
      - Rolling flanking score
    """

    WINDOW = 100  # Rolling window for stats

    def __init__(self, log_path: str = "./episode_log.csv", verbose: int = 1):
        super().__init__(verbose)
        self.log_path = log_path
        self.episode_count = 0
        self.episode_reward = 0.0
        self.episode_steps = 0
        # Per-episode action counts
        self.action_counts = [0] * 8
        self._file = None
        self._writer = None

        # Rolling deques for mastery metrics
        self._results = deque(maxlen=self.WINDOW)         # 1=WIN, 0=LOSS/TIMEOUT
        self._survivors = deque(maxlen=self.WINDOW)        # own_alive on WIN, 0 on LOSS
        self._episode_lengths = deque(maxlen=self.WINDOW)
        self._timeouts = deque(maxlen=self.WINDOW)         # 1=TIMEOUT, 0=WIN/LOSS
        self._flanking_scores = deque(maxlen=self.WINDOW)  # episode flanking score
        # Per-episode total action counts for rolling usage
        self._action_totals = deque(maxlen=self.WINDOW)    # list of [count_per_action]
        self._step_totals = deque(maxlen=self.WINDOW)      # total steps per episode

        # Per-episode flanking accumulator
        self._episode_flanking = 0.0

    def _on_training_start(self) -> None:
        os.makedirs(os.path.dirname(self.log_path) or ".", exist_ok=True)
        self._file = open(self.log_path, "w", newline="")
        self._writer = csv.writer(self._file)
        self._writer.writerow([
            "episode", "timestep", "result", "own_alive", "enemy_alive",
            "ep_steps", "ep_reward", "kills", "deaths",
            "act_hold", "act_nav", "act_frenzy", "act_retreat",
            "act_zone", "act_split", "act_merge", "act_aggro",
            "win_rate_100", "avg_survivors_100", "avg_ep_len_100",
            "timeout_rate_100", "flanking_score_100",
            "retreat_usage", "split_usage",
            "stage", "timestamp"
        ])
        self._file.flush()

    def _on_step(self) -> bool:
        # Track actions
        actions = self.locals.get("actions", None)
        if actions is not None and len(actions) > 0:
            act = int(actions[0])
            if 0 <= act < 8:
                self.action_counts[act] += 1

        # Track rewards
        rewards = self.locals.get("rewards", [])
        dones = self.locals.get("dones", [])
        infos = self.locals.get("infos", [])

        if rewards is not None and len(rewards) > 0:
            self.episode_reward += float(rewards[0])

        # Track flanking from info (if env exposes it)
        if infos and len(infos) > 0:
            info = infos[0]
            self._episode_flanking += info.get("flanking_bonus", 0.0)

        self.episode_steps += 1

        if dones is not None and len(dones) > 0 and dones[0]:
            self.episode_count += 1
            info = infos[0] if infos else {}
            own = info.get("own_count", -1)
            enemy = info.get("enemy_count", -1)

            # Determine result
            if own == 0 and enemy > 0:
                result = "LOSS"
            elif enemy == 0 and own > 0:
                result = "WIN"
            elif own == 0 and enemy == 0:
                result = "DRAW"
            else:
                result = "TIMEOUT"

            kills = max(0, 50 - enemy)
            deaths = max(0, 50 - own)

            # ── Update Rolling Stats ────────────────────────────
            self._results.append(1 if result == "WIN" else 0)
            self._survivors.append(own if result == "WIN" else 0)
            self._episode_lengths.append(self.episode_steps)
            self._timeouts.append(1 if result == "TIMEOUT" else 0)
            self._flanking_scores.append(self._episode_flanking)
            self._action_totals.append(list(self.action_counts))
            self._step_totals.append(self.episode_steps)

            # ── Compute Rolling Metrics ─────────────────────────
            win_rate = sum(self._results) / len(self._results) if self._results else 0
            win_survivors = [s for s in self._survivors if s > 0]
            avg_survivors = sum(win_survivors) / len(win_survivors) if win_survivors else 0
            avg_ep_len = sum(self._episode_lengths) / len(self._episode_lengths)
            timeout_rate = sum(self._timeouts) / len(self._timeouts) if self._timeouts else 0
            flanking_score = sum(self._flanking_scores) / len(self._flanking_scores) if self._flanking_scores else 0

            # Per-action usage as fraction of total steps
            action_usage = self._compute_action_usage()

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
                self.episode_steps,
                f"{self.episode_reward:.4f}",
                kills,
                deaths,
                *self.action_counts,
                f"{win_rate:.3f}",
                f"{avg_survivors:.1f}",
                f"{avg_ep_len:.1f}",
                f"{timeout_rate:.3f}",
                f"{flanking_score:.4f}",
                f"{action_usage.get('Retreat', 0):.3f}",
                f"{action_usage.get('SplitFaction', 0):.3f}",
                stage,
                datetime.now().strftime("%H:%M:%S"),
            ]
            self._writer.writerow(row)
            self._file.flush()

            if self.verbose >= 1:
                act_str = f"H:{self.action_counts[0]} N:{self.action_counts[1]} F:{self.action_counts[2]}"
                if stage >= 2:
                    act_str += f" R:{self.action_counts[3]}"
                if stage >= 3:
                    act_str += f" Sp:{self.action_counts[5]}"
                print(
                    f"[Ep {self.episode_count:>4}] {result:<7} | "
                    f"Own:{own:>2} Ene:{enemy:>2} | "
                    f"Steps:{self.episode_steps:>3} | "
                    f"Rew:{self.episode_reward:>+8.2f} | "
                    f"WR100:{win_rate:.0%} | "
                    f"Surv:{avg_survivors:.1f} | "
                    f"S{stage} | {act_str}"
                )

            # Reset per-episode accumulators
            self.episode_reward = 0.0
            self.episode_steps = 0
            self.action_counts = [0] * 8
            self._episode_flanking = 0.0

        return True

    # ── Public Properties for CurriculumCallback ────────────────

    def _compute_action_usage(self) -> dict:
        """Compute per-action usage fraction over the rolling window."""
        if not self._action_totals:
            return {}
        total_steps = sum(self._step_totals)
        if total_steps == 0:
            return {}
        # Sum action counts across all episodes in window
        summed = [0] * 8
        for ep_counts in self._action_totals:
            for i, c in enumerate(ep_counts):
                summed[i] += c
        return {
            ACTION_NAMES[i]: summed[i] / total_steps
            for i in range(8)
        }

    @property
    def rolling_win_rate(self) -> float:
        return sum(self._results) / len(self._results) if self._results else 0.0

    @property
    def rolling_avg_survivors(self) -> float:
        win_survivors = [s for s in self._survivors if s > 0]
        return sum(win_survivors) / len(win_survivors) if win_survivors else 0.0

    @property
    def rolling_action_usage(self) -> dict:
        return self._compute_action_usage()

    @property
    def rolling_timeout_rate(self) -> float:
        return sum(self._timeouts) / len(self._timeouts) if self._timeouts else 0.0

    @property
    def rolling_flanking_score(self) -> float:
        return sum(self._flanking_scores) / len(self._flanking_scores) if self._flanking_scores else 0.0

    def _on_training_end(self) -> None:
        if self._file:
            self._file.close()

# ── Curriculum Callback ─────────────────────────────────────────────

class CurriculumCallback(BaseCallback):
    """Mastery-based curriculum with promotion AND demotion.

    Reads curriculum stage configs from the GameProfile contract.

    Reads rolling stats from the EpisodeLogCallback:
      - rolling_win_rate, rolling_avg_survivors
      - rolling_action_usage (dict of action_name → fraction)
      - rolling_timeout_rate, rolling_flanking_score
      - episode_count, episodes_since_promotion

    Promotion: All graduation conditions must be met simultaneously.
    Demotion:  Win rate below floor for window episodes → drop one stage.
    """

    def __init__(
        self,
        episode_logger=None,
        profile: 'GameProfile' | None = None,
        verbose: int = 1,
    ):
        super().__init__(verbose)
        self.episode_logger = episode_logger
        self.profile = profile
        self._last_checked_episode = 0
        self._episodes_at_promotion = 0

        # Build stage configs from profile or use empty
        self._stage_configs: dict[int, dict] = {}
        if profile is not None:
            for stage_cfg in profile.training.curriculum:
                grad = {
                    "win_rate": stage_cfg.graduation.win_rate,
                    "min_episodes": stage_cfg.graduation.min_episodes,
                }
                if stage_cfg.graduation.avg_survivors is not None:
                    grad["avg_survivors"] = stage_cfg.graduation.avg_survivors
                if stage_cfg.graduation.action_usage:
                    grad["action_usage"] = dict(stage_cfg.graduation.action_usage)
                if stage_cfg.graduation.avg_flanking_score_min is not None:
                    grad["avg_flanking_score_min"] = stage_cfg.graduation.avg_flanking_score_min
                if stage_cfg.graduation.timeout_rate_max is not None:
                    grad["timeout_rate_max"] = stage_cfg.graduation.timeout_rate_max

                demotion = None
                if stage_cfg.demotion is not None:
                    demotion = {
                        "win_rate_floor": stage_cfg.demotion.win_rate_floor,
                        "window": stage_cfg.demotion.window,
                    }

                self._stage_configs[stage_cfg.stage] = {
                    "description": stage_cfg.description,
                    "graduation": grad,
                    "demotion": demotion,
                }

    def _on_step(self) -> bool:
        if self.episode_logger is None:
            return True

        current_ep = self.episode_logger.episode_count
        if current_ep == self._last_checked_episode:
            return True
        self._last_checked_episode = current_ep

        env = self._get_env()
        if env is None:
            return True

        current_stage = getattr(env, 'curriculum_stage', 1)
        eps_since_promo = current_ep - self._episodes_at_promotion

        # ── Check Demotion First ────────────────────────────────
        config = self._stage_configs.get(current_stage)
        if config and config.get("demotion"):
            demotion = config["demotion"]
            if eps_since_promo >= demotion["window"]:
                win_rate = self.episode_logger.rolling_win_rate
                if win_rate < demotion["win_rate_floor"]:
                    self._demote(env, current_stage, current_ep, win_rate)
                    return True

        # ── Check Graduation ────────────────────────────────────
        if config is None or "graduation" not in config:
            return True

        grad = config["graduation"]
        if eps_since_promo < grad.get("min_episodes", 100):
            return True

        # Collect all metrics
        win_rate = self.episode_logger.rolling_win_rate
        avg_surv = self.episode_logger.rolling_avg_survivors
        action_usage = self.episode_logger.rolling_action_usage
        timeout_rate = self.episode_logger.rolling_timeout_rate
        flanking_score = self.episode_logger.rolling_flanking_score

        # Check each condition
        reasons_met = []
        reasons_failed = []

        # 1. Win rate
        threshold = grad.get("win_rate", 0)
        if win_rate >= threshold:
            reasons_met.append(f"WR {win_rate:.0%} >= {threshold:.0%}")
        else:
            reasons_failed.append(f"WR {win_rate:.0%} < {threshold:.0%}")

        # 2. Avg survivors
        if "avg_survivors" in grad:
            threshold = grad["avg_survivors"]
            if avg_surv >= threshold:
                reasons_met.append(f"Surv {avg_surv:.1f} >= {threshold:.1f}")
            else:
                reasons_failed.append(f"Surv {avg_surv:.1f} < {threshold:.1f}")

        # 3. Action usage
        for action_name, min_usage in grad.get("action_usage", {}).items():
            actual = action_usage.get(action_name, 0.0)
            if actual >= min_usage:
                reasons_met.append(f"{action_name} {actual:.1%} >= {min_usage:.0%}")
            else:
                reasons_failed.append(f"{action_name} {actual:.1%} < {min_usage:.0%}")

        # 4. Flanking score
        if "avg_flanking_score_min" in grad:
            threshold = grad["avg_flanking_score_min"]
            if flanking_score > threshold:
                reasons_met.append(f"Flank {flanking_score:.3f} > {threshold}")
            else:
                reasons_failed.append(f"Flank {flanking_score:.3f} <= {threshold}")

        # 5. Timeout rate
        if "timeout_rate_max" in grad:
            threshold = grad["timeout_rate_max"]
            if timeout_rate <= threshold:
                reasons_met.append(f"Timeout {timeout_rate:.1%} <= {threshold:.0%}")
            else:
                reasons_failed.append(f"Timeout {timeout_rate:.1%} > {threshold:.0%}")

        # All conditions must pass
        if not reasons_failed:
            self._promote(env, current_stage, current_ep, reasons_met)
        elif self.verbose >= 2 and current_ep % 50 == 0:
            print(
                f"[Curriculum S{current_stage}] Ep {current_ep} | "
                f"Passed: {', '.join(reasons_met)} | "
                f"Blocked: {', '.join(reasons_failed)}"
            )

        return True

    def _get_env(self):
        if self.training_env and hasattr(self.training_env, 'envs'):
            return self.training_env.envs[0].unwrapped
        return None

    def _promote(self, env, from_stage, episode, reasons):
        next_stage = from_stage + 1
        env.curriculum_stage = next_stage
        self._episodes_at_promotion = episode

        if self.verbose >= 1:
            next_desc = self._stage_configs.get(next_stage, {}).get(
                'description', 'Final stage'
            )
            reasons_str = "\n".join(f"   ✅ {r}" for r in reasons)
            print(
                f"\n{'='*60}\n"
                f"🎓 STAGE {from_stage} → STAGE {next_stage} PROMOTION!\n"
                f"   Episode:   {episode}\n"
                f"   Timesteps: {self.num_timesteps}\n"
                f"{reasons_str}\n"
                f"   Next: {next_desc}\n"
                f"{'='*60}\n"
            )

    def _demote(self, env, from_stage, episode, win_rate):
        prev_stage = max(1, from_stage - 1)
        env.curriculum_stage = prev_stage
        self._episodes_at_promotion = episode

        if self.verbose >= 1:
            print(
                f"\n{'='*60}\n"
                f"⚠️  STAGE {from_stage} → STAGE {prev_stage} DEMOTION!\n"
                f"   Episode:   {episode}\n"
                f"   Win Rate:  {win_rate:.0%} (below floor)\n"
                f"   Reason:    Catastrophic forgetting prevention\n"
                f"   Action:    Rebuilding confidence at Stage {prev_stage}\n"
                f"{'='*60}\n"
            )
