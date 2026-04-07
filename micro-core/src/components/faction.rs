//! # Faction Component
//!
//! Numeric faction identifier. Context-agnostic.
//!
//! ## Ownership
//! - **Task:** task_01_context_agnostic_refactor
//! - **Contract:** implementation_plan.md → Contract 1: FactionId Component
//!
//! ## Depends On
//! - None

use bevy::prelude::*;
use serde::{Deserialize, Serialize};

/// Numeric faction identifier. Context-agnostic — the adapter maps ID to meaning.
/// Example: 0 = "swarm", 1 = "defender" (in the swarm demo adapter config).
#[derive(Component, Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct FactionId(pub u32);

impl std::fmt::Display for FactionId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "faction_{}", self.0)
    }
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_faction_id_display() {
        // Arrange & Act
        let f = FactionId(0);
        // Assert
        assert_eq!(f.to_string(), "faction_0");
    }

    #[test]
    fn test_faction_id_serde_roundtrip() {
        // Arrange
        let original = FactionId(1);

        // Act
        let json = serde_json::to_string(&original).unwrap();
        let deserialized: FactionId = serde_json::from_str(&json).unwrap();

        // Assert
        assert_eq!(
            original, deserialized,
            "FactionId should survive JSON roundtrip"
        );
    }
}
