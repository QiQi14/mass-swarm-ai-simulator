import pytest
from dataclasses import replace
from src.config.validator import validate_profile
from src.config.definitions import (
    ProfileMeta, WorldConfig, FactionConfig, FactionStats, CombatConfig, 
    CombatRuleConfig, MovementConfigDef, TerrainThresholdsDef, AbilitiesDef, 
    ActionDef, TrainingConfig, CurriculumStageConfig, GraduationConfig, RewardWeights,
    ActivateBuffDef, StatModifierDef
)
from src.config.game_profile import GameProfile

def _build_valid_profile():
    return GameProfile(
        meta=ProfileMeta(name="Test", version="1.0", description="Test"),
        world=WorldConfig(width=1000, height=1000, grid_width=100, grid_height=100, cell_size=10.0),
        factions=[
            FactionConfig(id=0, name="Brain", role="brain", stats=FactionStats(hp=100), default_count=10),
            FactionConfig(id=1, name="Bot", role="bot", stats=FactionStats(hp=100), default_count=10)
        ],
        combat=CombatConfig(rules=[
            CombatRuleConfig(source_faction=0, target_faction=1, range=50.0, effects=[])
        ]),
        movement=MovementConfigDef(max_speed=1.0, steering_factor=1.0, separation_radius=1.0, separation_weight=1.0, flow_weight=1.0),
        terrain_thresholds=TerrainThresholdsDef(impassable_threshold=1, destructible_min=1),
        abilities=AbilitiesDef(
            buff_cooldown_ticks=10, 
            movement_speed_stat=1, 
            combat_damage_stat=1,
            activate_buff=ActivateBuffDef(modifiers=[], duration_ticks=10)
        ),
        removal_rules=[],
        actions=[
            ActionDef(index=0, name="Action1", unlock_stage=1),
            ActionDef(index=1, name="Action2", unlock_stage=1)
        ],
        training=TrainingConfig(
            max_density=1.0, max_steps=100, ai_eval_interval_ticks=10, observation_channels=1,
            rewards=RewardWeights(time_penalty_per_step=0, kill_reward=0, death_penalty=0, win_terminal=0, loss_terminal=0, survival_bonus_multiplier=0),
            curriculum=[
                CurriculumStageConfig(
                    stage=1, description="Stage 1", 
                    graduation=GraduationConfig(win_rate=0.5, min_episodes=10, action_usage={"Action1": 1.0})
                )
            ]
        )
    )

@pytest.fixture
def valid_profile():
    return _build_valid_profile()

def test_valid_profile(valid_profile):
    result = validate_profile(valid_profile)
    assert result.valid is True
    assert len(result.errors) == 0
    assert len(result.warnings) == 0

def test_v1_duplicate_facton_ids():
    profile = _build_valid_profile()
    new_factions = list(profile.factions) + [
        FactionConfig(id=0, name="Bot2", role="bot", stats=FactionStats(hp=100), default_count=10)
    ]
    invalid_profile = replace(profile, factions=new_factions)
    result = validate_profile(invalid_profile)
    assert result.valid is False
    assert any(e.startswith("V1") for e in result.errors)

def test_v2_two_brain_factions():
    profile = _build_valid_profile()
    new_factions = list(profile.factions) + [
        FactionConfig(id=2, name="Brain2", role="brain", stats=FactionStats(hp=100), default_count=10)
    ]
    invalid_profile = replace(profile, factions=new_factions)
    result = validate_profile(invalid_profile)
    assert result.valid is False
    assert any(e.startswith("V2") for e in result.errors)

def test_v3_no_bot_factions():
    profile = _build_valid_profile()
    # Keep only the brain faction
    new_factions = [f for f in profile.factions if f.role == "brain"]
    invalid_profile = replace(profile, factions=new_factions)
    result = validate_profile(invalid_profile)
    assert result.valid is False
    assert any(e.startswith("V3") for e in result.errors)

def test_v4_combat_rule_invalid_faction():
    profile = _build_valid_profile()
    new_combat = CombatConfig(rules=[
        CombatRuleConfig(source_faction=99, target_faction=1, range=50.0, effects=[])
    ])
    invalid_profile = replace(profile, combat=new_combat)
    result = validate_profile(invalid_profile)
    assert result.valid is False
    assert any(e.startswith("V4") for e in result.errors)

def test_v5_non_contiguous_actions():
    profile = _build_valid_profile()
    new_actions = list(profile.actions) + [
        ActionDef(index=3, name="Action4", unlock_stage=1)
    ]
    invalid_profile = replace(profile, actions=new_actions)
    result = validate_profile(invalid_profile)
    assert result.valid is False
    assert any(e.startswith("V5") for e in result.errors)

def test_v6_non_sequential_curriculum():
    profile = _build_valid_profile()
    new_curriculum = list(profile.training.curriculum) + [
        CurriculumStageConfig(
            stage=3, description="Stage 3", 
            graduation=GraduationConfig(win_rate=0.5, min_episodes=10)
        )
    ]
    new_training = replace(profile.training, curriculum=new_curriculum)
    invalid_profile = replace(profile, training=new_training)
    result = validate_profile(invalid_profile)
    assert result.valid is False
    assert any(e.startswith("V6") for e in result.errors)

def test_v7_invalid_action_usage():
    profile = _build_valid_profile()
    grad = replace(profile.training.curriculum[0].graduation, action_usage={"NonExistent": 1.0})
    stage = replace(profile.training.curriculum[0], graduation=grad)
    new_curriculum = [stage]
    new_training = replace(profile.training, curriculum=new_curriculum)
    invalid_profile = replace(profile, training=new_training)
    result = validate_profile(invalid_profile)
    assert result.valid is True
    assert any(w.startswith("V7") for w in result.warnings)

def test_v8_invalid_unlock_stage():
    profile = _build_valid_profile()
    new_actions = list(profile.actions) + [
        ActionDef(index=2, name="Action3", unlock_stage=5)
    ]
    invalid_profile = replace(profile, actions=new_actions)
    result = validate_profile(invalid_profile)
    assert result.valid is True
    assert any(w.startswith("V8") for w in result.warnings)

def test_v9_invalid_world_dimensions():
    profile = _build_valid_profile()
    new_world = WorldConfig(width=2000, height=1000, grid_width=100, grid_height=100, cell_size=10.0)
    invalid_profile = replace(profile, world=new_world)
    result = validate_profile(invalid_profile)
    assert result.valid is True
    assert any(w.startswith("V9") for w in result.warnings)
