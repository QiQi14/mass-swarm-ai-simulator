//! # Micro-Core Library Root
//!
//! Re-exports modules for the cdylib and rlib targets.
//! The `wasm` feature enables the browser-callable WASM API.
//! The `native` feature enables WebSocket/ZMQ bridges (default).
//!
//! ## Ownership
//! - **Task:** task_01_project_scaffold
//! - **Contract:** implementation_plan.md
//!
//! ## Depends On
//! - `crate::bridges`
//! - `crate::components`
//! - `crate::config`
//! - `crate::pathfinding`
//! - `crate::spatial`
//! - `crate::systems`

pub mod bridges;
pub mod components;
pub mod config;
pub mod pathfinding;
pub mod plugins;
pub mod rules;
pub mod spatial;
pub mod systems;
pub mod terrain;
pub mod visibility;

#[cfg(feature = "wasm")]
pub mod wasm_api;
