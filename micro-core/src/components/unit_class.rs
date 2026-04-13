//! # UnitClassId Component
//!
//! Context-agnostic unit class identifier.
//! The Micro-Core never knows what class 0 or class 1 means.
//! The game profile defines the mapping (e.g., class 0 = "Infantry", class 1 = "Sniper").
//!
//! ## Ownership
//! - **Task:** task_01_unit_class_component
//! - **Contract:** implementation_plan.md → Contract C1
//!
//! ## Depends On
//! - None

use bevy::prelude::*;
use serde::{Deserialize, Serialize};

/// Context-agnostic unit class identifier. Default: 0 (generic).
///
/// Used by `InteractionRule` to apply class-specific combat rules.
/// When `UnitClassId` is absent or 0, all rules with `source_class: None`
/// and `target_class: None` apply (backward compatible).
#[derive(Component, Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct UnitClassId(pub u32);

impl Default for UnitClassId {
    fn default() -> Self {
        Self(0)
    }
}

impl std::fmt::Display for UnitClassId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "class_{}", self.0)
    }
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_unit_class_id_default() {
        // Arrange & Act
        let default_id = UnitClassId::default();

        // Assert
        assert_eq!(default_id.0, 0, "Default UnitClassId should be 0");
    }

    #[test]
    fn test_unit_class_id_display() {
        // Arrange
        let id = UnitClassId(5);

        // Act
        let display = id.to_string();

        // Assert
        assert_eq!(display, "class_5", "UnitClassId(5) should display as 'class_5'");
    }

    #[test]
    fn test_unit_class_id_serde_roundtrip() {
        // Arrange
        let original = UnitClassId(42);

        // Act
        let json = serde_json::to_string(&original).expect("Should serialize to JSON");
        let deserialized: UnitClassId = serde_json::from_str(&json).expect("Should deserialize from JSON");

        // Assert
        assert_eq!(original, deserialized, "UnitClassId should survive JSON roundtrip");
        assert_eq!(json, "42", "UnitClassId should serialize as a simple integer");
    }
}
