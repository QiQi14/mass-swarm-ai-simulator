//! # Rule Resources
//!
//! Config-driven rule sets for interactions, removals, navigation, and behavior.
//! These are DATA ONLY — no systems.
//!
//! ## Ownership
//! - **Task:** task_04_rule_resources
//! - **Contract:** implementation_plan.md → Contracts 5, 6, 10

pub mod interaction;
pub mod removal;
pub mod navigation;
pub mod behavior;

pub use interaction::{InteractionRuleSet, InteractionRule, StatEffect, RemovalEvents};
pub use removal::{RemovalRuleSet, RemovalRule, RemovalCondition};
pub use navigation::{NavigationRuleSet, NavigationRule};
pub use behavior::FactionBehaviorMode;
