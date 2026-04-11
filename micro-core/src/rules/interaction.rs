//! # Interaction Rules
//!
//! Defines what happens when entities of different factions are in proximity.
//! Loaded from config — zero hardcoded game logic.
//!
//! ## Ownership
//! - **Task:** task_04_rule_resources
//! - **Contract:** implementation_plan.md → Contract 5

use bevy::prelude::*;
use serde::{Deserialize, Serialize};

/// Config-driven interaction rules. Each rule defines source→target faction
/// proximity effects on the target's StatBlock.
#[derive(Resource, Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct InteractionRuleSet {
    pub rules: Vec<InteractionRule>,
}

/// A single interaction rule: when source_faction entity is within range
/// of target_faction entity, apply effects to target's StatBlock.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct InteractionRule {
    /// Faction ID of the entity causing the interaction.
    pub source_faction: u32,
    /// Faction ID of the entity receiving the effects.
    pub target_faction: u32,
    /// Range in world units at which this interaction activates.
    pub range: f32,
    /// Effects to apply to the TARGET entity's StatBlock.
    pub effects: Vec<StatEffect>,

    /// Filter: only apply this rule when the SOURCE entity has this class.
    /// None = any class (backward compatible default).
    #[serde(default)]
    pub source_class: Option<u32>,

    /// Filter: only apply this rule when the TARGET entity has this class.
    /// None = any class (backward compatible default).
    #[serde(default)]
    pub target_class: Option<u32>,

    /// If set, use the SOURCE entity's StatBlock[idx] as the combat range
    /// instead of the fixed `range` field. Falls back to `range` if stat is missing.
    #[serde(default)]
    pub range_stat_index: Option<usize>,

    /// Optional stat-driven damage mitigation on the TARGET.
    #[serde(default)]
    pub mitigation: Option<MitigationRule>,

    /// If set, each source entity can only fire this rule every N ticks.
    /// Tracked by `CooldownTracker` resource.
    #[serde(default)]
    pub cooldown_ticks: Option<u32>,
}

/// A single stat modification. Applied to target entity per tick.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct StatEffect {
    /// Index into the target's StatBlock array.
    pub stat_index: usize,
    /// Change per second. Negative = damage, positive = heal/buff.
    /// Normalized to per-tick by the interaction system: `delta * (1.0/60.0)`.
    pub delta_per_second: f32,
}

/// Stat-driven damage mitigation applied to the TARGET entity.
/// The engine doesn't know what "armor" or "shield" means — it just math.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct MitigationRule {
    /// Stat index on the TARGET entity providing mitigation value.
    pub stat_index: usize,
    /// How mitigation is applied to damage.
    pub mode: MitigationMode,
}

/// How damage mitigation math is computed.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum MitigationMode {
    /// damage = base_damage * (1.0 - target_stat.clamp(0.0, 1.0))
    /// Example: stat=0.3 → 30% damage reduction
    PercentReduction,
    /// damage = (base_damage.abs() - target_stat).max(0.0) * base_damage.signum()
    /// Example: stat=10.0 → 10 flat damage absorbed
    FlatReduction,
}

/// Accumulates entity IDs removed this tick for WebSocket broadcast.
/// Cleared at the start of each tick by the removal system.
#[derive(Resource, Debug, Default, PartialEq)]
pub struct RemovalEvents {
    pub removed_ids: Vec<u32>,
}

impl Default for InteractionRuleSet {
    /// Empty ruleset — no combat unless explicitly configured by game profile.
    fn default() -> Self {
        Self { rules: vec![] }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_interaction_rule_set_default() {
        let ruleset = InteractionRuleSet::default();
        assert_eq!(ruleset.rules.len(), 0);
    }

    #[test]
    fn test_interaction_rule_set_explicit_construction() {
        let ruleset = InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0,
                target_faction: 1,
                range: 10.0,
                effects: vec![],
                source_class: None,
                target_class: None,
                range_stat_index: None,
                mitigation: None,
                cooldown_ticks: None,
            }],
        };
        assert_eq!(ruleset.rules.len(), 1);
        assert_eq!(ruleset.rules[0].source_faction, 0);
        assert_eq!(ruleset.rules[0].target_faction, 1);
    }

    #[test]
    fn test_interaction_rule_set_serde_roundtrip() {
        let ruleset = InteractionRuleSet::default();
        let serialized = serde_json::to_string(&ruleset).unwrap();
        let deserialized: InteractionRuleSet = serde_json::from_str(&serialized).unwrap();
        assert_eq!(ruleset, deserialized);
    }

    #[test]
    fn test_removal_events_default() {
        let events = RemovalEvents::default();
        assert!(events.removed_ids.is_empty());
    }

    #[test]
    fn test_mitigation_rule_serde_roundtrip() {
        let rules = vec![
            MitigationRule {
                stat_index: 2,
                mode: MitigationMode::PercentReduction,
            },
            MitigationRule {
                stat_index: 3,
                mode: MitigationMode::FlatReduction,
            },
        ];
        
        let serialized = serde_json::to_string(&rules).unwrap();
        let deserialized: Vec<MitigationRule> = serde_json::from_str(&serialized).unwrap();
        assert_eq!(rules, deserialized);
    }

    #[test]
    fn test_interaction_rule_backward_compat() {
        let legacy_json = r#"{
            "source_faction": 0,
            "target_faction": 1,
            "range": 10.0,
            "effects": []
        }"#;
        
        let deserialized: InteractionRule = serde_json::from_str(legacy_json).unwrap();
        assert_eq!(deserialized.source_class, None);
        assert_eq!(deserialized.target_class, None);
        assert_eq!(deserialized.range_stat_index, None);
        assert_eq!(deserialized.mitigation, None);
        assert_eq!(deserialized.cooldown_ticks, None);
    }
}
