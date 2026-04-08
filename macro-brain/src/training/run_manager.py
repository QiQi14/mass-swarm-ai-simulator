import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class RunConfig:
    """Metadata and paths for a single training run."""
    run_id: str
    profile_name: str
    profile_path: str
    base_dir: Path

    @property
    def checkpoint_dir(self) -> Path:
        return self.base_dir / "checkpoints"

    @property
    def tensorboard_dir(self) -> Path:
        return self.base_dir / "tb_logs"

    @property
    def episode_log_path(self) -> Path:
        return self.base_dir / "episode_log.csv"

    @property
    def profile_snapshot_path(self) -> Path:
        return self.base_dir / "profile_snapshot.json"


def create_run(
    profile_path: str,
    profile_name: str,
    runs_dir: str = "./runs",
) -> RunConfig:
    """Create a new run directory with timestamped ID.

    Args:
        profile_path: Path to the game profile JSON.
        profile_name: Human-readable name from profile.meta.name.
        runs_dir: Base directory for all runs.

    Returns:
        RunConfig with all paths set and directories created.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"run_{timestamp}"
    base_dir = Path(runs_dir) / run_id

    config = RunConfig(
        run_id=run_id,
        profile_name=profile_name,
        profile_path=profile_path,
        base_dir=base_dir,
    )

    # Create directory structure
    config.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    config.tensorboard_dir.mkdir(parents=True, exist_ok=True)

    # Snapshot the profile (reproducibility)
    shutil.copy2(profile_path, config.profile_snapshot_path)

    return config
