//! # Pathfinding
//!
//! Dijkstra-based Vector Flow Fields for N-faction mass pathfinding.
//!
//! ## Ownership
//! - **Task:** task_03_flow_field_registry
//! - **Contract:** implementation_plan.md → Contract 4

pub mod flow_field;

pub use flow_field::{FlowField, FlowFieldRegistry};
