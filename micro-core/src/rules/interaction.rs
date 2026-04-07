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
}
