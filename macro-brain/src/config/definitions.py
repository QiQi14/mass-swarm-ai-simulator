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
    zone_modifier_duration_ticks: int = 1500


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
    # New tactical reward weights
    approach_scale: float = 0.02
    exploration_reward: float = 0.005
    exploration_decay_threshold: float = 0.8  # decay to 0 after 80% explored
    threat_priority_bonus: float = 2.0
    flanking_bonus_scale: float = 0.1
    lure_success_bonus: float = 3.0
    debuff_bonus: float = 2.0


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


# ── Bot Configuration ─────────────────────────────────────────────────

@dataclass(frozen=True)
class BotStrategyDef:
    """Abstract bot strategy — maps to Rust BotStrategy enum."""
    type: str  # "Charge", "HoldPosition", "Adaptive", "Mixed", "Patrol"
    target_faction: int | None = None
    x: float | None = None
    y: float | None = None
    retreat_health_fraction: float | None = None
    retreat_x: float | None = None
    retreat_y: float | None = None
    strategies: list | None = None  # list of BotStrategyDef dicts for Mixed
    waypoints: list | None = None  # list of {"x": float, "y": float} for Patrol
    waypoint_threshold: float = 50.0  # proximity to switch waypoint

    def to_dict(self) -> dict:
        """Serialize to ZMQ payload format matching Rust serde(tag='type')."""
        d = {"type": self.type}
        if self.type == "Charge":
            d["target_faction"] = self.target_faction
        elif self.type == "HoldPosition":
            d["x"] = self.x
            d["y"] = self.y
        elif self.type == "Adaptive":
            d["target_faction"] = self.target_faction
            d["retreat_health_fraction"] = self.retreat_health_fraction
            d["retreat_x"] = self.retreat_x
            d["retreat_y"] = self.retreat_y
        elif self.type == "Mixed":
            d["strategies"] = [s.to_dict() if isinstance(s, BotStrategyDef)
                               else s for s in (self.strategies or [])]
        elif self.type == "Patrol":
            d["waypoints"] = self.waypoints or []
            d["waypoint_threshold"] = self.waypoint_threshold
        return d


@dataclass(frozen=True)
class BotStageBehaviorDef:
    """Bot behavior config for a specific curriculum stage."""
    stage: int
    faction_id: int
    strategy: BotStrategyDef
    eval_interval_ticks: int = 60


# ── Root Profile ────────────────────────────────────────────────────

@dataclass(frozen=True)
class ProfileMeta:
    name: str
    version: str
    description: str
