"""Game profile parser — converts raw JSON dicts to typed GameProfile.

Extracted from game_profile.py to meet the 200-line file size convention.
"""

from __future__ import annotations

from typing import Any

from src.config.definitions import (
    WorldConfig, FactionStats, FactionConfig, StatEffectConfig,
    MitigationConfig, UnitClassConfig,
    AoeShapeDef, AoeConfigDef, EnergyModelDef, PenetrationConfigDef,
    CombatRuleConfig, CombatConfig, MovementConfigDef, TerrainThresholdsDef,
    StatModifierDef, ActivateBuffDef, AbilitiesDef, RemovalRuleDef,
    ActionDef, RewardWeights, GraduationConfig, DemotionConfig,
    CurriculumStageConfig, TrainingConfig, ProfileMeta,
    BotStrategyDef, BotStageBehaviorDef
)


def _parse_profile(raw: dict[str, Any]):
    """Parse raw JSON dict into typed GameProfile.

    Returns a GameProfile instance. Import is deferred to avoid circular deps.
    """
    from src.config.game_profile import GameProfile

    def _parse_strategy(raw_strat: dict) -> BotStrategyDef:
        strats = raw_strat.get("strategies")
        waypoints = raw_strat.get("waypoints")
        return BotStrategyDef(
            type=raw_strat["type"],
            target_faction=raw_strat.get("target_faction"),
            x=raw_strat.get("x"),
            y=raw_strat.get("y"),
            retreat_health_fraction=raw_strat.get("retreat_health_fraction"),
            retreat_x=raw_strat.get("retreat_x"),
            retreat_y=raw_strat.get("retreat_y"),
            strategies=[_parse_strategy(s) for s in strats] if strats else None,
            waypoints=waypoints,
            waypoint_threshold=raw_strat.get("waypoint_threshold", 50.0),
        )

    def _parse_unit_registry(raw: dict) -> list[UnitClassConfig]:
        """Parse optional unit_registry from game profile. Returns [] if absent."""
        registry = raw.get("unit_registry", [])
        return [
            UnitClassConfig(
                class_id=entry["class_id"],
                name=entry["name"],
                stats=FactionStats(primary_stat=entry["stats"].get("primary_stat", entry["stats"].get("hp", 100.0))),
                default_count=entry.get("default_count", 0),
            )
            for entry in registry
        ]

    def _parse_combat_rule(raw_rule: dict) -> CombatRuleConfig:
        mitigation_raw = raw_rule.get("mitigation")
        mitigation = MitigationConfig(
            stat_index=mitigation_raw["stat_index"],
            mode=mitigation_raw["mode"],
        ) if mitigation_raw else None

        # Parse AoE config
        aoe_raw = raw_rule.get("aoe")
        aoe = None
        if aoe_raw:
            shape_raw = aoe_raw["shape"]
            shape = AoeShapeDef(
                type=shape_raw["type"],
                radius=shape_raw.get("radius"),
                semi_major=shape_raw.get("semi_major"),
                semi_minor=shape_raw.get("semi_minor"),
                vertices=shape_raw.get("vertices"),
                rotation_mode=shape_raw.get("rotation_mode"),
            )
            aoe = AoeConfigDef(shape=shape, falloff=aoe_raw["falloff"])

        # Parse Penetration config
        pen_raw = raw_rule.get("penetration")
        penetration = None
        if pen_raw:
            em_raw = pen_raw["energy_model"]
            if isinstance(em_raw, dict) and "Kinetic" in em_raw:
                energy_model = EnergyModelDef(
                    type="Kinetic", base_energy=em_raw["Kinetic"]["base_energy"]
                )
            else:
                energy_model = EnergyModelDef(type="Beam")
            penetration = PenetrationConfigDef(
                ray_width=pen_raw["ray_width"],
                energy_model=energy_model,
                absorption_stat_index=pen_raw["absorption_stat_index"],
                absorption_ignores_mitigation=pen_raw.get(
                    "absorption_ignores_mitigation", True
                ),
                max_targets=pen_raw.get("max_targets"),
            )

        return CombatRuleConfig(
            source_faction=raw_rule["source_faction"],
            target_faction=raw_rule["target_faction"],
            range=raw_rule["range"],
            effects=[StatEffectConfig(**e) for e in raw_rule["effects"]],
            source_class=raw_rule.get("source_class"),
            target_class=raw_rule.get("target_class"),
            range_stat_index=raw_rule.get("range_stat_index"),
            mitigation=mitigation,
            cooldown_ticks=raw_rule.get("cooldown_ticks"),
            aoe=aoe,
            penetration=penetration,
        )

    meta = ProfileMeta(**raw["meta"])

    world = WorldConfig(**raw["world"])

    factions = [
        FactionConfig(
            id=f["id"],
            name=f["name"],
            role=f["role"],
            stats=FactionStats(primary_stat=f["stats"].get("primary_stat", f["stats"].get("hp", 100.0))),
            default_count=f["default_count"],
        )
        for f in raw["factions"]
    ]

    combat = CombatConfig(
        rules=[_parse_combat_rule(r) for r in raw["combat"]["rules"]]
    )

    movement = MovementConfigDef(**raw["movement"])

    terrain_thresholds = TerrainThresholdsDef(**raw["terrain_thresholds"])

    ab_raw = raw["abilities"]
    buff_raw = ab_raw.get("activate_buff")
    activate_buff = None
    if buff_raw:
        activate_buff = ActivateBuffDef(
            modifiers=[StatModifierDef(**m) for m in buff_raw["modifiers"]],
            duration_ticks=buff_raw["duration_ticks"]
        )
    
    skills = None
    if "skills" in ab_raw:
        from src.config.definitions import SkillDef
        skills = [
            SkillDef(
                index=s["index"],
                name=s["name"],
                modifiers=[StatModifierDef(**m) for m in s["modifiers"]],
                duration_ticks=s["duration_ticks"],
                cooldown_ticks=s["cooldown_ticks"]
            )
            for s in ab_raw["skills"]
        ]

    abilities = AbilitiesDef(
        buff_cooldown_ticks=ab_raw.get("buff_cooldown_ticks", 0),
        movement_speed_stat=ab_raw.get("movement_speed_stat"),
        combat_damage_stat=ab_raw.get("combat_damage_stat"),
        activate_buff=activate_buff,
        zone_modifier_duration_ticks=ab_raw.get("zone_modifier_duration_ticks", 1500),
        skills=skills,
    )

    removal_rules = [RemovalRuleDef(**r) for r in raw.get("removal_rules", [])]

    actions = [ActionDef(**a) for a in raw["actions"]]

    training_raw = raw["training"]
    rewards = RewardWeights(**training_raw["rewards"])

    curriculum = []
    for s in training_raw["curriculum"]:
        grad_raw = s["graduation"]
        graduation = GraduationConfig(
            win_rate=grad_raw["win_rate"],
            min_episodes=grad_raw["min_episodes"],
            avg_survivors=grad_raw.get("avg_survivors"),
            action_usage=grad_raw.get("action_usage", {}),
            avg_flanking_score_min=grad_raw.get("avg_flanking_score_min"),
            timeout_rate_max=grad_raw.get("timeout_rate_max"),
        )

        demotion = None
        if s.get("demotion"):
            demotion = DemotionConfig(**s["demotion"])

        curriculum.append(CurriculumStageConfig(
            stage=s["stage"],
            description=s["description"],
            graduation=graduation,
            demotion=demotion,
        ))

    training = TrainingConfig(
        max_density=training_raw["max_density"],
        max_steps=training_raw["max_steps"],
        ai_eval_interval_ticks=training_raw["ai_eval_interval_ticks"],
        observation_channels=training_raw["observation_channels"],
        rewards=rewards,
        curriculum=curriculum,
    )

    bot_stage_behaviors = [
        BotStageBehaviorDef(
            stage=b["stage"],
            faction_id=b["faction_id"],
            strategy=_parse_strategy(b["strategy"]),
            eval_interval_ticks=b.get("eval_interval_ticks", 60),
        )
        for b in raw.get("bot_stage_behaviors", [])
    ]
    
    unit_registry = _parse_unit_registry(raw)

    return GameProfile(
        meta=meta,
        world=world,
        factions=factions,
        combat=combat,
        movement=movement,
        terrain_thresholds=terrain_thresholds,
        abilities=abilities,
        removal_rules=removal_rules,
        actions=actions,
        training=training,
        bot_stage_behaviors=bot_stage_behaviors,
        unit_registry=unit_registry,
    )
