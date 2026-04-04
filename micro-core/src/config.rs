//! # Simulation Config
//!
//! Global configuration and generic resources for the simulation framework.
//!
//! ## Ownership
//! - **Task:** task_03_systems_config
//! - **Contract:** implementation_plan.md → Shared Contracts → Resources
//!

use bevy::prelude::*;
use serde::{Deserialize, Serialize};

/// Global simulation configuration. Inserted as a Bevy Resource at app startup.
#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct SimulationConfig {
    /// Width of the playable world in units
    pub world_width: f32,
    /// Height of the playable world in units
    pub world_height: f32,
    /// Initial number of entities to spawn
    pub initial_entity_count: u32,
}

impl Default for SimulationConfig {
    fn default() -> Self {
        Self {
            world_width: 1000.0,
            world_height: 1000.0,
            initial_entity_count: 100,
        }
    }
}

/// Monotonically increasing tick counter. Incremented once per ECS tick.
#[derive(Resource, Debug, Default)]
pub struct TickCounter {
    /// The current tick number
    pub tick: u64,
}

/// User-controlled simulation pause (from Debug Visualizer).
/// Independent of `SimState::WaitingForAI`.
#[derive(Resource, Debug, Clone, PartialEq)]
pub struct SimPaused(pub bool);

impl Default for SimPaused {
    fn default() -> Self { Self(false) }
}

/// Speed multiplier for entity movement.
#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct SimSpeed {
    pub multiplier: f32,
}

impl Default for SimSpeed {
    fn default() -> Self { Self { multiplier: 1.0 } }
}

/// Step mode: when > 0, movement runs for this many ticks even if paused,
/// then auto-pauses when it reaches 0. Used for single-step debugging.
#[derive(Resource, Debug, Clone, Default)]
pub struct SimStepRemaining(pub u32);

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        // Arrange
        let config = SimulationConfig::default();
        
        // Assert
        assert!((config.world_width - 1000.0).abs() < f32::EPSILON, "world_width should be exactly 1000.0");
        assert!((config.world_height - 1000.0).abs() < f32::EPSILON, "world_height should be exactly 1000.0");
        assert_eq!(config.initial_entity_count, 100, "initial_entity_count should be exactly 100");
    }

    #[test]
    fn test_tick_counter_default() {
        // Arrange
        let counter = TickCounter::default();
        
        // Assert
        assert_eq!(counter.tick, 0, "Counter should start at 0");
    }

    #[test]
    fn test_sim_paused_default() {
        assert_eq!(SimPaused::default().0, false, "SimPaused default should be false");
    }

    #[test]
    fn test_sim_speed_default() {
        assert!((SimSpeed::default().multiplier - 1.0).abs() < f32::EPSILON, "SimSpeed multiplier default should be 1.0");
    }

    #[test]
    fn test_sim_step_remaining_default() {
        assert_eq!(SimStepRemaining::default().0, 0, "SimStepRemaining default should be 0");
    }
}
