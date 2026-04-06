from stable_baselines3.common.callbacks import BaseCallback

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
