//! # Configuration Resources
//!
//! Bevy ECS resources for simulation configuration, buff system, and zone modifiers.
//! All resources are injected at startup or via ZMQ ResetEnvironment.

mod buff;
mod cooldown;
mod simulation;
mod zones;

pub use buff::*;
pub use cooldown::*;
pub use simulation::*;
pub use zones::*;
