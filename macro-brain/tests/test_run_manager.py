import json
from pathlib import Path
from unittest.mock import patch
from datetime import datetime

import pytest

from src.training.run_manager import RunConfig, create_run


def test_run_config_paths():
    """Verify RunConfig calculates paths correctly relative to base_dir."""
    base = Path("/fake/run_dir")
    config = RunConfig(
        run_id="run_123",
        profile_name="test_profile",
        profile_path="fake.json",
        base_dir=base
    )

    assert config.checkpoint_dir == base / "checkpoints"
    assert config.tensorboard_dir == base / "tb_logs"
    assert config.episode_log_path == base / "episode_log.csv"
    assert config.profile_snapshot_path == base / "profile_snapshot.json"


def test_create_run(tmp_path):
    """Verify create_run creates directories and copies the profile correctly."""
    # Setup a dummy profile to copy
    profile_path = tmp_path / "dummy_profile.json"
    profile_path.write_text('{"test": "data"}')

    runs_dir = tmp_path / "runs"
    
    # Execute create_run
    config = create_run(
        profile_path=str(profile_path),
        profile_name="Test Profile",
        runs_dir=str(runs_dir)
    )

    # Verify RunConfig structure
    assert config.profile_name == "Test Profile"
    assert config.profile_path == str(profile_path)
    assert config.run_id.startswith("run_")
    
    # Verify directories exist
    assert config.base_dir.exists()
    assert config.checkpoint_dir.exists()
    assert config.tensorboard_dir.exists()

    # Verify profile was copied
    assert config.profile_snapshot_path.exists()
    
    # Check copied contents
    copied_content = json.loads(config.profile_snapshot_path.read_text())
    assert copied_content == {"test": "data"}


def test_create_run_unique_ids(tmp_path):
    """Verify that multiple calls produce different run IDs based on timestamp."""
    profile_path = tmp_path / "dummy_profile.json"
    profile_path.write_text("{}")
    
    runs_dir = tmp_path / "runs"

    with patch('src.training.run_manager.datetime') as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 8, 12, 0, 0)
        config1 = create_run(str(profile_path), "P1", str(runs_dir))
        
        mock_dt.now.return_value = datetime(2026, 4, 8, 12, 0, 1)
        config2 = create_run(str(profile_path), "P2", str(runs_dir))

    assert config1.run_id != config2.run_id
    assert config1.run_id == "run_20260408_120000"
    assert config2.run_id == "run_20260408_120001"
