//! # StatBlock Component
//!
//! Anonymous stat array for entities.
//!
//! ## Ownership
//! - **Task:** task_01_context_agnostic_refactor
//! - **Contract:** implementation_plan.md → Contract 2: StatBlock Component
//!
//! ## Depends On
//! - None

use bevy::prelude::*;
use serde::{Deserialize, Serialize};

/// Maximum number of stats per entity. Compile-time constant.
pub const MAX_STATS: usize = 8;

/// Anonymous stat array. The Micro-Core never knows what each index means.
/// The Adapter layer defines the mapping (e.g., index 0 = "health", index 1 = "mana").
///
/// Default: all zeros. Initialize via `StatBlock::with_defaults(&[...])`.
#[derive(Component, Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct StatBlock(pub [f32; MAX_STATS]);

impl Default for StatBlock {
    fn default() -> Self {
        Self([0.0; MAX_STATS])
    }
}

impl StatBlock {
    /// Create a StatBlock with specified (index, value) pairs.
    /// Unspecified indices default to 0.0.
    pub fn with_defaults(pairs: &[(usize, f32)]) -> Self {
        let mut block = Self::default();
        for &(idx, val) in pairs {
            if idx < MAX_STATS {
                block.0[idx] = val;
            }
        }
        block
    }
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_stat_block_default_is_zeros() {
        // Arrange & Act
        let block = StatBlock::default();
        
        // Assert
        for &val in &block.0 {
            assert!((val - 0.0).abs() < f32::EPSILON, "Default stat should be 0.0");
        }
    }

    #[test]
    fn test_stat_block_with_defaults() {
        // Arrange & Act
        let block = StatBlock::with_defaults(&[(0, 1.0), (3, 5.5)]);
        
        // Assert
        assert!((block.0[0] - 1.0).abs() < f32::EPSILON);
        assert!((block.0[1] - 0.0).abs() < f32::EPSILON);
        assert!((block.0[3] - 5.5).abs() < f32::EPSILON);
    }
    
    #[test]
    fn test_stat_block_serde_roundtrip() {
        // Arrange
        let original = StatBlock::with_defaults(&[(0, 0.5)]);
        
        // Act
        let json = serde_json::to_string(&original).unwrap();
        let deserialized: StatBlock = serde_json::from_str(&json).unwrap();
        
        // Assert
        assert_eq!(original, deserialized, "StatBlock should survive JSON roundtrip");
    }
}
