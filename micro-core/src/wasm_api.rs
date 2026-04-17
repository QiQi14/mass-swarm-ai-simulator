//! # WASM API
//!
//! Browser-callable interface for running the micro-core simulation
//! entirely in WebAssembly. Exposes init, tick, spawn, and query
//! functions via `#[wasm_bindgen]`.
//!
//! ## Ownership
//! - **Task:** wasm_engine_build
//! - **Contract:** implementation_plan.md → WASM Build
//!
//! ## Depends On
//! - `crate::components::{Position, Velocity, FactionId, Stats, ClassId}`
//! - `crate::config::*`
//! - `crate::systems::*`
//! - `crate::rules::*`
//! - `crate::spatial::SpatialHashGrid`

use wasm_bindgen::prelude::*;
use bevy::prelude::*;

use crate::components::{FactionId, NextEntityId, Position, StatBlock, MAX_STATS, Velocity, UnitClassId};
use crate::config::*;
use crate::pathfinding::FlowFieldRegistry;
use crate::rules::*;
use crate::spatial::SpatialHashGrid;
use crate::systems::*;
use crate::terrain::TerrainGrid;
use crate::visibility::FactionVisibility;

/// Global simulation state held across WASM calls.
/// Uses thread_local because WASM is single-threaded.
thread_local! {
    static ENGINE: std::cell::RefCell<Option<App>> = std::cell::RefCell::new(None);
}

/// Initialize the simulation engine.
///
/// Creates a headless Bevy App with all ECS systems registered.
/// Must be called once before any other WASM function.
///
/// # Arguments
/// * `world_width` - World width in pixels (default: 1000.0)
/// * `world_height` - World height in pixels (default: 1000.0)
#[wasm_bindgen]
pub fn wasm_init(world_width: f32, world_height: f32) {
    let mut app = App::new();
    app.add_plugins(MinimalPlugins);
    app.add_plugins(bevy_state::app::StatesPlugin);

    let mut config = SimulationConfig::default();
    config.world_width = world_width;
    config.world_height = world_height;

    let cell_size = 20.0;
    let grid_w = (world_width / cell_size).ceil() as u32;
    let grid_h = (world_height / cell_size).ceil() as u32;

    app.insert_resource(config)
        .init_resource::<TickCounter>()
        .init_resource::<NextEntityId>()
        .insert_resource(SimPaused(false))
        .insert_resource(TrainingMode(false))
        .init_resource::<SimSpeed>()
        .init_resource::<SimStepRemaining>()
        .init_resource::<RemovalEvents>()
        .init_resource::<FactionBehaviorMode>()
        .init_resource::<NavigationRuleSet>()
        .init_resource::<InteractionRuleSet>()
        .init_resource::<RemovalRuleSet>()
        .insert_resource(SpatialHashGrid::new(cell_size))
        .init_resource::<FlowFieldRegistry>()
        .insert_resource(TerrainGrid::new(grid_w, grid_h, cell_size))
        .insert_resource(FactionVisibility::new(grid_w, grid_h, cell_size))
        .init_resource::<ActiveZoneModifiers>()
        .init_resource::<InterventionTracker>()
        .init_resource::<FactionBuffs>()
        .init_resource::<BuffConfig>()
        .init_resource::<CooldownTracker>()
        .init_resource::<DensityConfig>()
        .init_resource::<AggroMaskRegistry>()
        .init_resource::<ActiveSubFactions>()
        .init_resource::<crate::systems::directive_executor::LatestDirective>()
        .init_resource::<FactionTacticalOverrides>()
        .init_resource::<UnitTypeRegistry>()
        .init_resource::<TerrainChanged>();

    // Register simulation systems (same as play mode, minus WS/ZMQ)
    let sim_gate = |paused: Res<SimPaused>, step: Res<SimStepRemaining>| !paused.0 || step.0 > 0;

    app.add_systems(
        Update,
        (
            flow_field_update_system,
            crate::spatial::update_spatial_grid_system,
            interaction_system,
            aoe_interaction_system,
            penetration_interaction_system,
            removal_system,
            tactical_sensor_system,
            movement_system,
        )
            .chain()
            .run_if(sim_gate),
    );
    app.add_systems(
        Update,
        (
            directive_executor_system,
            zone_tick_system,
            buff_tick_system,
        )
            .chain()
            .run_if(|paused: Res<SimPaused>, step: Res<SimStepRemaining>| !paused.0 || step.0 > 0)
            .before(movement_system),
    )
    .add_systems(
        Update,
        engine_override_system
            .after(movement_system)
            .run_if(|paused: Res<SimPaused>, step: Res<SimStepRemaining>| !paused.0 || step.0 > 0),
    )
    .add_systems(
        Update,
        (
            tick_counter_system,
            visibility_update_system,
        ),
    );

    ENGINE.with(|cell| {
        *cell.borrow_mut() = Some(app);
    });
}

/// Advance the simulation by `n` ticks.
///
/// Each call runs `app.update()` n times. For smooth 60fps rendering,
/// call `wasm_tick(1)` per animation frame.
#[wasm_bindgen]
pub fn wasm_tick(n: u32) {
    ENGINE.with(|cell| {
        if let Some(app) = cell.borrow_mut().as_mut() {
            for _ in 0..n {
                app.update();
            }
        }
    });
}

/// Returns the current tick count.
#[wasm_bindgen]
pub fn wasm_get_tick() -> u64 {
    ENGINE.with(|cell| {
        cell.borrow()
            .as_ref()
            .and_then(|app| app.world().get_resource::<TickCounter>())
            .map(|c| c.tick)
            .unwrap_or(0)
    })
}

/// Returns all entity data as a flat Float32Array.
///
/// Layout per entity (stride = 6 floats):
///   [x, y, faction_id, hp, dx, dy]
///
/// Total length = entity_count * 6.
#[wasm_bindgen]
pub fn wasm_get_entities() -> Vec<f32> {
    ENGINE.with(|cell| {
        let mut borrow = cell.borrow_mut();
        let Some(app) = borrow.as_mut() else {
            return Vec::new();
        };
        let world = app.world_mut();

        let mut buf = Vec::new();
        let mut query = world.query::<(&Position, &Velocity, &FactionId, &StatBlock)>();
        for (pos, vel, fid, stats) in query.iter(world) {
            buf.push(pos.x);
            buf.push(pos.y);
            buf.push(fid.0 as f32);
            buf.push(stats.0[0]);
            buf.push(vel.dx);
            buf.push(vel.dy);
        }
        buf
    })
}

/// Returns the number of alive entities.
#[wasm_bindgen]
pub fn wasm_entity_count() -> u32 {
    ENGINE.with(|cell| {
        let mut borrow = cell.borrow_mut();
        let Some(app) = borrow.as_mut() else {
            return 0;
        };
        let world = app.world_mut();
        let mut query = world.query::<&Position>();
        query.iter(world).count() as u32
    })
}

/// Spawn entities for a faction.
///
/// # Arguments
/// * `faction_id` - Faction ID (0, 1, 2, ...)
/// * `count` - Number of entities to spawn
/// * `x` - Center X position
/// * `y` - Center Y position
/// * `spread` - Random spread radius
/// * `stats_json` - JSON array of initial stat values, e.g. "[100.0]"
#[wasm_bindgen]
pub fn wasm_spawn(faction_id: u32, count: u32, x: f32, y: f32, spread: f32, stats_json: &str) {
    let stats_values: Vec<f32> = serde_json::from_str(stats_json).unwrap_or_else(|_| vec![100.0]);

    ENGINE.with(|cell| {
        if let Some(app) = cell.borrow_mut().as_mut() {
            let world = app.world_mut();
            let mut rng = rand::rng();
            use rand::Rng;

            for _ in 0..count {
                let sx = x + rng.random_range(-spread..spread);
                let sy = y + rng.random_range(-spread..spread);

                let mut stat_block = [0.0f32; MAX_STATS];
                for (i, v) in stats_values.iter().enumerate() {
                    if i < MAX_STATS { stat_block[i] = *v; }
                }

                world.spawn((
                    Position { x: sx, y: sy },
                    Velocity { dx: 0.0, dy: 0.0 },
                    FactionId(faction_id),
                    StatBlock(stat_block),
                    UnitClassId(0),
                ));
            }
        }
    });
}

/// Set navigation rules from JSON.
///
/// Expects a JSON array matching the NavigationRule schema.
#[wasm_bindgen]
pub fn wasm_set_navigation(json: &str) {
    ENGINE.with(|cell| {
        if let Some(app) = cell.borrow_mut().as_mut() {
            if let Ok(rules) = serde_json::from_str::<Vec<NavigationRule>>(json) {
                if let Some(mut ruleset) = app.world_mut().get_resource_mut::<NavigationRuleSet>() {
                    ruleset.rules = rules;
                }
            }
        }
    });
}

/// Set interaction rules from JSON.
///
/// Expects a JSON array matching the InteractionRule schema.
#[wasm_bindgen]
pub fn wasm_set_interaction(json: &str) {
    ENGINE.with(|cell| {
        if let Some(app) = cell.borrow_mut().as_mut() {
            if let Ok(rules) = serde_json::from_str::<Vec<InteractionRule>>(json) {
                if let Some(mut ruleset) = app.world_mut().get_resource_mut::<InteractionRuleSet>() {
                    ruleset.rules = rules;
                }
            }
        }
    });
}

/// Set removal rules from JSON.
///
/// Expects a JSON array matching the RemovalRule schema.
#[wasm_bindgen]
pub fn wasm_set_removal(json: &str) {
    ENGINE.with(|cell| {
        if let Some(app) = cell.borrow_mut().as_mut() {
            if let Ok(rules) = serde_json::from_str::<Vec<RemovalRule>>(json) {
                if let Some(mut ruleset) = app.world_mut().get_resource_mut::<RemovalRuleSet>() {
                    ruleset.rules = rules;
                }
            }
        }
    });
}

/// Kill all entities belonging to a faction.
///
/// Pass `u32::MAX` (4294967295) to kill ALL entities regardless of faction.
#[wasm_bindgen]
pub fn wasm_kill_all(faction_id: u32) {
    ENGINE.with(|cell| {
        if let Some(app) = cell.borrow_mut().as_mut() {
            let world = app.world_mut();
            let mut to_despawn = Vec::new();
            {
                let mut query = world.query::<(Entity, &FactionId)>();
                for (entity, fid) in query.iter(world) {
                    if faction_id == u32::MAX || fid.0 == faction_id {
                        to_despawn.push(entity);
                    }
                }
            }
            for entity in to_despawn {
                world.despawn(entity);
            }
        }
    });
}

/// Toggle pause state.
#[wasm_bindgen]
pub fn wasm_toggle_pause() {
    ENGINE.with(|cell| {
        if let Some(app) = cell.borrow_mut().as_mut() {
            if let Some(mut paused) = app.world_mut().get_resource_mut::<SimPaused>() {
                paused.0 = !paused.0;
            }
        }
    });
}

/// Returns true if simulation is paused.
#[wasm_bindgen]
pub fn wasm_is_paused() -> bool {
    ENGINE.with(|cell| {
        cell.borrow()
            .as_ref()
            .and_then(|app| app.world().get_resource::<SimPaused>())
            .map(|p| p.0)
            .unwrap_or(true)
    })
}
