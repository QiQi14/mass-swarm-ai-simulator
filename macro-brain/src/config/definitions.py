from __future__ import annotations

from dataclasses import dataclass, field


# ── World ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class WorldConfig:
    width: float
    height: float
    grid_width: int
    grid_height: int
    cell_size: float


# ── Factions ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FactionStats:
    hp: float


@dataclass(frozen=True)
class FactionConfig:
    id: int
    name: str
    role: str  # "brain" or "bot"
    stats: FactionStats
    default_count: int


# ── Combat ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class StatEffectConfig:
    stat_index: int
    delta_per_second: float


@dataclass(frozen=True)
class CombatRuleConfig:
    source_faction: int
    target_faction: int
    range: float
    effects: list[StatEffectConfig]


@dataclass(frozen=True)
class CombatConfig:
    rules: list[CombatRuleConfig]


# ── Movement ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MovementConfigDef:
    max_speed: float
    steering_factor: float
    separation_radius: float
    separation_weight: float
    flow_weight: float


# ── Environment Configs ─────────────────────────────────────────────

@dataclass(frozen=True)
class TerrainThresholdsDef:
    impassable_threshold: int
    destructible_min: int


@dataclass(frozen=True)
class StatModifierDef:
    stat_index: int
    modifier_type: str
    value: float


@dataclass(frozen=True)
class ActivateBuffDef:
    modifiers: list[StatModifierDef]
    duration_ticks: int


@dataclass(frozen=True)
class AbilitiesDef:
    buff_cooldown_ticks: int
    movement_speed_stat: int | None
    combat_damage_stat: int | None
    activate_buff: ActivateBuffDef


@dataclass(frozen=True)
class RemovalRuleDef:
    stat_index: int
    threshold: float
    condition: str


# ── Actions ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ActionDef:
    index: int
    name: str
    unlock_stage: int


# ── Training / Rewards / Curriculum ─────────────────────────────────

@dataclass(frozen=True)
class RewardWeights:
    time_penalty_per_step: float
    kill_reward: float
    death_penalty: float
    win_terminal: float
    loss_terminal: float
    survival_bonus_multiplier: float


@dataclass(frozen=True)
class GraduationConfig:
    win_rate: float
    min_episodes: int
    avg_survivors: float | None = None
    action_usage: dict[str, float] = field(default_factory=dict)
    avg_flanking_score_min: float | None = None
    timeout_rate_max: float | None = None


@dataclass(frozen=True)
class DemotionConfig:
    win_rate_floor: float
    window: int


@dataclass(frozen=True)
class CurriculumStageConfig:
    stage: int
    description: str
    graduation: GraduationConfig
    demotion: DemotionConfig | None = None


@dataclass(frozen=True)
class TrainingConfig:
    max_density: float
    max_steps: int
    ai_eval_interval_ticks: int
    observation_channels: int
    rewards: RewardWeights
    curriculum: list[CurriculumStageConfig]


# ── Root Profile ────────────────────────────────────────────────────

@dataclass(frozen=True)
class ProfileMeta:
    name: str
    version: str
    description: str
