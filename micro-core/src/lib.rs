//! # Micro-Core Library Root
//!
//! Re-exports modules for the cdylib and rlib targets.
//!
//! ## Ownership
//! - **Task:** task_01_project_scaffold
//! - **Contract:** implementation_plan.md
//!
//! ## Depends On
//! - `crate::bridges`
//! - `crate::components`
//! - `crate::config`
//! - `crate::systems`

pub mod bridges;
pub mod components;
pub mod config;
pub mod systems;
