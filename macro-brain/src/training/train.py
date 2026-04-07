"""Training entrypoint for Mass-Swarm AI Simulator.

Usage:
    python -m src.training.train --profile profiles/default_swarm_combat.json
    python -m src.training.train --timesteps 500000

All game parameters are loaded from the game profile JSON.
"""

import argparse
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.vec_env import DummyVecEnv

from src.config.game_profile import load_profile
from src.env.swarm_env import SwarmEnv
from src.training.callbacks import CurriculumCallback
from src.training.callbacks import EnvStatCallback, EpisodeLogCallback


def make_env(profile, args):
    def _init():
        env_config = {
            "profile": profile,
            "curriculum_stage": 1,
        }
        env = SwarmEnv(config=env_config)
        env = ActionMasker(env, lambda e: e.action_masks())
        return env
    return _init


def main():
    parser = argparse.ArgumentParser(description="Mass-Swarm AI Training")
    parser.add_argument(
        "--profile", type=str,
        default="profiles/default_swarm_combat.json",
        help="Path to game profile JSON (default: profiles/default_swarm_combat.json)",
    )
    parser.add_argument("--timesteps", type=int, default=100_000)
    parser.add_argument("--checkpoint-dir", default="./checkpoints")
    args = parser.parse_args()

    # Load the game profile — single source of truth for everything
    profile = load_profile(args.profile)
    print(f"📋 Loaded profile: {profile.meta.name} v{profile.meta.version}")
    print(f"   {profile.meta.description}")
    print(f"   Factions: {', '.join(f.name for f in profile.factions)}")
    print(f"   Actions:  {profile.num_actions}")
    print(f"   Stages:   {len(profile.training.curriculum)}")

    vec_env = DummyVecEnv([make_env(profile, args)])

    print(f"Using cpu device")
    model = MaskablePPO(
        "MultiInputPolicy",
        vec_env,
        verbose=1,
        tensorboard_log="./tb_logs/",
    )

    # Create episode logger first — curriculum reads from it
    episode_logger = EpisodeLogCallback(log_path="./episode_log.csv")

    callbacks = [
        CheckpointCallback(
            save_freq=10000,
            save_path=args.checkpoint_dir,
            name_prefix="ppo_swarm",
        ),
        EnvStatCallback(),
        episode_logger,
        CurriculumCallback(
            episode_logger=episode_logger,
            profile=profile,
            verbose=1,
        ),
    ]

    model.learn(total_timesteps=args.timesteps, callback=callbacks)


if __name__ == "__main__":
    main()
