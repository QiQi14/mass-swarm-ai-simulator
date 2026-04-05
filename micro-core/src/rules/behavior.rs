//! # Faction Behavior Mode
//!
//! Runtime-toggleable per-faction behavior: static (random drift) vs brain-driven.
//!
//! ## Ownership
//! - **Task:** task_04_rule_resources
//! - **Contract:** implementation_plan.md → Contract 10

use bevy::prelude::*;
use std::collections::HashSet;

/// Controls per-faction behavior mode at runtime.
/// Factions in `static_factions` use random drift (Phase 1 behavior).
/// All other factions follow NavigationRuleSet flow fields (brain-driven).
///
/// Toggleable via Debug Visualizer: `set_faction_mode` WS command.
#[derive(Resource, Debug, Clone)]
pub struct FactionBehaviorMode {
    /// Set of faction IDs currently in "static" mode (random drift).
    /// Factions NOT in this set follow flow fields.
    pub static_factions: HashSet<u32>,
}

impl Default for FactionBehaviorMode {
    /// Swarm demo default: faction 1 (defenders) starts in static mode.
    fn default() -> Self {
        let mut static_factions = HashSet::new();
        static_factions.insert(1);
        Self { static_factions }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_faction_behavior_mode_default() {
        let mode = FactionBehaviorMode::default();
        assert!(mode.static_factions.contains(&1));
        assert!(!mode.static_factions.contains(&0));
    }
}
