//! # Engine Override Component
//!
//! Component for Tier 1 manual physics override.
//!
//! ## Ownership
//! - **Task:** task_02_phase3_resources
//! - **Contract:** implementation_plan.md → Shared Contracts
//!

use bevy::prelude::*;

/// Component for Tier 1 manual physics override.
#[derive(Component, Debug, Clone)]
pub struct EngineOverride {
    pub forced_velocity: Vec2,
    pub ticks_remaining: Option<u32>,
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_engine_override_default_no_ticks() {
        let override_comp = EngineOverride {
            forced_velocity: Vec2::new(1.0, 0.0),
            ticks_remaining: None,
        };
        assert!(override_comp.ticks_remaining.is_none());
        assert_eq!(override_comp.forced_velocity, Vec2::new(1.0, 0.0));
    }
}
