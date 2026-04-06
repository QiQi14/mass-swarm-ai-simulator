from stable_baselines3.common.callbacks import BaseCallback

class CurriculumCallback(BaseCallback):
    """Stage 1→2 promotion when mean_reward > threshold."""
    
    def __init__(self, stage1_threshold=0.3, window=50, verbose=0):
        super().__init__(verbose)
        self.stage1_threshold = stage1_threshold
        self.window = window
        self.rewards = []
    
    def _on_step(self) -> bool:
        if "rewards" in self.locals:
            reward = self.locals["rewards"][0]
            self.rewards.append(reward)
            if len(self.rewards) > self.window:
                self.rewards.pop(0)
                
            mean_reward = sum(self.rewards) / len(self.rewards)
            
            if self.training_env and hasattr(self.training_env, 'envs'):
                env = self.training_env.envs[0].unwrapped
                if hasattr(env, 'curriculum_stage') and env.curriculum_stage == 1:
                    if len(self.rewards) == self.window and mean_reward > self.stage1_threshold:
                        if self.verbose:
                            print(f"Promoting to Stage 2 (mean_reward={mean_reward:.2f})")
                        self._promote_to_stage2()
                
        return True

    def _promote_to_stage2(self):
        """Enable terrain randomization and full action space."""
        for env in self.training_env.envs:
            env.unwrapped.curriculum_stage = 2
