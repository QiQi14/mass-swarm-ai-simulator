//! # Velocity Component
//!
//! Per-tick velocity vector applied by the movement system.
//!
//! ## Ownership
//! - **Task:** task_02_ecs_components
//! - **Contract:** implementation_plan.md → Component 2: ECS Components → velocity.rs
//!
//! ## Depends On
//! - `bevy::prelude::Component`
//! - `serde::{Serialize, Deserialize}`

use bevy::prelude::*;
use serde::{Deserialize, Serialize};

/// Per-tick velocity vector applied by the movement system.
#[derive(Component, Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Velocity {
    /// Change in horizontal position per tick.
    pub dx: f32,
    /// Change in vertical position per tick.
    pub dy: f32,
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_velocity_serialization_roundtrip() {
        // Arrange
        let original = Velocity { dx: -0.5, dy: 1.0 };

        // Act
        let json = serde_json::to_string(&original).unwrap();
        let deserialized: Velocity = serde_json::from_str(&json).unwrap();

        // Assert
        assert!(
            (original.dx - deserialized.dx).abs() < f32::EPSILON,
            "dx should match after roundtrip, got {}",
            deserialized.dx
        );
        assert!(
            (original.dy - deserialized.dy).abs() < f32::EPSILON,
            "dy should match after roundtrip, got {}",
            deserialized.dy
        );
        assert_eq!(
            original, deserialized,
            "Velocity should be equal after JSON roundtrip"
        );
    }
}
