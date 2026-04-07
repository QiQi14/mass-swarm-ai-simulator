//! # Configuration Resources
//!
//! Bevy ECS resources for simulation configuration, buff system, and zone modifiers.
//! All resources are injected at startup or via ZMQ ResetEnvironment.

mod buff;
mod simulation;
mod zones;

pub use buff::*;
pub use simulation::*;
pub use zones::*;
