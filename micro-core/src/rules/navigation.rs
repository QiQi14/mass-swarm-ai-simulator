//! # Navigation Rules
//!
//! Defines which factions navigate toward which factions via flow fields.
//!
//! ## Ownership
//! - **Task:** task_04_rule_resources
//! - **Contract:** implementation_plan.md → Contract 5

use bevy::prelude::*;
use serde::{Deserialize, Serialize};
use crate::bridges::zmq_protocol::NavigationTarget;

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
    /// Swarm demo default: faction 0 navigates toward faction 1.
    fn default() -> Self {
        Self {
            rules: vec![NavigationRule {
                follower_faction: 0,
                target: NavigationTarget::Faction { faction_id: 1 },
            }],
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_navigation_rule_set_default() {
        let ruleset = NavigationRuleSet::default();
        assert_eq!(ruleset.rules.len(), 1);
        assert_eq!(ruleset.rules[0].follower_faction, 0);
        assert_eq!(ruleset.rules[0].target, NavigationTarget::Faction { faction_id: 1 });
    }

    #[test]
    fn test_navigation_rule_set_serde_roundtrip() {
        let ruleset = NavigationRuleSet::default();
        let serialized = serde_json::to_string(&ruleset).unwrap();
        let deserialized: NavigationRuleSet = serde_json::from_str(&serialized).unwrap();
        assert_eq!(ruleset, deserialized);
    }
}
