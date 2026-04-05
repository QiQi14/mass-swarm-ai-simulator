//! # ECS Components
//!
//! Barrel file for re-exporting all ECS components.
//!
//! ## Ownership
//! - **Task:** task_02_ecs_components
//! - **Contract:** implementation_plan.md → Component 2: ECS Components → mod.rs
//!
//! ## Depends On
//! - `crate::components::entity_id`
//! - `crate::components::faction`
//! - `crate::components::position`
//! - `crate::components::stat_block`
//! - `crate::components::velocity`

pub mod entity_id;
pub mod faction;
pub mod position;
pub mod movement_config;
pub mod stat_block;
pub mod velocity;
pub mod vision_radius;

pub use entity_id::{EntityId, NextEntityId};
pub use faction::FactionId;
pub use movement_config::MovementConfig;
pub use position::Position;
pub use stat_block::{StatBlock, MAX_STATS};
pub use velocity::Velocity;
pub use vision_radius::VisionRadius;
