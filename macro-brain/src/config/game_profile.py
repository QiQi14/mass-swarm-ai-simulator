"""Game Profile — typed configuration contract for the training pipeline.

The profile replaces ALL hardcoded game parameters. To train a different
game scenario, create a new JSON file — no source code changes needed.

Usage:
    from src.config.game_profile import load_profile
    profile = load_profile("profiles/default_swarm_combat.json")
    env = SwarmEnv(profile=profile)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from src.config.definitions import (
    WorldConfig, FactionStats, FactionConfig, StatEffectConfig,
    CombatRuleConfig, CombatConfig, MovementConfigDef, TerrainThresholdsDef,
    StatModifierDef, ActivateBuffDef, AbilitiesDef, RemovalRuleDef,
    ActionDef, RewardWeights, GraduationConfig, DemotionConfig,
    CurriculumStageConfig, TrainingConfig, ProfileMeta
)

@dataclass(frozen=True)
class GameProfile:
    """The complete game configuration contract.

    Every module in the training pipeline receives this object.
    No module should define its own constants — everything comes from here.
    """
    meta: ProfileMeta
    world: WorldConfig
    factions: list[FactionConfig]
    combat: CombatConfig
    movement: MovementConfigDef
    terrain_thresholds: TerrainThresholdsDef
    abilities: AbilitiesDef
    removal_rules: list[RemovalRuleDef]
    actions: list[ActionDef]
    training: TrainingConfig

    # ── Derived helpers ─────────────────────────────────────

    @property
    def brain_faction(self) -> FactionConfig:
        """The faction controlled by the RL agent."""
        return next(f for f in self.factions if f.role == "brain")

    @property
    def bot_factions(self) -> list[FactionConfig]:
        """All factions controlled by scripted bots."""
        return [f for f in self.factions if f.role == "bot"]

    @property
    def num_actions(self) -> int:
        return len(self.actions)

    def actions_unlocked_at(self, stage: int) -> list[ActionDef]:
        """Actions available at a given curriculum stage."""
        return [a for a in self.actions if a.unlock_stage <= stage]

    def get_stage_config(self, stage: int) -> CurriculumStageConfig | None:
        """Lookup curriculum config by stage number."""
        return next(
            (s for s in self.training.curriculum if s.stage == stage),
            None
        )

    def combat_rules_payload(self) -> list[dict]:
        """Serialize combat rules for ZMQ ResetEnvironment payload."""
        return [
            {
                "source_faction": r.source_faction,
                "target_faction": r.target_faction,
                "range": r.range,
                "effects": [
                    {"stat_index": e.stat_index, "delta_per_second": e.delta_per_second}
                    for e in r.effects
                ],
            }
            for r in self.combat.rules
        ]

    def ability_config_payload(self) -> dict:
        """Serialize ability config for ZMQ ResetEnvironment payload."""
        return {
            "buff_cooldown_ticks": self.abilities.buff_cooldown_ticks,
            "movement_speed_stat": self.abilities.movement_speed_stat,
            "combat_damage_stat": self.abilities.combat_damage_stat,
        }

    def movement_config_payload(self) -> dict:
        return asdict(self.movement)

    def terrain_thresholds_payload(self) -> dict:
        return asdict(self.terrain_thresholds)

    def removal_rules_payload(self) -> list:
        return [asdict(r) for r in self.removal_rules]

    def navigation_rules_payload(self) -> list[dict]:
        """Serialize navigation rules for ZMQ ResetEnvironment payload.
        
        Generates bidirectional navigation: brain faction chases bot factions
        and each bot faction chases the brain faction. Uses faction IDs from
        the profile — no hardcoded values.
        """
        rules = []
        brain = self.brain_faction
        for bot in self.bot_factions:
            # Brain faction navigates toward bot
            rules.append({
                "follower_faction": brain.id,
                "target": {"type": "Faction", "faction_id": bot.id}
            })
            # Bot faction navigates toward brain
            rules.append({
                "follower_faction": bot.id,
                "target": {"type": "Faction", "faction_id": brain.id}
            })
        return rules


# ── Loader ──────────────────────────────────────────────────────────

def load_profile(path: str | Path) -> GameProfile:
    """Load and validate a game profile from a JSON file.

    Raises:
        FileNotFoundError: If the profile file doesn't exist.
        KeyError: If a required field is missing.
        ValueError: If a field has an invalid value.
    """
    from src.config.parser import _parse_profile

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Game profile not found: {path}")

    with open(path) as f:
        raw = json.load(f)

    return _parse_profile(raw)

