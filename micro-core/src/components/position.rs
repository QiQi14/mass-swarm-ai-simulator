//! # Position Component
//!
//! 2D position in world space.
//! Origin is top-left (0,0), positive Y goes down.
//!
//! ## Ownership
//! - **Task:** task_02_ecs_components
//! - **Contract:** implementation_plan.md → Component 2: ECS Components → position.rs
//!
//! ## Depends On
//! - `bevy::prelude::Component`
//! - `serde::{Serialize, Deserialize}`

use bevy::prelude::*;
use serde::{Deserialize, Serialize};

/// 2D position in world space.
/// Origin is top-left (0,0), positive Y goes down.
#[derive(Component, Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Position {
    /// Horizontal coordinate in world units.
    pub x: f32,
    /// Vertical coordinate in world units.
    pub y: f32,
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_position_serialization_roundtrip() {
        // Arrange
        let original = Position { x: 1.5, y: 2.5 };

        // Act
        let json = serde_json::to_string(&original).unwrap();
        let deserialized: Position = serde_json::from_str(&json).unwrap();

        // Assert
        assert!((original.x - deserialized.x).abs() < f32::EPSILON, "x should match after roundtrip, got {}", deserialized.x);
        assert!((original.y - deserialized.y).abs() < f32::EPSILON, "y should match after roundtrip, got {}", deserialized.y);
        assert_eq!(original, deserialized, "Position should be equal after JSON roundtrip");
    }
}
