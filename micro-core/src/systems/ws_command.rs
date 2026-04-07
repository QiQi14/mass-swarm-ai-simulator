//! # WebSocket Command System
//!
//! Receives and processes commands from the Debug Visualizer via WebSocket.
//!
//! ## Ownership
//! - **Task:** task_03_ws_bidirectional_commands
//! - **Contract:** implementation_plan.md → Phase 1 Micro-Phase 4
//!
//! **File Size Rationale:** This module is 580+ lines but contains only two tightly
//! coupled systems (`ws_command_system` + `step_tick_system`) that share the same
//! WS receiver channel. Splitting would fragment the ownership chain.
//! Split if a third concern is added or tests exceed 300 lines.
//!
//! ## Depends On
//! - `crate::config::{SimPaused, SimSpeed, SimStepRemaining, SimulationConfig}`
//! - `crate::bridges::ws_protocol::WsCommand`
//! - `crate::components::{Position, FactionId, StatBlock, Velocity, NextEntityId, EntityId}`

use bevy::prelude::*;
use rand::Rng;
use std::sync::{Mutex, mpsc};

use crate::bridges::ws_protocol::WsCommand;
use crate::bridges::zmq_protocol::MacroDirective;
use crate::components::{
    EngineOverride, EntityId, FactionId, MovementConfig, NextEntityId, Position, StatBlock,
    Velocity, VisionRadius,
};
use crate::config::{
    ActiveZoneModifiers, AggroMaskRegistry, SimPaused, SimSpeed, SimStepRemaining,
    SimulationConfig, ZoneModifier,
};
use crate::rules::{FactionBehaviorMode, InteractionRuleSet, NavigationRuleSet, RemovalRuleSet};
use crate::systems::directive_executor::LatestDirective;
use crate::systems::ws_sync::BroadcastSender;
use crate::terrain::TerrainGrid;

// Created here because it was missing from Task 12
#[derive(Resource, Default, Debug, Clone)]
pub struct ActiveFogFaction(pub Option<u32>);

/// Resource wrapping the standard library MPSC receiver for WS commands.
#[derive(Resource)]
pub struct WsCommandReceiver(pub Mutex<mpsc::Receiver<String>>);

/// Processes incoming WebSocket commands and updates simulation state accordingly.
#[allow(clippy::too_many_arguments)]
#[allow(clippy::collapsible_if)]
#[allow(clippy::type_complexity)]
pub fn ws_command_system(
    receiver: Res<WsCommandReceiver>,
    mut commands: Commands,
    mut next_id: ResMut<NextEntityId>,
    mut paused: ResMut<SimPaused>,
    mut speed: ResMut<SimSpeed>,
    mut step: ResMut<SimStepRemaining>,
    _config: Res<SimulationConfig>,
    faction_query: Query<(
        Entity,
        &EntityId,
        &Position,
        &Velocity,
        &FactionId,
        &StatBlock,
    )>,
    mut behavior_mode: ResMut<FactionBehaviorMode>,
    mut terrain: ResMut<TerrainGrid>,
    sender: Option<Res<BroadcastSender>>,
    mut removal_events: ResMut<crate::rules::RemovalEvents>,
    mut optionals: (
        Option<ResMut<ActiveFogFaction>>,
        Option<ResMut<ActiveZoneModifiers>>,
        Option<ResMut<LatestDirective>>,
        Option<ResMut<AggroMaskRegistry>>,
    ),
    mut rule_sets: (
        ResMut<NavigationRuleSet>,
        ResMut<InteractionRuleSet>,
        ResMut<RemovalRuleSet>,
    ),
) {
    let Ok(rx) = receiver.0.lock() else {
        return;
    };
    while let Ok(json) = rx.try_recv() {
        if let Ok(cmd) = serde_json::from_str::<WsCommand>(&json) {
            match cmd.cmd.as_str() {
                "toggle_sim" => {
                    paused.0 = !paused.0;
                    println!(
                        "[WS Command] Simulation {}",
                        if paused.0 { "paused" } else { "resumed" }
                    );
                }
                "step" => {
                    let count = cmd
                        .params
                        .get("count")
                        .and_then(|v| v.as_u64())
                        .unwrap_or(1) as u32;
                    step.0 = count;
                    println!("[WS Command] Stepping {} tick(s)", count);
                }
                "spawn_wave" => {
                    let faction_id = cmd
                        .params
                        .get("faction_id")
                        .and_then(|v| v.as_u64())
                        .unwrap_or(0) as u32;
                    let amount = cmd
                        .params
                        .get("amount")
                        .and_then(|v| v.as_u64())
                        .unwrap_or(1) as u32;
                    let x = cmd.params.get("x").and_then(|v| v.as_f64()).unwrap_or(0.0) as f32;
                    let y = cmd.params.get("y").and_then(|v| v.as_f64()).unwrap_or(0.0) as f32;
                    let spread = cmd
                        .params
                        .get("spread")
                        .and_then(|v| v.as_f64())
                        .unwrap_or(0.0) as f32;

                    let mut stats = Vec::new();
                    if let Some(stats_array) = cmd.params.get("stats").and_then(|v| v.as_array()) {
                        for stat_val in stats_array {
                            if let (Some(idx), Some(val)) = (
                                stat_val.get("index").and_then(|v| v.as_u64()),
                                stat_val.get("value").and_then(|v| v.as_f64()),
                            ) {
                                stats.push((idx as usize, val as f32));
                            }
                        }
                    }
                    if stats.is_empty() {
                        stats.push((0, 100.0));
                    }

                    let mut rng = rand::rng();
                    let golden_angle = 137.5f32.to_radians();

                    let default_mc = MovementConfig {
                        max_speed: 60.0,
                        steering_factor: 5.0,
                        separation_radius: 6.0,
                        separation_weight: 1.5,
                        flow_weight: 1.0,
                    };

                    let mut spawned_count = 0;
                    for i in 0..amount {
                        let (spawn_x, spawn_y) = if spread > 0.0 {
                            let r = spread * (i as f32 / amount as f32).sqrt();
                            let theta = i as f32 * golden_angle;
                            (x + r * theta.cos(), y + r * theta.sin())
                        } else {
                            (x, y)
                        };

                        if terrain.get_hard_cost(terrain.world_to_cell(spawn_x, spawn_y))
                            == u16::MAX
                        {
                            continue;
                        }

                        commands.spawn((
                            EntityId { id: next_id.0 },
                            Position {
                                x: spawn_x,
                                y: spawn_y,
                            },
                            Velocity {
                                dx: rng.random_range(-1.0..1.0),
                                dy: rng.random_range(-1.0..1.0),
                            },
                            FactionId(faction_id),
                            StatBlock::with_defaults(&stats),
                            VisionRadius::default(),
                            default_mc,
                        ));
                        next_id.0 += 1;
                        spawned_count += 1;
                    }
                    println!(
                        "[WS Command] Spawned {}/{} faction_{} at ({}, {}) spread {}",
                        spawned_count, amount, faction_id, x, y, spread
                    );
                }
                "set_speed" => {
                    if let Some(m) = cmd.params.get("multiplier").and_then(|v| v.as_f64()) {
                        speed.multiplier = m as f32;
                        println!("[WS Command] Set speed to {}", speed.multiplier);
                    }
                }
                "kill_all" => {
                    if let Some(fid) = cmd.params.get("faction_id").and_then(|v| v.as_u64()) {
                        let target_faction = FactionId(fid as u32);
                        let mut count = 0;
                        for (entity, eid, _, _, faction, _) in faction_query.iter() {
                            if *faction == target_faction {
                                removal_events.removed_ids.push(eid.id);
                                commands.entity(entity).despawn();
                                count += 1;
                            }
                        }
                        println!("[WS Command] Killed {} faction_{} entities", count, fid);
                    }
                }
                "set_faction_mode" => {
                    if let (Some(faction_id), Some(mode)) = (
                        cmd.params
                            .get("faction_id")
                            .and_then(|v| v.as_u64())
                            .map(|v| v as u32),
                        cmd.params.get("mode").and_then(|v| v.as_str()),
                    ) {
                        match mode {
                            "static" => {
                                behavior_mode.static_factions.insert(faction_id);
                            }
                            "brain" => {
                                behavior_mode.static_factions.remove(&faction_id);
                            }
                            _ => {
                                println!("[WS Command] Unknown mode: {}", mode);
                            }
                        }
                        println!("[WS Command] Faction {} mode set to: {}", faction_id, mode);
                    }
                }
                "set_terrain" => {
                    if let Some(cells) = cmd.params.get("cells").and_then(|v| v.as_array()) {
                        for cell in cells {
                            if let (Some(x), Some(y), Some(hard), Some(soft)) = (
                                cell.get("x").and_then(|v| v.as_u64()),
                                cell.get("y").and_then(|v| v.as_u64()),
                                cell.get("hard").and_then(|v| v.as_u64()),
                                cell.get("soft").and_then(|v| v.as_u64()),
                            ) {
                                terrain.set_cell(x as u32, y as u32, hard as u16, soft as u16);
                            }
                        }
                        println!("[WS Command] set_terrain with {} cells", cells.len());
                    }
                }
                "clear_terrain" => {
                    terrain.reset();
                    println!("[WS Command] clear_terrain");
                }
                "save_scenario" => {
                    if let Some(sender_res) = &sender {
                        let mut ents = Vec::new();
                        for (_, eid, pos, _, faction, stat_block) in faction_query.iter() {
                            ents.push(serde_json::json!({
                                "id": eid.id,
                                "x": pos.x,
                                "y": pos.y,
                                "faction_id": faction.0,
                                "stats": stat_block.0.to_vec(),
                            }));
                        }

                        let msg = serde_json::json!({
                            "type": "scenario_data",
                            "terrain": {
                                "hard_costs": terrain.hard_costs,
                                "soft_costs": terrain.soft_costs,
                                "width": terrain.width,
                                "height": terrain.height,
                                "cell_size": terrain.cell_size
                            },
                            "entities": ents
                        });

                        if let Ok(json_str) = serde_json::to_string(&msg) {
                            let _ = sender_res.0.send(json_str);
                        }
                        println!("[WS Command] save_scenario broadcasted");
                    }
                }
                "load_scenario" => {
                    for (entity, eid, _, _, _, _) in faction_query.iter() {
                        removal_events.removed_ids.push(eid.id);
                        commands.entity(entity).despawn();
                    }
                    let mut max_loaded_id = 0;

                    if let Some(t_data) = cmd.params.get("terrain") {
                        if let (Some(hard), Some(soft), Some(w), Some(h), Some(cs)) = (
                            t_data.get("hard_costs").and_then(|v| v.as_array()),
                            t_data.get("soft_costs").and_then(|v| v.as_array()),
                            t_data.get("width").and_then(|v| v.as_u64()),
                            t_data.get("height").and_then(|v| v.as_u64()),
                            t_data.get("cell_size").and_then(|v| v.as_f64()),
                        ) {
                            terrain.width = w as u32;
                            terrain.height = h as u32;
                            terrain.cell_size = cs as f32;
                            terrain.hard_costs = hard
                                .iter()
                                .filter_map(|v| v.as_u64().map(|n| n as u16))
                                .collect();
                            terrain.soft_costs = soft
                                .iter()
                                .filter_map(|v| v.as_u64().map(|n| n as u16))
                                .collect();
                        }
                    }

                    if let Some(ents) = cmd.params.get("entities").and_then(|v| v.as_array()) {
                        for e in ents {
                            if let (Some(id), Some(x), Some(y), Some(faction)) = (
                                e.get("id").and_then(|v| v.as_u64()),
                                e.get("x").and_then(|v| v.as_f64()),
                                e.get("y").and_then(|v| v.as_f64()),
                                e.get("faction_id").and_then(|v| v.as_u64()),
                            ) {
                                let id = id as u32;
                                if id > max_loaded_id {
                                    max_loaded_id = id;
                                }

                                let mut base_stats = [0.0; crate::components::MAX_STATS];
                                if let Some(stats_arr) = e.get("stats").and_then(|v| v.as_array()) {
                                    for (i, val) in
                                        stats_arr.iter().enumerate().take(base_stats.len())
                                    {
                                        base_stats[i] = val.as_f64().unwrap_or(0.0) as f32;
                                    }
                                }

                                commands.spawn((
                                    EntityId { id },
                                    Position {
                                        x: x as f32,
                                        y: y as f32,
                                    },
                                    Velocity { dx: 0.0, dy: 0.0 },
                                    FactionId(faction as u32),
                                    StatBlock(base_stats),
                                    VisionRadius::default(),
                                    MovementConfig::default(),
                                ));
                            }
                        }
                    }
                    next_id.0 = max_loaded_id + 1;
                    println!(
                        "[WS Command] load_scenario complete, NextEntityId: {}",
                        next_id.0
                    );
                }
                "set_fog_faction" => {
                    if let Some(ref mut af) = optionals.0 {
                        if cmd.params.get("faction_id").is_none_or(|v| v.is_null()) {
                            af.0 = None;
                            println!("[WS Command] set_fog_faction: disable");
                        } else if let Some(fid) =
                            cmd.params.get("faction_id").and_then(|v| v.as_u64())
                        {
                            af.0 = Some(fid as u32);
                            println!("[WS Command] set_fog_faction: {}", fid);
                        }
                    }
                }
                "place_zone_modifier" => {
                    if let Some(ref mut zones) = optionals.1 {
                        if let (
                            Some(target_faction),
                            Some(x),
                            Some(y),
                            Some(radius),
                            Some(cost_modifier),
                            Some(ticks),
                        ) = (
                            cmd.params.get("target_faction").and_then(|v| v.as_u64()),
                            cmd.params.get("x").and_then(|v| v.as_f64()),
                            cmd.params.get("y").and_then(|v| v.as_f64()),
                            cmd.params.get("radius").and_then(|v| v.as_f64()),
                            cmd.params.get("cost_modifier").and_then(|v| v.as_f64()),
                            cmd.params.get("ticks").and_then(|v| v.as_u64()),
                        ) {
                            zones.zones.push(ZoneModifier {
                                target_faction: target_faction as u32,
                                x: x as f32,
                                y: y as f32,
                                radius: radius as f32,
                                cost_modifier: cost_modifier as f32,
                                ticks_remaining: ticks as u32,
                            });
                            println!(
                                "[WS Command] Placed ZoneModifier at ({}, {}) cost {}",
                                x, y, cost_modifier
                            );
                        }
                    }
                }
                "split_faction" => {
                    if let Some(ref mut ld) = optionals.2 {
                        if let (Some(source), Some(target), Some(pct), Some(ex), Some(ey)) = (
                            cmd.params.get("source_faction").and_then(|v| v.as_u64()),
                            cmd.params.get("new_sub_faction").and_then(|v| v.as_u64()),
                            cmd.params.get("percentage").and_then(|v| v.as_f64()),
                            cmd.params.get("epicenter_x").and_then(|v| v.as_f64()),
                            cmd.params.get("epicenter_y").and_then(|v| v.as_f64()),
                        ) {
                            ld.directive = Some(MacroDirective::SplitFaction {
                                source_faction: source as u32,
                                new_sub_faction: target as u32,
                                percentage: pct as f32,
                                epicenter: [ex as f32, ey as f32],
                            });
                            println!("[WS Command] Sent SplitFaction");
                        }
                    }
                }
                "merge_faction" => {
                    if let Some(ref mut ld) = optionals.2 {
                        if let (Some(source), Some(target)) = (
                            cmd.params.get("source_faction").and_then(|v| v.as_u64()),
                            cmd.params.get("target_faction").and_then(|v| v.as_u64()),
                        ) {
                            ld.directive = Some(MacroDirective::MergeFaction {
                                source_faction: source as u32,
                                target_faction: target as u32,
                            });
                            println!("[WS Command] Sent MergeFaction");
                        }
                    }
                }
                "set_aggro_mask" => {
                    if let Some(ref mut am) = optionals.3 {
                        if let (Some(source), Some(target), Some(allow)) = (
                            cmd.params.get("source_faction").and_then(|v| v.as_u64()),
                            cmd.params.get("target_faction").and_then(|v| v.as_u64()),
                            cmd.params.get("allow_combat").and_then(|v| v.as_bool()),
                        ) {
                            am.masks.insert((source as u32, target as u32), allow);
                            println!(
                                "[WS Command] SetAggroMask {} -> {} = {}",
                                source, target, allow
                            );
                        }
                    }
                }
                "inject_directive" => {
                    if let Some(ref mut ld) = optionals.2 {
                        if let Some(dir_val) = cmd.params.get("directive") {
                            if let Ok(dir) =
                                serde_json::from_value::<MacroDirective>(dir_val.clone())
                            {
                                ld.directive = Some(dir);
                                println!("[WS Command] Injected Raw MacroDirective");
                            } else {
                                eprintln!("[WS Command] Failed to parse MacroDirective");
                            }
                        }
                    }
                }
                "set_engine_override" => {
                    if let (Some(entity_id), Some(vx), Some(vy), Some(ticks)) = (
                        cmd.params.get("entity_id").and_then(|v| v.as_u64()),
                        cmd.params.get("vx").and_then(|v| v.as_f64()),
                        cmd.params.get("vy").and_then(|v| v.as_f64()),
                        cmd.params.get("ticks").and_then(|v| v.as_u64()),
                    ) {
                        for (entity, eid, _, _, _, _) in faction_query.iter() {
                            if eid.id == entity_id as u32 {
                                commands.entity(entity).insert(EngineOverride {
                                    forced_velocity: Vec2::new(vx as f32, vy as f32),
                                    ticks_remaining: if ticks > 0 {
                                        Some(ticks as u32)
                                    } else {
                                        None
                                    },
                                });
                                println!("[WS Command] Set EngineOverride on {}", entity_id);
                                break;
                            }
                        }
                    }
                }
                "clear_engine_override" => {
                    if let Some(entity_id) = cmd.params.get("entity_id").and_then(|v| v.as_u64()) {
                        for (entity, eid, _, _, _, _) in faction_query.iter() {
                            if eid.id == entity_id as u32 {
                                commands.entity(entity).remove::<EngineOverride>();
                                println!("[WS Command] Cleared EngineOverride on {}", entity_id);
                                break;
                            }
                        }
                    }
                }
                "set_navigation" => {
                    if let Some(rules_array) = cmd.params.get("rules").and_then(|v| v.as_array()) {
                        rule_sets.0.rules.clear();
                        for rule_json in rules_array {
                            if let (Some(follower), Some(target_json)) = (
                                rule_json.get("follower_faction").and_then(|v| v.as_u64()),
                                rule_json.get("target"),
                            ) {
                                if let Ok(target) =
                                    serde_json::from_value::<
                                        crate::bridges::zmq_protocol::NavigationTarget,
                                    >(target_json.clone())
                                {
                                    rule_sets.0.rules.push(crate::rules::NavigationRule {
                                        follower_faction: follower as u32,
                                        target,
                                    });
                                }
                            }
                        }
                        println!(
                            "[WS Command] Set {} navigation rules",
                            rule_sets.0.rules.len()
                        );
                    }
                }
                "set_interaction" => {
                    if let Some(rules_array) = cmd.params.get("rules").and_then(|v| v.as_array()) {
                        rule_sets.1.rules.clear();
                        for rule_json in rules_array {
                            if let (Some(source), Some(target), Some(range)) = (
                                rule_json.get("source_faction").and_then(|v| v.as_u64()),
                                rule_json.get("target_faction").and_then(|v| v.as_u64()),
                                rule_json.get("range").and_then(|v| v.as_f64()),
                            ) {
                                let effects = rule_json
                                    .get("effects")
                                    .and_then(|v| v.as_array())
                                    .map(|fx| {
                                        fx.iter()
                                            .filter_map(|e| {
                                                Some(crate::rules::StatEffect {
                                                    stat_index: e.get("stat_index")?.as_u64()?
                                                        as usize,
                                                    delta_per_second: e
                                                        .get("delta_per_second")?
                                                        .as_f64()?
                                                        as f32,
                                                })
                                            })
                                            .collect()
                                    })
                                    .unwrap_or_default();

                                rule_sets.1.rules.push(crate::rules::InteractionRule {
                                    source_faction: source as u32,
                                    target_faction: target as u32,
                                    range: range as f32,
                                    effects,
                                });
                            }
                        }
                        println!(
                            "[WS Command] Set {} interaction rules",
                            rule_sets.1.rules.len()
                        );
                    }
                }
                "set_removal" => {
                    if let Some(rules_array) = cmd.params.get("rules").and_then(|v| v.as_array()) {
                        rule_sets.2.rules.clear();
                        for rule_json in rules_array {
                            if let (Some(stat_idx), Some(threshold)) = (
                                rule_json.get("stat_index").and_then(|v| v.as_u64()),
                                rule_json.get("threshold").and_then(|v| v.as_f64()),
                            ) {
                                let condition =
                                    match rule_json.get("condition").and_then(|v| v.as_str()) {
                                        Some("GreaterThanEqual") => {
                                            crate::rules::RemovalCondition::GreaterOrEqual
                                        }
                                        _ => crate::rules::RemovalCondition::LessOrEqual,
                                    };
                                rule_sets.2.rules.push(crate::rules::RemovalRule {
                                    stat_index: stat_idx as usize,
                                    threshold: threshold as f32,
                                    condition,
                                });
                            }
                        }
                        println!("[WS Command] Set {} removal rules", rule_sets.2.rules.len());
                    }
                }
                other => {
                    eprintln!("[WS Command] Unknown: {}", other);
                }
            }
        }
    }
}

/// Decrements step counter and auto-pauses when step mode completes.
/// Runs every tick when steps remain (regardless of SimPaused).
pub fn step_tick_system(mut step: ResMut<SimStepRemaining>, mut paused: ResMut<SimPaused>) {
    if step.0 > 0 {
        step.0 -= 1;
        if step.0 == 0 {
            paused.0 = true;
            println!("[Step Mode] Step complete, auto-paused");
        }
    }
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use bevy::app::App;
    use tokio::sync::broadcast;

    // We make a helper building an app
    fn setup_app() -> (App, mpsc::Sender<String>) {
        let mut app = App::new();
        let (tx, rx) = mpsc::channel();
        app.insert_resource(WsCommandReceiver(Mutex::new(rx)));
        app.insert_resource(NextEntityId(1));
        app.insert_resource(SimPaused(false));
        app.insert_resource(SimSpeed { multiplier: 1.0 });
        app.insert_resource(SimStepRemaining(0));
        app.insert_resource(SimulationConfig::default());
        app.insert_resource(FactionBehaviorMode::default());
        app.insert_resource(TerrainGrid::new(50, 50, 20.0));
        app.insert_resource(ActiveFogFaction(None));
        app.init_resource::<crate::rules::RemovalEvents>();
        app.init_resource::<crate::rules::NavigationRuleSet>();
        app.init_resource::<crate::rules::InteractionRuleSet>();
        app.init_resource::<crate::rules::RemovalRuleSet>();

        let (btx, _) = broadcast::channel(10);
        app.insert_resource(BroadcastSender(btx));

        app.add_systems(Update, ws_command_system);
        (app, tx)
    }

    #[test]
    fn test_fibonacci_spiral_no_overlap() {
        let (mut app, tx) = setup_app();

        let cmd = serde_json::json!({
            "type": "command",
            "cmd": "spawn_wave",
            "params": {
                "amount": 100,
                "x": 50.0,
                "y": 50.0,
                "spread": 50.0
            }
        });
        tx.send(cmd.to_string()).unwrap();

        app.update();

        let mut positions = Vec::new();
        for pos in app.world_mut().query::<&Position>().iter(app.world()) {
            positions.push((pos.x, pos.y));
        }

        assert_eq!(positions.len(), 100);

        for i in 0..positions.len() {
            for j in (i + 1)..positions.len() {
                let dx = positions[i].0 - positions[j].0;
                let dy = positions[i].1 - positions[j].1;
                let dist = (dx * dx + dy * dy).sqrt();
                // They should not overlap exactly
                assert!(dist > 0.1, "Found overlapping entities at dist: {}", dist);
            }
        }
    }

    #[test]
    fn test_fibonacci_spiral_skips_walls() {
        let (mut app, tx) = setup_app();

        // Put a wall right at (50, 50)
        let cell_x = 50.0 / 20.0;
        let cell_y = 50.0 / 20.0;
        app.world_mut()
            .get_resource_mut::<TerrainGrid>()
            .unwrap()
            .set_cell(cell_x as u32, cell_y as u32, u16::MAX, 0);

        let cmd = serde_json::json!({
            "type": "command",
            "cmd": "spawn_wave",
            "params": {
                "amount": 1,
                "x": 50.0,
                "y": 50.0,
                "spread": 0.0 // no spread: tries to spawn precisely at wall
            }
        });
        tx.send(cmd.to_string()).unwrap();

        app.update();

        let count = app
            .world_mut()
            .query::<&Position>()
            .iter(app.world())
            .count();
        assert_eq!(count, 0, "Should have skipped spawning inside wall");
    }

    #[test]
    fn test_set_terrain_updates_grid() {
        let (mut app, tx) = setup_app();

        let cmd = serde_json::json!({
            "type": "command",
            "cmd": "set_terrain",
            "params": {
                "cells": [
                    { "x": 10, "y": 10, "hard": u16::MAX, "soft": 0 },
                    { "x": 11, "y": 10, "hard": 200, "soft": 50 }
                ]
            }
        });
        tx.send(cmd.to_string()).unwrap();

        app.update();

        let terrain = app.world().get_resource::<TerrainGrid>().unwrap();
        assert_eq!(terrain.get_hard_cost(IVec2::new(10, 10)), u16::MAX);
        assert_eq!(terrain.get_hard_cost(IVec2::new(11, 10)), 200);
        assert_eq!(terrain.get_soft_cost(IVec2::new(11, 10)), 50);
    }

    #[test]
    fn test_clear_terrain_resets_all() {
        let (mut app, tx) = setup_app();

        // First set terrain
        app.world_mut()
            .get_resource_mut::<TerrainGrid>()
            .unwrap()
            .set_cell(5, 5, u16::MAX, 0);

        let cmd = serde_json::json!({
            "type": "command",
            "cmd": "clear_terrain",
            "params": {}
        });
        tx.send(cmd.to_string()).unwrap();

        app.update();

        let terrain = app.world().get_resource::<TerrainGrid>().unwrap();
        assert!(terrain.hard_costs.iter().all(|&c| c == 100));
        assert!(terrain.soft_costs.iter().all(|&c| c == 100));
    }

    #[test]
    fn test_load_scenario_updates_next_entity_id() {
        let (mut app, tx) = setup_app();

        app.world_mut()
            .get_resource_mut::<NextEntityId>()
            .unwrap()
            .0 = 1;

        let cmd = serde_json::json!({
            "type": "command",
            "cmd": "load_scenario",
            "params": {
                "entities": [
                    { "id": 1, "x": 10.0, "y": 10.0, "faction_id": 0, "stats": [] },
                    { "id": 50, "x": 20.0, "y": 20.0, "faction_id": 1, "stats": [] }
                ]
            }
        });
        tx.send(cmd.to_string()).unwrap();

        app.update();

        let next_id = app.world().get_resource::<NextEntityId>().unwrap().0;
        assert_eq!(next_id, 51);

        let mut count = 0;
        for (_, &EntityId { id }, _, _, _, _) in app
            .world_mut()
            .query::<(
                Entity,
                &EntityId,
                &Position,
                &Velocity,
                &FactionId,
                &StatBlock,
            )>()
            .iter(app.world())
        {
            count += 1;
            assert!(id == 1 || id == 50);
        }
        assert_eq!(count, 2);
    }

    #[test]
    fn test_step_tick_system_decrements_and_pauses() {
        // ... omitted since we already tested StepTick in original file
        // Here we just test it broadly
        let mut app = App::new();
        app.insert_resource(SimStepRemaining(2));
        app.insert_resource(SimPaused(false));
        app.add_systems(Update, step_tick_system);

        app.update();
        assert_eq!(app.world().resource::<SimStepRemaining>().0, 1);
        assert!(!app.world().resource::<SimPaused>().0);

        app.update();
        assert_eq!(app.world().resource::<SimStepRemaining>().0, 0);
        assert!(app.world().resource::<SimPaused>().0);
    }
    #[test]
    fn test_set_navigation_ws_command() {
        let (mut app, tx) = setup_app();
        let cmd = serde_json::json!({
            "type": "command",
            "cmd": "set_navigation",
            "params": {
                "rules": [
                    { "follower_faction": 0, "target": { "type": "Faction", "faction_id": 1 } }
                ]
            }
        });
        tx.send(cmd.to_string()).unwrap();
        app.update();
        let nav_rules = app
            .world()
            .get_resource::<crate::rules::NavigationRuleSet>()
            .unwrap();
        assert_eq!(nav_rules.rules.len(), 1);
        assert_eq!(nav_rules.rules[0].follower_faction, 0);
    }

    #[test]
    fn test_set_interaction_ws_command() {
        let (mut app, tx) = setup_app();
        let cmd = serde_json::json!({
            "type": "command",
            "cmd": "set_interaction",
            "params": {
                "rules": [
                    { "source_faction": 0, "target_faction": 1, "range": 15.0, "effects": [{ "stat_index": 0, "delta_per_second": -10.0 }] }
                ]
            }
        });
        tx.send(cmd.to_string()).unwrap();
        app.update();
        let int_rules = app
            .world()
            .get_resource::<crate::rules::InteractionRuleSet>()
            .unwrap();
        assert_eq!(int_rules.rules.len(), 1);
        assert_eq!(int_rules.rules[0].source_faction, 0);
        assert_eq!(int_rules.rules[0].range, 15.0);
    }

    #[test]
    fn test_set_removal_ws_command() {
        let (mut app, tx) = setup_app();
        let cmd = serde_json::json!({
            "type": "command",
            "cmd": "set_removal",
            "params": {
                "rules": [
                    { "stat_index": 0, "threshold": 0.0, "condition": "LessThanEqual" }
                ]
            }
        });
        tx.send(cmd.to_string()).unwrap();
        app.update();
        let rem_rules = app
            .world()
            .get_resource::<crate::rules::RemovalRuleSet>()
            .unwrap();
        assert_eq!(rem_rules.rules.len(), 1);
        assert_eq!(rem_rules.rules[0].stat_index, 0);
        assert_eq!(rem_rules.rules[0].threshold, 0.0);
    }
}
