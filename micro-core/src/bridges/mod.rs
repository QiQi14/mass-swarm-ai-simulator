//! # Bridges Module
//!
//! Exposes external communication bridges (WebSocket, ZeroMQ).
//! Native-only bridges are gated behind `#[cfg(feature = "native")]`.
//!
//! ## Ownership
//! - **Task:** task_06_zmq_protocol_cargo
//! - **Contract:** implementation_plan.md → Phase 1 — Micro-Phase 3: ZeroMQ Bridge + Stub AI Round-Trip
//!
//! ## Depends On
//! - `ws_protocol` (shared data types, always available)
//! - `ws_server` (native-only: tokio WebSocket listener)
//! - `zmq_protocol` (shared data types, always available)
//! - `zmq_bridge` (native-only: ZMQ AI bridge + tokio runtime)

pub mod ws_protocol;
pub mod zmq_protocol;

#[cfg(feature = "native")]
pub mod ws_server;

#[cfg(feature = "native")]
pub mod zmq_bridge;
