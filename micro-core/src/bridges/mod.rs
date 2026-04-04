//! # Bridges Module
//!
//! Exposes external communication bridges (WebSocket, ZeroMQ).
//!
//! ## Ownership
//! - **Task:** task_06_zmq_protocol_cargo
//! - **Contract:** implementation_plan.md → Phase 1 — Micro-Phase 3: ZeroMQ Bridge + Stub AI Round-Trip
//!
//! ## Depends On
//! - `ws_protocol`
//! - `ws_server`
//! - `zmq_protocol`
//! - `zmq_bridge`

pub mod ws_protocol;
pub mod ws_server;
pub mod zmq_protocol;
pub mod zmq_bridge;
