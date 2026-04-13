//! # Movement Configuration Component
//!
//! Per-entity movement tuning: speed, steering, separation.
//!
//! ## Ownership
//! - **Task:** task_06_flow_field_movement_spawning
//! - **Contract:** implementation_plan.md → Contract 7

use bevy::prelude::*;

/// Per-entity movement configuration. Entities with this component
/// participate in flow-field navigation and Boids separation.
/// Entities WITHOUT this component retain Phase 1 behavior (random drift).
#[derive(Component, Debug, Clone, Copy)]
pub struct MovementConfig {
    /// Maximum speed in world units per second.
    pub max_speed: f32,
    /// Lerp factor for velocity steering (higher = snappier turns).
    pub steering_factor: f32,
    /// Personal space bubble radius for Boids separation (world units).
    pub separation_radius: f32,
    /// Strength multiplier for separation push-back.
    pub separation_weight: f32,
    /// Strength multiplier for flow field pull.
    pub flow_weight: f32,
}

impl Default for MovementConfig {
    /// Zero movement — entities don't move unless configured by game profile.
    fn default() -> Self {
        Self {
            max_speed: 0.0,
            steering_factor: 0.0,
            separation_radius: 0.0,
            separation_weight: 0.0,
            flow_weight: 0.0,
        }
    }
}
