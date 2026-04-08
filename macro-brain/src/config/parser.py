"""Game profile parser — converts raw JSON dicts to typed GameProfile.

Extracted from game_profile.py to meet the 200-line file size convention.
"""

from __future__ import annotations

from typing import Any

from src.config.definitions import (
    WorldConfig, FactionStats, FactionConfig, StatEffectConfig,
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
        return BotStrategyDef(
            type=raw_strat["type"],
            target_faction=raw_strat.get("target_faction"),
            x=raw_strat.get("x"),
            y=raw_strat.get("y"),
            retreat_health_fraction=raw_strat.get("retreat_health_fraction"),
            retreat_x=raw_strat.get("retreat_x"),
            retreat_y=raw_strat.get("retreat_y"),
            strategies=[_parse_strategy(s) for s in strats] if strats else None
        )

    meta = ProfileMeta(**raw["meta"])

    world = WorldConfig(**raw["world"])

    factions = [
        FactionConfig(
            id=f["id"],
            name=f["name"],
            role=f["role"],
            stats=FactionStats(**f["stats"]),
            default_count=f["default_count"],
        )
        for f in raw["factions"]
    ]

    combat = CombatConfig(
        rules=[
            CombatRuleConfig(
                source_faction=r["source_faction"],
                target_faction=r["target_faction"],
                range=r["range"],
                effects=[StatEffectConfig(**e) for e in r["effects"]],
            )
            for r in raw["combat"]["rules"]
        ]
    )

    movement = MovementConfigDef(**raw["movement"])

    terrain_thresholds = TerrainThresholdsDef(**raw["terrain_thresholds"])

    ab_raw = raw["abilities"]
    buff_raw = ab_raw["activate_buff"]
    abilities = AbilitiesDef(
        buff_cooldown_ticks=ab_raw["buff_cooldown_ticks"],
        movement_speed_stat=ab_raw.get("movement_speed_stat"),
        combat_damage_stat=ab_raw.get("combat_damage_stat"),
        activate_buff=ActivateBuffDef(
            modifiers=[StatModifierDef(**m) for m in buff_raw["modifiers"]],
            duration_ticks=buff_raw["duration_ticks"]
        )
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
    )
