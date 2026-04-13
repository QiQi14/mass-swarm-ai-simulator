//! # Tactical Components
//!
//! ECS components for the Boids 2.0 tactical steering system.
//! These hold per-entity runtime state from the 10 Hz tactical sensor.
//!
//! ## Ownership
//! - **Task:** T03 — ECS Components + Registry (Boids 2.0)
//! - **Contract:** implementation_plan.md → T03
//!
//! ## Depends On
//! - `bevy::prelude::*`

use bevy::prelude::*;

/// Per-entity tactical steering state, updated at 10 Hz by the tactical sensor.
///
/// Stores the subsumption winner: the highest-priority tactical behavior's
/// vector and weight. This value is blended with V_flow and V_sep in the
/// movement system every tick (60 Hz).
///
/// ## Default
/// Zero vector + zero weight = no tactical override (pure flow follower).
#[derive(Component, Debug, Clone, Default)]
pub struct TacticalState {
    /// Tactical steering direction (normalized or zero).
    pub direction: Vec2,
    /// Weight for the blending formula. 0.0 = no tactical influence.
    pub weight: f32,
    /// Engagement range from UnitTypeRegistry. Cached here for O(1) access
    /// in the movement system. 0.0 = charge to melee (default).
    pub engagement_range: f32,
}

/// Per-entity combat tracking, stamped by the interaction system.
///
/// Used by the tactical sensor to detect "recently damaged" allies
/// for PeelForAlly behavior (the sensor checks if
/// `current_tick - last_damaged_tick < threshold`).
///
/// ## Default
/// `last_damaged_tick = 0` means never damaged.
#[derive(Component, Debug, Clone, Default)]
pub struct CombatState {
    /// Tick when this entity last took damage. 0 = never.
    pub last_damaged_tick: u64,
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tactical_state_default_is_neutral() {
        // Arrange
        let ts = TacticalState::default();

        // Assert
        assert_eq!(ts.direction, Vec2::ZERO, "Default direction should be zero");
        assert!((ts.weight - 0.0).abs() < f32::EPSILON, "Default weight should be 0.0");
        assert!((ts.engagement_range - 0.0).abs() < f32::EPSILON, "Default engagement_range should be 0.0");
    }

    #[test]
    fn test_combat_state_default_never_damaged() {
        // Arrange
        let cs = CombatState::default();

        // Assert
        assert_eq!(cs.last_damaged_tick, 0, "Default last_damaged_tick should be 0");
    }
}
