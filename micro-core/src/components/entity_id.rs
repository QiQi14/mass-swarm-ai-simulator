//! # Entity IDs
//!
//! Monotonic entity identification system.
//!
//! ## Ownership
//! - **Task:** task_02_ecs_components
//! - **Contract:** implementation_plan.md → Component 2: ECS Components → entity_id.rs
//!
//! ## Depends On
//! - `bevy::prelude::Component`
//! - `bevy::prelude::Resource`
//! - `serde::{Serialize, Deserialize}`

use bevy::prelude::*;
use serde::{Deserialize, Serialize};

/// Globally unique entity identifier within a simulation session.
/// Monotonically assigned via the `NextEntityId` resource.
#[derive(Component, Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct EntityId {
    /// The unique integer ID.
    pub id: u32,
}

/// Resource tracking the next available entity ID.
/// Incremented each time a new simulation entity is spawned.
#[derive(Resource, Debug)]
pub struct NextEntityId(pub u32);

impl Default for NextEntityId {
    fn default() -> Self {
        Self(1) // IDs start at 1, 0 is reserved for "no entity" sentinel
    }
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_next_entity_id_default_starts_at_one() {
        // Arrange & Act
        let next_id = NextEntityId::default();

        // Assert
        assert_eq!(next_id.0, 1, "NextEntityId default should be 1");
    }

    #[test]
    fn test_entity_id_serialization_roundtrip() {
        // Arrange
        let original = EntityId { id: 42 };

        // Act
        let json = serde_json::to_string(&original).unwrap();
        let deserialized: EntityId = serde_json::from_str(&json).unwrap();

        // Assert
        assert_eq!(
            original, deserialized,
            "EntityId should be equal after JSON roundtrip"
        );
    }
}
