//! # Removal Rules
//!
//! Defines when entities are removed from simulation based on stat thresholds.
//!
//! ## Ownership
//! - **Task:** task_04_rule_resources
//! - **Contract:** implementation_plan.md → Contract 5

use bevy::prelude::*;
use serde::{Deserialize, Serialize};

/// Config-driven removal rules. Checked each tick by the removal system.
#[derive(Resource, Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RemovalRuleSet {
    pub rules: Vec<RemovalRule>,
}

/// A single removal rule: remove entity when stat[index] crosses threshold.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RemovalRule {
    /// Which stat index to monitor.
    pub stat_index: usize,
    /// Threshold value for removal.
    pub threshold: f32,
    /// Direction of comparison.
    pub condition: RemovalCondition,
}

/// Direction of threshold comparison for removal.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum RemovalCondition {
    /// Remove when stat <= threshold (e.g., "health" drops to 0).
    LessOrEqual,
    /// Remove when stat >= threshold (e.g., "corruption" reaches 100).
    GreaterOrEqual,
}

impl Default for RemovalRuleSet {
    /// Empty ruleset — no entity removal unless configured by game profile.
    fn default() -> Self {
        Self { rules: vec![] }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_removal_rule_set_default() {
        let ruleset = RemovalRuleSet::default();
        assert_eq!(ruleset.rules.len(), 0);
    }

    #[test]
    fn test_removal_rule_explicit_construction() {
        let ruleset = RemovalRuleSet {
            rules: vec![RemovalRule {
                stat_index: 1,
                threshold: 50.0,
                condition: RemovalCondition::GreaterOrEqual,
            }],
        };
        assert_eq!(ruleset.rules.len(), 1);
        assert_eq!(ruleset.rules[0].stat_index, 1);
        assert_eq!(ruleset.rules[0].condition, RemovalCondition::GreaterOrEqual);
    }

    #[test]
    fn test_removal_condition_variants() {
        assert_ne!(
            RemovalCondition::LessOrEqual,
            RemovalCondition::GreaterOrEqual
        );
    }

    #[test]
    fn test_removal_rule_set_serde_roundtrip() {
        let ruleset = RemovalRuleSet::default();
        let serialized = serde_json::to_string(&ruleset).unwrap();
        let deserialized: RemovalRuleSet = serde_json::from_str(&serialized).unwrap();
        assert_eq!(ruleset, deserialized);
    }
}
