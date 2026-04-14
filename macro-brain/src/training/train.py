"""Training entrypoint for Mass-Swarm AI Simulator.

Stage 1 Tactical: 3-faction decision training.

Usage:
    python -m src.training.train --profile profiles/stage1_tactical.json
    python -m src.training.train --timesteps 500000
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
from src.models.feature_extractor import TacticalExtractor

from src.env.wrappers import FrameSkipWrapper

def make_env(profile, args):
    def _init():
        env_config = {
            "profile": profile,
            "curriculum_stage": args.start_stage,
        }
        env = SwarmEnv(config=env_config)
        env = FrameSkipWrapper(env, skip=5)
        env = ActionMasker(env, lambda e: e.action_masks())
        return env
    return _init


def main():
    parser = argparse.ArgumentParser(description="Mass-Swarm AI Training")
    parser.add_argument("--profile", type=str,
        default="profiles/tactical_curriculum.json")
    parser.add_argument("--timesteps", type=int, default=100_000)
    parser.add_argument("--runs-dir", default="./runs")
    parser.add_argument("--load-checkpoint", type=str, default=None,
        help="Path to a zip file to resume training from.")
    parser.add_argument("--start-stage", type=int, default=0,
        help="Curriculum stage to start from when resuming.")
    args = parser.parse_args()

    # 1. Load and VALIDATE profile
    from src.config.validator import validate_profile
    profile = load_profile(args.profile)
    result = validate_profile(profile)
    if not result.valid:
        import sys
        print("❌ Profile validation failed:")
        for e in result.errors:
            print(f"  ERROR: {e}")
        sys.exit(1)
    for w in result.warnings:
        print(f"  ⚠️  {w}")

    # 2. Create run directory
    from src.training.run_manager import create_run
    run = create_run(
        profile_path=args.profile,
        profile_name=profile.meta.name,
        runs_dir=args.runs_dir,
    )

    # 3. Write initial stage snapshot for debug visualizer
    import json
    from src.training.curriculum import get_stage_snapshot
    snapshot = get_stage_snapshot(args.start_stage, profile=profile)
    with open(run.stage_snapshot_path, "w") as f:
        json.dump(snapshot, f, indent=2)

    # 4. Print banner
    print(f"{'='*60}")
    print(f"🚀 Training Run: {run.run_id}")
    print(f"   Profile:     {profile.meta.name} v{profile.meta.version}")
    print(f"   Factions:    {', '.join(f.name for f in profile.factions)}")
    print(f"   Actions:     {profile.num_actions}")
    print(f"   Stages:      {len(profile.training.curriculum)}")
    print(f"   Output:      {run.base_dir}")
    print(f"{'='*60}")

    # 4. Setup env, model, callbacks with run paths
    vec_env = DummyVecEnv([make_env(profile, args)])

    policy_kwargs = {
        "features_extractor_class": TacticalExtractor,
        "features_extractor_kwargs": {"features_dim": 256},
    }

    if args.load_checkpoint:
        print(f"Loading model checkpoint from {args.load_checkpoint}...")
        model = MaskablePPO.load(
            args.load_checkpoint,
            env=vec_env,
            custom_objects={"policy_kwargs": policy_kwargs, "tensorboard_log": str(run.tensorboard_dir)},
        )
        model.tensorboard_log = str(run.tensorboard_dir)
    else:
        model = MaskablePPO(
            "MultiInputPolicy",
            vec_env,
            verbose=1,
            tensorboard_log=str(run.tensorboard_dir),
            policy_kwargs=policy_kwargs,
            learning_rate=3e-4,
            n_steps=2048,
            batch_size=64,
            n_epochs=10,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.01,
        )

    episode_logger = EpisodeLogCallback(
        log_path=str(run.episode_log_path),
        num_actions=8,  # was 3
    )

    callbacks = [
        CheckpointCallback(
            save_freq=10000,
            save_path=str(run.checkpoint_dir),
            name_prefix="ppo_swarm",
        ),
        EnvStatCallback(),
        episode_logger,
        CurriculumCallback(
            episode_logger=episode_logger,
            profile=profile,
            verbose=1,
            checkpoint_dir=str(run.checkpoint_dir),
            run_dir=str(run.base_dir),
        ),
    ]

    model.learn(total_timesteps=args.timesteps, callback=callbacks)


if __name__ == "__main__":
    main()
