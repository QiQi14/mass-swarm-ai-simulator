//! # State Snapshot Builder
//!
//! Constructs `StateSnapshot` from the current ECS state for ZMQ transmission.
//!
//! ## Ownership
//! - **Task:** task_r1_split_zmq_systems
//! - **Contract:** implementation_plan.md → Task R1

use bevy::prelude::*;

use crate::bridges::zmq_protocol::{
    EntitySnapshot, StateSnapshot, SummarySnapshot, WorldSize, ZoneModifierSnapshot,
};
use crate::components::{EntityId, FactionId, Position, StatBlock};
use crate::config::{
    ActiveSubFactions, ActiveZoneModifiers, AggroMaskRegistry, DensityConfig, InterventionTracker,
    SimulationConfig, TickCounter, FactionBuffs, BuffConfig,
};
use crate::systems::state_vectorizer::{DEFAULT_MAX_DENSITY, build_density_maps, build_ecp_density_maps};
use crate::terrain::TerrainGrid;
use crate::visibility::FactionVisibility;

/// Builds a StateSnapshot from the current ECS state.
///
/// Queries all entities with EntityId, Position, FactionId, and StatBlock components
/// and packages them into the IPC-compatible StateSnapshot format.
/// Populates density maps from entity positions, intervention flags,
/// zone modifier snapshots, active sub-factions, and aggro mask states.
///
/// # Arguments
/// * `tick` - Current simulation tick
/// * `sim_config` - World dimensions for the world_size field
/// * `query` - All entities with EntityId, Position, FactionId, and StatBlock
/// * `visibility` - Fog-of-war visibility grids
/// * `terrain` - Terrain cost grids
/// * `brain_faction` - Faction ID of the ML brain
/// * `zones` - Active zone modifiers for snapshot feedback
/// * `intervention` - Tier 1 engine override activity tracker
/// * `sub_factions` - Currently active sub-factions
/// * `aggro` - Aggro mask registry for faction-pair combat control
/// * `density_config` - Density/ECP normalization configuration
#[allow(clippy::too_many_arguments)]
pub(super) fn build_state_snapshot(
    tick: &TickCounter,
    sim_config: &SimulationConfig,
    query: &Query<(&EntityId, &Position, &FactionId, &StatBlock, &crate::components::UnitClassId)>,
    visibility: &FactionVisibility,
    terrain: &TerrainGrid,
    brain_faction: u32,
    zones: &ActiveZoneModifiers,
    intervention: &InterventionTracker,
    sub_factions: &ActiveSubFactions,
    aggro: &AggroMaskRegistry,
    combat_buffs: &FactionBuffs,
    buff_config: &BuffConfig,
    density_config: &DensityConfig,
) -> StateSnapshot {
    let mut faction_counts = std::collections::HashMap::new();
    let mut faction_sum_stats: std::collections::HashMap<u32, Vec<f32>> =
        std::collections::HashMap::new();
    let mut entities = Vec::new();

    // Collect ALL entity positions for density map computation (unfiltered)
    let mut all_entity_positions: Vec<(f32, f32, u32)> = Vec::new();
    let mut all_entity_ecp: Vec<(f32, f32, u32, f32, f32)> = Vec::new();

    let vis_grid = visibility.visible.get(&brain_faction);
    let exp_grid = visibility.explored.get(&brain_faction);

    for (eid, pos, faction, stat_block, unit_class) in query.iter() {
        let count = faction_counts.entry(faction.0).or_insert(0);
        *count += 1;

        let sums = faction_sum_stats
            .entry(faction.0)
            .or_insert_with(|| vec![0.0; crate::components::MAX_STATS]);
        for (i, &val) in stat_block.0.iter().enumerate() {
            sums[i] += val;
        }

        // Density maps use ALL entities (not fog-filtered) so the brain
        // has complete spatial awareness of its own forces
        all_entity_positions.push((pos.x, pos.y, faction.0));
        
        // Read primary stat for ECP from configurable index (V-01 fix)
        // Feature 2: Multi-stat formula for ECP
        let primary_stat = if let Some(ref formula) = density_config.ecp_formula {
            formula.iter()
                .map(|&idx| stat_block.0.get(idx).copied().unwrap_or(1.0))
                .product::<f32>()
        } else {
            density_config.ecp_stat_index
                .and_then(|idx| stat_block.0.get(idx).copied())
                .unwrap_or(0.0)
        };
        let damage_mult = buff_config.combat_damage_stat
            .map(|stat_idx| combat_buffs.get_multiplier(faction.0, eid.id, stat_idx))
            .unwrap_or(1.0);
        all_entity_ecp.push((pos.x, pos.y, faction.0, primary_stat, damage_mult));

        // Entity list is fog-filtered: own faction always visible, enemies only if in visible cells
        let mut is_visible = false;
        if faction.0 == brain_faction {
            is_visible = true;
        } else if let Some(vg) = vis_grid {
            let cx = (pos.x / visibility.cell_size).floor() as i32;
            let cy = (pos.y / visibility.cell_size).floor() as i32;
            if cx >= 0
                && cx < visibility.grid_width as i32
                && cy >= 0
                && cy < visibility.grid_height as i32
            {
                let cell_idx = (cy as u32 * visibility.grid_width + cx as u32) as usize;
                if FactionVisibility::get_bit(vg, cell_idx) {
                    is_visible = true;
                }
            }
        }

        if is_visible {
            entities.push(EntitySnapshot {
                id: eid.id,
                x: pos.x,
                y: pos.y,
                faction_id: faction.0,
                stats: stat_block.0.to_vec(),
                unit_class_id: unit_class.0,
            });
        }
    }

    let mut faction_avg_stats: std::collections::HashMap<u32, Vec<f32>> =
        std::collections::HashMap::new();
    for (&fid, count) in &faction_counts {
        if let Some(sums) = faction_sum_stats.get(&fid) {
            let avgs: Vec<f32> = sums.iter().map(|s| s / (*count as f32)).collect();
            faction_avg_stats.insert(fid, avgs);
        }
    }

    // Raw density maps — HashMap<faction_id, Vec<f32>>
    // Sub-factions automatically get their own key
    let density_maps = build_density_maps(
        &all_entity_positions,
        terrain.width,
        terrain.height,
        terrain.cell_size,
        DEFAULT_MAX_DENSITY,
    );

    let ecp_density_maps = build_ecp_density_maps(
        &all_entity_ecp,
        terrain.width,
        terrain.height,
        terrain.cell_size,
        density_config.max_density * density_config.max_entity_ecp,
    );

    // Zone modifier snapshots for observation feedback
    let active_zones: Vec<ZoneModifierSnapshot> = zones
        .zones
        .iter()
        .map(|z| ZoneModifierSnapshot {
            target_faction: z.target_faction,
            x: z.x,
            y: z.y,
            radius: z.radius,
            cost_modifier: z.cost_modifier,
            ticks_remaining: z.ticks_remaining,
        })
        .collect();

    // Aggro mask serialization: (source, target) → "source_target" key
    let aggro_masks: std::collections::HashMap<String, bool> = aggro
        .masks
        .iter()
        .map(|(&(s, t), &v)| (format!("{}_{}", s, t), v))
        .collect();

    StateSnapshot {
        msg_type: "state_snapshot".to_string(),
        tick: tick.tick,
        world_size: WorldSize {
            w: sim_config.world_width,
            h: sim_config.world_height,
        },
        entities,
        summary: SummarySnapshot {
            faction_counts,
            faction_avg_stats,
        },
        explored: exp_grid.cloned(),
        visible: vis_grid.cloned(),
        fog_explored: None,
        fog_visible: None,
        terrain_hard: terrain.hard_costs.clone(),
        terrain_soft: terrain.soft_costs.clone(),
        terrain_grid_w: terrain.width,
        terrain_grid_h: terrain.height,
        terrain_cell_size: terrain.cell_size,
        density_maps,
        ecp_density_maps,
        intervention_active: intervention.active,
        active_zones,
        active_sub_factions: sub_factions.factions.clone(),
        aggro_masks,
    }
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[derive(Resource)]
    struct CapturedSnapshot(Option<StateSnapshot>);

    fn capture_snapshot_system(
        tick: Res<TickCounter>,
        sim_config: Res<SimulationConfig>,
        visibility: Res<FactionVisibility>,
        terrain: Res<TerrainGrid>,
        zones: Res<ActiveZoneModifiers>,
        intervention: Res<InterventionTracker>,
        sub_factions: Res<ActiveSubFactions>,
        aggro: Res<AggroMaskRegistry>,
        combat_buffs: Res<FactionBuffs>,
        buff_config: Res<BuffConfig>,
        density_config: Res<DensityConfig>,
        query: Query<(&EntityId, &Position, &FactionId, &StatBlock, &crate::components::UnitClassId)>,
        mut captured: ResMut<CapturedSnapshot>,
    ) {
        captured.0 = Some(build_state_snapshot(
            &tick,
            &sim_config,
            &query,
            &visibility,
            &terrain,
            0,
            &zones,
            &intervention,
            &sub_factions,
            &aggro,
            &combat_buffs,
            &buff_config,
            &density_config,
        ));
    }

    /// Helper to build a minimal app for snapshot tests.
    fn snapshot_test_app() -> App {
        let mut app = App::new();
        app.insert_resource(SimulationConfig::default());
        app.insert_resource(TickCounter { tick: 30 });
        app.insert_resource(FactionVisibility::new(5, 5, 20.0));
        app.insert_resource(TerrainGrid::new(5, 5, 20.0));
        app.insert_resource(ActiveZoneModifiers::default());
        app.insert_resource(InterventionTracker::default());
        app.insert_resource(ActiveSubFactions::default());
        app.insert_resource(AggroMaskRegistry::default());
        app.insert_resource(FactionBuffs::default());
        app.init_resource::<BuffConfig>();
        app.init_resource::<DensityConfig>();
        app.insert_resource(CapturedSnapshot(None));
        app.add_systems(Update, capture_snapshot_system);
        app
    }

    #[test]
    fn test_snapshot_always_includes_own_entities() {
        // Arrange
        let mut app = snapshot_test_app();
        let mut vis = FactionVisibility::new(5, 5, 20.0);
        vis.ensure_faction(0);
        // Fog is black (no visible cells)
        app.insert_resource(vis);

        app.world_mut().spawn((
            EntityId { id: 10 },
            Position { x: 10.0, y: 10.0 },
            FactionId(0),
            StatBlock::default(), crate::components::UnitClassId::default(),
        ));

        // Act
        app.update();

        // Assert
        let snap = app
            .world()
            .resource::<CapturedSnapshot>()
            .0
            .as_ref()
            .unwrap();
        assert_eq!(
            snap.entities.len(),
            1,
            "Should include own entity even if invisible in fog"
        );
        assert_eq!(snap.entities[0].id, 10);
    }

    #[test]
    fn test_snapshot_filters_enemies_by_fog() {
        // Arrange
        let mut app = snapshot_test_app();
        let mut vis = FactionVisibility::new(5, 5, 20.0);
        vis.ensure_faction(0);

        // Enemy 1 at (0,0) - make visible
        let vg = vis.visible.get_mut(&0).unwrap();
        FactionVisibility::set_bit(vg, 0); // cell (0,0) is visible

        app.insert_resource(vis);

        // Enemy in visible cell
        app.world_mut().spawn((
            EntityId { id: 20 },
            Position { x: 10.0, y: 10.0 }, // Cell (0,0)
            FactionId(1),                  // Enemy
            StatBlock::default(), crate::components::UnitClassId::default(),
        ));

        // Enemy in fog cell
        app.world_mut().spawn((
            EntityId { id: 21 },
            Position { x: 90.0, y: 90.0 }, // Cell (4,4)
            FactionId(1),                  // Enemy
            StatBlock::default(), crate::components::UnitClassId::default(),
        ));

        // Act
        app.update();

        // Assert
        let snap = app
            .world()
            .resource::<CapturedSnapshot>()
            .0
            .as_ref()
            .unwrap();
        assert_eq!(
            snap.entities.len(),
            1,
            "Should only include visible enemies"
        );
        assert_eq!(
            snap.entities[0].id, 20,
            "Should include enemy at visible cell"
        );
    }

    #[test]
    fn test_snapshot_includes_density_maps() {
        // Arrange
        let mut app = snapshot_test_app();
        // TerrainGrid is 5×5, cell_size=20 → entities at known positions

        app.world_mut().spawn((
            EntityId { id: 1 },
            Position { x: 10.0, y: 10.0 }, // Cell (0,0)
            FactionId(0),
            StatBlock::default(), crate::components::UnitClassId::default(),
        ));

        app.world_mut().spawn((
            EntityId { id: 2 },
            Position { x: 30.0, y: 30.0 }, // Cell (1,1)
            FactionId(1),
            StatBlock::default(), crate::components::UnitClassId::default(),
        ));

        // Act
        app.update();

        // Assert
        let snap = app
            .world()
            .resource::<CapturedSnapshot>()
            .0
            .as_ref()
            .unwrap();
        assert!(
            snap.density_maps.contains_key(&0),
            "Density maps should contain faction 0"
        );
        assert!(
            snap.density_maps.contains_key(&1),
            "Density maps should contain faction 1"
        );
        // Verify faction 0 has correct density at cell (0,0) = index 0
        let f0_map = &snap.density_maps[&0];
        assert_eq!(f0_map.len(), 25, "5×5 grid = 25 cells");
        assert!(
            f0_map[0] > 0.0,
            "Entity at (10,10) should produce density at cell (0,0)"
        );
    }

    #[test]
    fn test_snapshot_sub_faction_density() {
        // Arrange
        let mut app = snapshot_test_app();

        app.world_mut().spawn((
            EntityId { id: 1 },
            Position { x: 10.0, y: 10.0 },
            FactionId(101), // Sub-faction
            StatBlock::default(), crate::components::UnitClassId::default(),
        ));

        // Act
        app.update();

        // Assert
        let snap = app
            .world()
            .resource::<CapturedSnapshot>()
            .0
            .as_ref()
            .unwrap();
        assert!(
            snap.density_maps.contains_key(&101),
            "Sub-faction 101 should have its own density map key"
        );
    }

    #[test]
    fn test_snapshot_intervention_flag() {
        // Arrange — intervention active
        let mut app = snapshot_test_app();
        app.insert_resource(InterventionTracker { active: true });

        app.world_mut().spawn((
            EntityId { id: 1 },
            Position { x: 10.0, y: 10.0 },
            FactionId(0),
            StatBlock::default(), crate::components::UnitClassId::default(),
        ));

        // Act
        app.update();

        // Assert
        let snap = app
            .world()
            .resource::<CapturedSnapshot>()
            .0
            .as_ref()
            .unwrap();
        assert!(
            snap.intervention_active,
            "Snapshot should reflect intervention_active = true"
        );
    }

    #[test]
    fn test_snapshot_active_zones() {
        // Arrange
        let mut app = snapshot_test_app();
        let mut zones = ActiveZoneModifiers::default();
        zones.zones.push(crate::config::ZoneModifier {
            target_faction: 0,
            x: 50.0,
            y: 50.0,
            radius: 100.0,
            cost_modifier: -50.0,
            ticks_remaining: 60,
        });
        app.insert_resource(zones);

        app.world_mut().spawn((
            EntityId { id: 1 },
            Position { x: 10.0, y: 10.0 },
            FactionId(0),
            StatBlock::default(), crate::components::UnitClassId::default(),
        ));

        // Act
        app.update();

        // Assert
        let snap = app
            .world()
            .resource::<CapturedSnapshot>()
            .0
            .as_ref()
            .unwrap();
        assert_eq!(
            snap.active_zones.len(),
            1,
            "Snapshot should contain 1 active zone"
        );
        assert_eq!(snap.active_zones[0].target_faction, 0);
        assert!((snap.active_zones[0].cost_modifier - (-50.0)).abs() < f32::EPSILON);
        assert_eq!(snap.active_zones[0].ticks_remaining, 60);
    }

    #[test]
    fn test_snapshot_aggro_masks_serialization() {
        // Arrange
        let mut app = snapshot_test_app();
        let mut aggro = AggroMaskRegistry::default();
        aggro.masks.insert((0, 1), false);
        aggro.masks.insert((1, 0), false);
        app.insert_resource(aggro);

        app.world_mut().spawn((
            EntityId { id: 1 },
            Position { x: 10.0, y: 10.0 },
            FactionId(0),
            StatBlock::default(), crate::components::UnitClassId::default(),
        ));

        // Act
        app.update();

        // Assert
        let snap = app
            .world()
            .resource::<CapturedSnapshot>()
            .0
            .as_ref()
            .unwrap();
        assert!(
            snap.aggro_masks.contains_key("0_1"),
            "Aggro mask should contain key '0_1'"
        );
        assert!(!snap.aggro_masks["0_1"], "Aggro mask 0→1 should be false");
        assert!(
            snap.aggro_masks.contains_key("1_0"),
            "Aggro mask should contain key '1_0'"
        );
    }
}
