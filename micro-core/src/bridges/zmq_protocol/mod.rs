//! # ZMQ Protocol Types
//!
//! Defines all data contracts for the ZMQ bridge between micro-core and macro-brain.
//! Split into: state types, directive/action enums, and config payloads.

mod directives;
mod payloads;
mod types;

pub use directives::*;
pub use payloads::*;
pub use types::*;
