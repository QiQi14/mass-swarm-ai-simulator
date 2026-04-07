//! # Navigation Rules
//!
//! Defines which factions navigate toward which factions via flow fields.
//!
//! ## Ownership
//! - **Task:** task_04_rule_resources
//! - **Contract:** implementation_plan.md → Contract 5

use crate::bridges::zmq_protocol::NavigationTarget;
use bevy::prelude::*;
use serde::{Deserialize, Serialize};

/// Config-driven navigation matrix. The flow_field_update_system reads this
/// to decide which flow fields to calculate and which factions use them.
#[derive(Resource, Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct NavigationRuleSet {
    pub rules: Vec<NavigationRule>,
}

/// A single navigation rule: follower_faction follows flow field toward target_faction.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct NavigationRule {
    /// Faction ID of entities that will follow the flow field.
    pub follower_faction: u32,
    /// Navigation target, replacing direct target_faction.
    pub target: NavigationTarget,
}

impl Default for NavigationRuleSet {
    /// Empty ruleset — no navigation unless explicitly configured by game profile.
    /// Consistent with InteractionRuleSet and RemovalRuleSet defaults.
    fn default() -> Self {
        Self { rules: vec![] }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_navigation_rule_set_default_is_empty() {
        // Arrange & Act
        let ruleset = NavigationRuleSet::default();

        // Assert — consistent with InteractionRuleSet and RemovalRuleSet
        assert_eq!(
            ruleset.rules.len(),
            0,
            "Default NavigationRuleSet should be empty"
        );
    }

    #[test]
    fn test_navigation_rule_set_serde_roundtrip() {
        let ruleset = NavigationRuleSet::default();
        let serialized = serde_json::to_string(&ruleset).unwrap();
        let deserialized: NavigationRuleSet = serde_json::from_str(&serialized).unwrap();
        assert_eq!(ruleset, deserialized);
    }
}
