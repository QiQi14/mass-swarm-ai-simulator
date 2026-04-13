import gymnasium as gym

class FrameSkipWrapper(gym.Wrapper):
    """
    Return only every `skip`-th frame.
    Repeats the action `skip` times and accumulates the reward.
    
    This solves the "action jitter" issue by allowing the swarm 
    sufficient time to navigate towards the selected coordinate 
    before providing the RL model another chance to change it.
    """
    def __init__(self, env: gym.Env, skip: int = 5):
        super().__init__(env)
        self._skip = skip

    def step(self, action):
        total_reward = 0.0
        obs, terminated, truncated, info = None, False, False, {}
        
        for _ in range(self._skip):
            obs, reward, terminated, truncated, info = self.env.step(action)
            total_reward += reward
            if terminated or truncated:
                break
                
        return obs, total_reward, terminated, truncated, info

    def action_masks(self):
        """Pass through for the SB3 ActionMasker."""
        if hasattr(self.env, "action_masks"):
            return self.env.action_masks()
        elif hasattr(self.env.unwrapped, "action_masks"):
            return self.env.unwrapped.action_masks()
        else:
            raise NotImplementedError("Underlying env does not implement action_masks")
