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
    primary_stat: float  # Generic primary resource (context-agnostic)


@dataclass(frozen=True)
class FactionConfig:
    id: int
    name: str
    role: str  # "brain" or "bot"
    stats: FactionStats
    default_count: int


@dataclass(frozen=True)
class UnitClassConfig:
    """Single unit class definition from game profile.
    
    The class_id is context-agnostic — the engine doesn't know
    what 'Sniper' or 'Tank' means. The name is for humans only.
    """
    class_id: int
    name: str  # For human readability only — engine ignores this
    stats: FactionStats  # Default stats for this class
    default_count: int = 0


# ── Combat ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class StatEffectConfig:
    stat_index: int
    delta_per_second: float


@dataclass(frozen=True)
class MitigationConfig:
    """Stat-driven damage mitigation configuration."""
    stat_index: int
    mode: str  # "PercentReduction" or "FlatReduction"


# ── AoE Configuration (mirrors Rust AoeConfig) ─────────────────────

@dataclass(frozen=True)
class AoeShapeDef:
    """AoE damage shape. Matches Rust AoeShape enum with serde(tag='type').

    type must be 'Circle', 'Ellipse', or 'ConvexPolygon'.
    """
    type: str  # "Circle", "Ellipse", "ConvexPolygon"
    # Circle fields
    radius: float | None = None
    # Ellipse fields
    semi_major: float | None = None
    semi_minor: float | None = None
    # ConvexPolygon fields — list of [dx, dy] offsets, CCW wound
    vertices: list[list[float]] | None = None
    # Rotation (for Ellipse/ConvexPolygon)
    rotation_mode: str | None = None  # "TargetAligned" or {"Fixed": angle}

    def to_dict(self) -> dict:
        d: dict = {"type": self.type}
        if self.type == "Circle":
            d["radius"] = self.radius
        elif self.type == "Ellipse":
            d["semi_major"] = self.semi_major
            d["semi_minor"] = self.semi_minor
            if self.rotation_mode:
                d["rotation_mode"] = self.rotation_mode
        elif self.type == "ConvexPolygon":
            d["vertices"] = self.vertices
            if self.rotation_mode:
                d["rotation_mode"] = self.rotation_mode
        return d


@dataclass(frozen=True)
class AoeConfigDef:
    """AoE damage area configuration. Matches Rust AoeConfig struct."""
    shape: AoeShapeDef
    falloff: str  # "None", "Linear", "Quadratic"

    def to_dict(self) -> dict:
        return {
            "shape": self.shape.to_dict(),
            "falloff": self.falloff,
        }


# ── Penetration Configuration (mirrors Rust PenetrationConfig) ─────

@dataclass(frozen=True)
class EnergyModelDef:
    """Penetration energy model. Matches Rust EnergyModel enum.

    type must be 'Kinetic' or 'Beam'.
    """
    type: str  # "Kinetic" or "Beam"
    base_energy: float | None = None  # Only for Kinetic

    def to_dict(self) -> dict:
        if self.type == "Kinetic":
            return {"Kinetic": {"base_energy": self.base_energy}}
        return "Beam"


@dataclass(frozen=True)
class PenetrationConfigDef:
    """Penetration (piercing) damage configuration.

    Matches Rust PenetrationConfig struct.
    """
    ray_width: float
    energy_model: EnergyModelDef
    absorption_stat_index: int
    absorption_ignores_mitigation: bool = True
    max_targets: int | None = None

    def to_dict(self) -> dict:
        d = {
            "ray_width": self.ray_width,
            "energy_model": self.energy_model.to_dict(),
            "absorption_stat_index": self.absorption_stat_index,
            "absorption_ignores_mitigation": self.absorption_ignores_mitigation,
        }
        if self.max_targets is not None:
            d["max_targets"] = self.max_targets
        return d


@dataclass(frozen=True)
class CombatRuleConfig:
    source_faction: int
    target_faction: int
    range: float
    effects: list[StatEffectConfig]
    source_class: int | None = None
    target_class: int | None = None
    range_stat_index: int | None = None
    mitigation: MitigationConfig | None = None
    cooldown_ticks: int | None = None
    aoe: AoeConfigDef | None = None
    penetration: PenetrationConfigDef | None = None


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
class SkillDef:
    index: int
    name: str
    modifiers: list[StatModifierDef]
    duration_ticks: int
    cooldown_ticks: int


@dataclass(frozen=True)
class AbilitiesDef:
    buff_cooldown_ticks: int
    movement_speed_stat: int | None
    combat_damage_stat: int | None
    activate_buff: ActivateBuffDef
    zone_modifier_duration_ticks: int = 1500
    skills: list[SkillDef] | None = None


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
