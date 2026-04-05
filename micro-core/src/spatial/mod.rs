//! # Spatial Partitioning
//!
//! Hash grid for O(1) amortized proximity lookups.
//!
//! ## Ownership
//! - **Task:** task_02_spatial_hash_grid
//! - **Contract:** implementation_plan.md -> Contract 3

pub mod hash_grid;

pub use hash_grid::{SpatialHashGrid, update_spatial_grid_system};
