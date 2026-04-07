//! # ECS Systems
//!
//! Barrel file for re-exporting all ECS systems.
//!
//! ## Ownership
//! - **Task:** task_01_project_scaffold
//! - **Contract:** implementation_plan.md
//!
//! ## Depends On
//! - `movement_system`
//! - `initial_spawn_system`
//! - `tick_counter_system`

pub mod directive_executor;
pub mod engine_override;
pub mod flow_field_safety;
pub mod flow_field_update;
pub mod interaction;
pub mod movement;
pub mod removal;
pub mod spawning;
pub mod state_vectorizer;
pub mod visibility;
pub mod ws_command;
pub mod ws_sync;

use crate::config::TickCounter;
use bevy::prelude::*;

pub use directive_executor::{buff_tick_system, directive_executor_system, zone_tick_system};
pub use engine_override::engine_override_system;
pub use flow_field_update::flow_field_update_system;
pub use interaction::interaction_system;
pub use movement::movement_system;
pub use removal::removal_system;
pub use spawning::initial_spawn_system;
pub use visibility::visibility_update_system;
pub use ws_sync::{BroadcastSender, ws_sync_system};

/// Increments the global tick counter each frame.
///
/// Continually keeps track of ticks for serialization payload sync.
///
/// # Arguments
/// * `counter` - Monotonically increasing tick counter resource
pub fn tick_counter_system(mut counter: ResMut<TickCounter>) {
    counter.tick += 1;
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use bevy::app::App;

    #[test]
    fn test_tick_counter_increments() {
        // Arrange
        let mut app = App::new();
        app.insert_resource(TickCounter::default());
        app.add_systems(Update, tick_counter_system);

        // Act
        app.update();
        app.update();

        // Assert
        let counter = app.world().get_resource::<TickCounter>().unwrap();
        assert_eq!(
            counter.tick, 2,
            "Tick counter should increment by 2 after 2 updates"
        );
    }
}
