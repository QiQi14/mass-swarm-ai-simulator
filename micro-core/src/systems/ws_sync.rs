//! # WebSocket Sync System
//!
//! Bridges the synchronous Bevy world to the async Tokio world.
//! Extracts changed entities and broadcasts state updates to connected WebSocket clients.
//!
//! ## Ownership
//! - **Task:** task_03_ws_sync_system
//! - **Contract:** Phase 1, Micro-Phase 2 WebSocket Message Schema

#[cfg(feature = "debug-telemetry")]
use crate::bridges::ws_protocol::{AggroMaskSync, MlBrainSync, VisibilitySync, ZoneModifierSync};
use crate::bridges::ws_protocol::{EntityState, WsMessage};
use crate::components::{EntityId, FactionId, Position, StatBlock, Velocity};
use crate::config::TickCounter;
use crate::rules::RemovalEvents;
#[cfg(feature = "debug-telemetry")]
use crate::visibility::FactionVisibility;
use bevy::prelude::*;
use tokio::sync::broadcast::Sender;

#[cfg(feature = "debug-telemetry")]
use crate::plugins::telemetry::PerfTelemetry;

/// Resource wrapping the async broadcast sender.
#[derive(Resource, Clone)]
pub struct BroadcastSender(pub Sender<String>);

/// Extracts entities that have moved and sends a state synchronization message
/// to the async broadcast channel.
///
/// Every 60 ticks (~1 second), broadcasts a FULL snapshot of all entity positions.
/// On all other ticks, broadcasts only entities whose Position changed (delta sync).
/// This ensures late-connecting WS clients always get a complete picture.
/// Bundles all debug-telemetry resources for `ws_sync_system` to stay
/// under Bevy's 16-param limit.
#[cfg(feature = "debug-telemetry")]
#[derive(bevy::ecs::system::SystemParam)]
pub struct WsSyncTelemetry<'w> {
    pub fog_faction: Res<'w, crate::systems::ws_command::ActiveFogFaction>,
    pub visibility: Res<'w, FactionVisibility>,
    pub telemetry: Option<ResMut<'w, PerfTelemetry>>,
    pub active_zones: Option<Res<'w, crate::config::ActiveZoneModifiers>>,
    pub active_sub_factions_res: Option<Res<'w, crate::config::ActiveSubFactions>>,
    pub aggro_masks_res: Option<Res<'w, crate::config::AggroMaskRegistry>>,
    pub intervention_tracker: Option<Res<'w, crate::config::InterventionTracker>>,
    pub config: Option<Res<'w, crate::config::SimulationConfig>>,
    pub density_config: Option<Res<'w, crate::config::DensityConfig>>,
    pub latest_directive: Option<Res<'w, crate::systems::directive_executor::LatestDirective>>,
    pub combat_buffs: Option<Res<'w, crate::config::FactionBuffs>>,
    pub buff_config: Option<Res<'w, crate::config::BuffConfig>>,
}

#[allow(clippy::too_many_arguments)]
pub fn ws_sync_system(
    changed_query: Query<
        (&EntityId, &Position, &Velocity, &FactionId, &StatBlock),
        Or<(Changed<Position>, Changed<Velocity>, Changed<StatBlock>)>,
    >,
    full_query: Query<(&EntityId, &Position, &Velocity, &FactionId, &StatBlock)>,
    tick: Res<TickCounter>,
    sender: Res<BroadcastSender>,
    mut removal_events: ResMut<RemovalEvents>,
    #[cfg(feature = "debug-telemetry")] telem: WsSyncTelemetry<'_>,
) {
    #[cfg(feature = "debug-telemetry")]
    let start = telem.telemetry.as_ref().map(|_| std::time::Instant::now());

    // Every 60 ticks: full snapshot; otherwise delta only
    let is_full_sync = tick.tick.is_multiple_of(60);

    let mut moved = Vec::new();
    if is_full_sync {
        for (id, pos, vel, faction, stat_block) in full_query.iter() {
            moved.push(EntityState {
                id: id.id,
                x: pos.x,
                y: pos.y,
                dx: vel.dx,
                dy: vel.dy,
                faction_id: faction.0,
                stats: stat_block.0.to_vec(),
            });
        }
    } else {
        for (id, pos, vel, faction, stat_block) in changed_query.iter() {
            moved.push(EntityState {
                id: id.id,
                x: pos.x,
                y: pos.y,
                dx: vel.dx,
                dy: vel.dy,
                faction_id: faction.0,
                stats: stat_block.0.to_vec(),
            });
        }
    }

    let removed = removal_events.removed_ids.clone();
    removal_events.removed_ids.clear();

    let msg = WsMessage::SyncDelta {
        tick: tick.tick,
        moved,
        removed,
        #[cfg(feature = "debug-telemetry")]
        telemetry: telem.telemetry.as_ref().map(|t| {
            let mut snapshot = (*t).clone();
            snapshot.entity_count = full_query.iter().count() as u32;
            snapshot
        }),
        #[cfg(feature = "debug-telemetry")]
        visibility: if tick.tick.is_multiple_of(6) {
            telem.fog_faction.0.and_then(|fid| {
                let explored = telem.visibility.explored.get(&fid)?;
                let visible = telem.visibility.visible.get(&fid)?;
                Some(VisibilitySync {
                    faction_id: fid,
                    grid_width: telem.visibility.grid_width,
                    grid_height: telem.visibility.grid_height,
                    explored: explored.clone(),
                    visible: visible.clone(),
                })
            })
        } else {
            None
        },
        #[cfg(feature = "debug-telemetry")]
        zone_modifiers: if tick.tick.is_multiple_of(6) {
            telem.active_zones.as_ref().map(|z| {
                z.zones
                    .iter()
                    .map(|zone| ZoneModifierSync {
                        target_faction: zone.target_faction,
                        x: zone.x,
                        y: zone.y,
                        radius: zone.radius,
                        cost_modifier: zone.cost_modifier,
                        ticks_remaining: zone.ticks_remaining,
                    })
                    .collect()
            })
        } else {
            None
        },
        #[cfg(feature = "debug-telemetry")]
        active_sub_factions: if tick.tick.is_multiple_of(6) {
            telem.active_sub_factions_res
                .as_ref()
                .map(|sf| sf.factions.clone())
        } else {
            None
        },
        #[cfg(feature = "debug-telemetry")]
        aggro_masks: if tick.tick.is_multiple_of(6) {
            telem.aggro_masks_res.as_ref().map(|m| {
                let mut masks = std::collections::HashMap::new();
                for (&(src, tgt), &allowed) in &m.masks {
                    masks.insert(format!("{}_{}", src, tgt), allowed);
                }
                AggroMaskSync { masks }
            })
        } else {
            None
        },
        #[cfg(feature = "debug-telemetry")]
        ml_brain: if tick.tick.is_multiple_of(6) {
            telem.intervention_tracker.as_ref().map(|tracker| {
                let py_connected = telem.latest_directive
                    .as_ref()
                    .map(|ld| ld.last_received_tick == u64::MAX || ld.last_directive_json.is_some())
                    .unwrap_or(false);
                let last_dir_str = telem.latest_directive
                    .as_ref()
                    .and_then(|ld| ld.last_directive_json.clone());
                MlBrainSync {
                    intervention_active: tracker.active,
                    python_connected: py_connected,
                    last_directive: last_dir_str,
                }
            })
        } else {
            None
        },
        #[cfg(feature = "debug-telemetry")]
        density_heatmap: if tick.tick.is_multiple_of(6) {
            if let Some(cfg) = &telem.config {
                let grid_w = (cfg.world_width / cfg.flow_field_cell_size).ceil() as u32;
                let grid_h = (cfg.world_height / cfg.flow_field_cell_size).ceil() as u32;
                let mut entities = Vec::new();
                for (_, pos, _, faction, _) in full_query.iter() {
                    entities.push((pos.x, pos.y, faction.0));
                }
                Some(crate::systems::state_vectorizer::build_density_maps(
                    &entities,
                    grid_w,
                    grid_h,
                    cfg.flow_field_cell_size,
                    telem.density_config
                        .as_ref()
                        .map(|dc| dc.max_density)
                        .unwrap_or(50.0),
                ))
            } else {
                None
            }
        } else {
            None
        },
        #[cfg(feature = "debug-telemetry")]
        ecp_density_maps: if tick.tick.is_multiple_of(6) {
            if let Some(cfg) = &telem.config {
                let grid_w = (cfg.world_width / cfg.flow_field_cell_size).ceil() as u32;
                let grid_h = (cfg.world_height / cfg.flow_field_cell_size).ceil() as u32;
                let mut all_entity_ecp = Vec::new();
                
                let cb = telem.combat_buffs.as_deref();
                let bc = telem.buff_config.as_deref();
                
                for (eid, pos, _, faction, stat_block) in full_query.iter() {
                    // Read primary stat for ECP from configurable index (V-01 fix)
                    let primary_stat = telem.density_config
                        .as_ref()
                        .and_then(|dc| dc.ecp_stat_index)
                        .and_then(|idx| stat_block.0.get(idx).copied())
                        .unwrap_or(0.0);
                    let damage_mult = bc.and_then(|config| {
                        config.combat_damage_stat.map(|stat_idx| {
                            cb.map(|buffs| buffs.get_multiplier(faction.0, eid.id, stat_idx))
                                .unwrap_or(1.0)
                        })
                    }).unwrap_or(1.0);
                    all_entity_ecp.push((pos.x, pos.y, faction.0, primary_stat, damage_mult));
                }
                
                let max_density = telem.density_config
                    .as_ref()
                    .map(|dc| dc.max_density)
                    .unwrap_or(50.0);
                let max_entity_ecp = telem.density_config
                    .as_ref()
                    .map(|dc| dc.max_entity_ecp)
                    .unwrap_or(100.0);
                    
                Some(crate::systems::state_vectorizer::build_ecp_density_maps(
                    &all_entity_ecp,
                    grid_w,
                    grid_h,
                    cfg.flow_field_cell_size,
                    max_density * max_entity_ecp,
                ))
            } else {
                None
            }
        } else {
            None
        },
    };

    if let Ok(json_str) = serde_json::to_string(&msg) {
        // Try to send to connected clients. If no clients exist,
        // the channel returns an error, which we simply ignore.
        let _ = sender.0.send(json_str);
    }

    #[cfg(feature = "debug-telemetry")]
    if let (Some(mut t), Some(s)) = (telem.telemetry, start) {
        t.ws_sync_us = s.elapsed().as_micros() as u32;
    }
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use bevy::app::App;
    use tokio::sync::broadcast;

    #[test]
    fn test_ws_sync_system_broadcasts_changes() {
        // Arrange
        let mut app = App::new();
        let (tx, mut rx) = broadcast::channel::<String>(10);
        app.insert_resource(BroadcastSender(tx));
        app.insert_resource(TickCounter { tick: 42 });
        app.init_resource::<crate::rules::RemovalEvents>();
        #[cfg(feature = "debug-telemetry")]
        app.init_resource::<crate::systems::ws_command::ActiveFogFaction>();
        #[cfg(feature = "debug-telemetry")]
        app.insert_resource(FactionVisibility::new(5, 5, 20.0));
        #[cfg(feature = "debug-telemetry")]
        app.init_resource::<crate::plugins::telemetry::PerfTelemetry>();

        app.add_systems(Update, ws_sync_system);

        app.world_mut().spawn((
            EntityId { id: 100 },
            Position { x: 5.0, y: 10.0 },
            Velocity { dx: 1.5, dy: -2.5 },
            FactionId(0),
            StatBlock::with_defaults(&[(0, 0.8)]),
        ));

        // Act
        app.update();

        // Assert
        let msg = rx.try_recv().expect("Should have received a message");
        assert!(msg.contains(r#""type":"SyncDelta""#));
        assert!(msg.contains(r#""tick":42"#));
        assert!(msg.contains(r#""id":100"#));
        assert!(msg.contains(r#""x":5.0"#));
        assert!(msg.contains(r#""y":10.0"#));
        assert!(msg.contains(r#""dx":1.5"#));
        assert!(msg.contains(r#""dy":-2.5"#));
        assert!(msg.contains(r#""faction_id":0"#));
        assert!(msg.contains(r#""stats":[0.8,0.0,0.0,0.0,0.0,0.0,0.0,0.0]"#));
    }
}
