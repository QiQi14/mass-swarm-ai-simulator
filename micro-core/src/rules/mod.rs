//! # Rule Resources
//!
//! Config-driven rule sets for interactions, removals, navigation, and behavior.
//! These are DATA ONLY — no systems.
//!
//! ## Ownership
//! - **Task:** task_04_rule_resources
//! - **Contract:** implementation_plan.md → Contracts 5, 6, 10

pub mod behavior;
pub mod interaction;
pub mod navigation;
pub mod removal;

pub use behavior::FactionBehaviorMode;
pub use interaction::{InteractionRule, InteractionRuleSet, RemovalEvents, StatEffect};
pub use navigation::{NavigationRule, NavigationRuleSet};
pub use removal::{RemovalCondition, RemovalRule, RemovalRuleSet};
