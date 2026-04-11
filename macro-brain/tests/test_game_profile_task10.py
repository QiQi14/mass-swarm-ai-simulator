import pytest
from pathlib import Path
from src.config.game_profile import load_profile

def test_tactical_curriculum_profile_loads_and_has_correct_structure():
    profile_path = Path('profiles/tactical_curriculum.json')
    assert profile_path.exists(), "tactical_curriculum.json does not exist"
    
    # 1. Profile loads without errors
    profile = load_profile(profile_path)
    assert profile is not None, "Profile failed to load"
    
    # 2. Profile has 8 actions
    assert profile.num_actions == 8, f"Expected 8 actions, found {profile.num_actions}"
    
    # 8. Profile has 9 curriculum stages (0-8)
    assert len(profile.training.curriculum) == 9, f"Expected 9 stages, found {len(profile.training.curriculum)}"

    # 9. curriculum[7].graduation.win_rate == 0.75 (Stage 7: Protected Target)
    stage7_win_rate = profile.training.curriculum[7].graduation.win_rate
    assert stage7_win_rate == 0.75, f"Expected Stage 7 win_rate 0.75, found {stage7_win_rate}"

def test_old_profiles_deleted():
    # 9. Old profiles deleted or deprecated
    assert not Path('profiles/stage1_tactical.json').exists(), "stage1_tactical.json should be deleted"
    assert not Path('profiles/default_swarm_combat.json').exists(), "default_swarm_combat.json should be deleted"
