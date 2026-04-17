use bevy::prelude::*;
use serde::{Deserialize, Serialize};

/// Global simulation configuration. Inserted as a Bevy Resource at app startup.
#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct SimulationConfig {
    /// Width of the playable world in units
    pub world_width: f32,
    /// Height of the playable world in units
    pub world_height: f32,
    /// Initial number of entities to spawn
    pub initial_entity_count: u32,
    /// Size of a flow field cell in world units (default: 20.0).
    pub flow_field_cell_size: f32,
    /// Ticks between flow field recalculations (default: 30 = ~2 updates/sec).
    pub flow_field_update_interval: u64,
    /// Number of factions to alternate between during initial spawn.
    /// Default: 2 (faction 0 and faction 1).
    pub initial_faction_count: u32,
    /// Default stat values for initially spawned entities.
    /// Each tuple is (stat_index, value). Default: [(0, 1.0)].
    pub initial_stat_defaults: Vec<(usize, f32)>,
}

impl Default for SimulationConfig {
    fn default() -> Self {
        Self {
            world_width: 1000.0,
            world_height: 1000.0,
            initial_entity_count: 100,
            flow_field_cell_size: 20.0,
            flow_field_update_interval: 30,
            initial_faction_count: 2,
            initial_stat_defaults: vec![(0, 100.0)],
        }
    }
}

/// Monotonically increasing tick counter. Incremented once per ECS tick.
#[derive(Resource, Debug, Default)]
pub struct TickCounter {
    /// The current tick number
    pub tick: u64,
}

/// User-controlled simulation pause (from Debug Visualizer).
/// Independent of `SimState::WaitingForAI`.
#[derive(Resource, Debug, Clone, PartialEq)]
pub struct SimPaused(pub bool);

impl Default for SimPaused {
    fn default() -> Self {
        Self(true)
    }
}

/// Speed multiplier for entity movement.
#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct SimSpeed {
    pub multiplier: f32,
}

impl Default for SimSpeed {
    fn default() -> Self {
        Self { multiplier: 1.0 }
    }
}

/// Step mode: when > 0, movement runs for this many ticks even if paused,
/// then auto-pauses when it reaches 0. Used for single-step debugging.
#[derive(Resource, Debug, Clone, Default)]
pub struct SimStepRemaining(pub u32);

/// Whether the simulation is running in headless training mode.
/// When true, verbose per-tick logs are suppressed.
#[derive(Resource, Debug, Clone)]
pub struct TrainingMode(pub bool);

impl Default for TrainingMode {
    fn default() -> Self {
        Self(false)
    }
}

/// Flag set to `true` after `ResetEnvironment` writes new terrain data.
/// `ws_sync_system` reads this to broadcast terrain once, then clears it.
#[derive(Resource, Debug, Clone, Default)]
pub struct TerrainChanged(pub bool);

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = SimulationConfig::default();
        assert!(
            (config.world_width - 1000.0).abs() < f32::EPSILON,
            "world_width should be exactly 1000.0"
        );
        assert!(
            (config.world_height - 1000.0).abs() < f32::EPSILON,
            "world_height should be exactly 1000.0"
        );
        assert_eq!(
            config.initial_entity_count, 100,
            "initial_entity_count should be exactly 100"
        );
        assert!(
            (config.flow_field_cell_size - 20.0).abs() < f32::EPSILON,
            "cell_size should be 20.0"
        );
        assert_eq!(
            config.flow_field_update_interval, 30,
            "interval should be 30"
        );
        assert_eq!(
            config.initial_faction_count, 2,
            "default faction count should be 2"
        );
        assert_eq!(
            config.initial_stat_defaults,
            vec![(0, 100.0)],
            "default stats should be [(0, 100.0)]"
        );
    }

    #[test]
    fn test_tick_counter_default() {
        let counter = TickCounter::default();
        assert_eq!(counter.tick, 0, "Counter should start at 0");
    }

    #[test]
    fn test_sim_paused_default() {
        assert!(SimPaused::default().0, "SimPaused default should be true");
    }

    #[test]
    fn test_sim_speed_default() {
        assert!(
            (SimSpeed::default().multiplier - 1.0).abs() < f32::EPSILON,
            "SimSpeed multiplier default should be 1.0"
        );
    }

    #[test]
    fn test_sim_step_remaining_default() {
        assert_eq!(
            SimStepRemaining::default().0,
            0,
            "SimStepRemaining default should be 0"
        );
    }
}
