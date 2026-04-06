import argparse
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.vec_env import DummyVecEnv

from src.env.swarm_env import SwarmEnv
from src.training.curriculum import CurriculumCallback
from src.training.callbacks import EnvStatCallback

def make_env(args):
    def _init():
        env_config = {"max_steps": args.max_steps, "curriculum_stage": 1 if args.curriculum else 2}
        env = SwarmEnv(config=env_config)
        env = ActionMasker(env, lambda e: e.action_masks())
        return env
    return _init

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=100_000)
    parser.add_argument("--max-steps", type=int, default=200)
    parser.add_argument("--checkpoint-dir", default="./checkpoints")
    parser.add_argument("--curriculum", action="store_true")
    args = parser.parse_args()
    
    vec_env = DummyVecEnv([make_env(args)])
    
    model = MaskablePPO(
        "MultiInputPolicy",
        vec_env,
        verbose=1,
        tensorboard_log="./tb_logs/",
    )
    
    callbacks = [
        CheckpointCallback(save_freq=10000, save_path=args.checkpoint_dir, name_prefix="ppo_swarm"),
        EnvStatCallback()
    ]
    if args.curriculum:
        callbacks.append(CurriculumCallback(verbose=1))
    
    model.learn(total_timesteps=args.timesteps, callback=callbacks)

if __name__ == "__main__":
    main()
