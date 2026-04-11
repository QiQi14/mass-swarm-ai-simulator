//! # State Vectorizer
//!
//! Compresses 10,000+ entity positions into fixed-size spatial heatmaps.
//! Produces one density channel per faction (including sub-factions).
//!
//! ## Responsibility Boundary
//! This module produces RAW density data as HashMap<faction_id, Vec<f32>>.
//! It does NOT pack data into fixed NN channels — that is Python's job.
//!
//! ## Algorithm
//! 1. Iterate all entities with Position + FactionId
//! 2. Map world position → grid cell: floor(pos / cell_size)
//! 3. Increment cell counter for that faction
//! 4. Normalize: cell_value / max_density (configurable)
//!
//! ## Ownership
//! - **Task:** task_03_state_vectorizer

use std::collections::HashMap;

/// Default maximum density for normalization.
/// Cells with more entities than this are clamped to 1.0.
pub const DEFAULT_MAX_DENSITY: f32 = 50.0;

/// Builds density heatmaps from entity positions.
///
/// Returns a HashMap where each key is a faction_id and each value
/// is a flat Vec<f32> of size (grid_w × grid_h), row-major order.
/// Values are normalized to [0.0, 1.0].
///
/// Sub-factions (created by SplitFaction) automatically get their own
/// density channel — no special handling needed.
pub fn build_density_maps(
    entities: &[(f32, f32, u32)],
    grid_w: u32,
    grid_h: u32,
    cell_size: f32,
    max_density: f32,
) -> HashMap<u32, Vec<f32>> {
    let total_cells = (grid_w * grid_h) as usize;
    let mut count_maps: HashMap<u32, Vec<u32>> = HashMap::new();

    for &(x, y, faction) in entities {
        let cx = (x / cell_size).floor() as i32;
        let cy = (y / cell_size).floor() as i32;

        if cx < 0 || cx >= grid_w as i32 || cy < 0 || cy >= grid_h as i32 {
            continue;
        }

        let idx = (cy as u32 * grid_w + cx as u32) as usize;
        let counts = count_maps
            .entry(faction)
            .or_insert_with(|| vec![0u32; total_cells]);
        counts[idx] += 1;
    }

    count_maps
        .into_iter()
        .map(|(faction, counts)| {
            let normalized: Vec<f32> = counts
                .iter()
                .map(|&c| (c as f32 / max_density).min(1.0))
                .collect();
            (faction, normalized)
        })
        .collect()
}

/// Builds Effective Combat Power (ECP) density heatmaps.
///
/// Each cell value = sum(entity_hp * entity_damage_mult) / max_ecp_per_cell
/// clamped to [0.0, 1.0].
///
/// ECP captures both survivability (HP) and damage output (buff multiplier).
/// Tankers (high HP, low DPS) produce moderate ECP.
/// Glass cannons (low HP, high DPS) produce moderate ECP.
/// Debuffed units (low HP * 0.25 mult) produce very low ECP.
pub fn build_ecp_density_maps(
    entities: &[(f32, f32, u32, f32, f32)], // (x, y, faction_id, hp, damage_mult)
    grid_w: u32,
    grid_h: u32,
    cell_size: f32,
    max_ecp_per_cell: f32,
) -> HashMap<u32, Vec<f32>> {
    let total_cells = (grid_w * grid_h) as usize;
    let mut ecp_maps: HashMap<u32, Vec<f32>> = HashMap::new();

    for &(x, y, faction, hp, damage_mult) in entities {
        let cx = (x / cell_size).floor() as i32;
        let cy = (y / cell_size).floor() as i32;

        if cx < 0 || cx >= grid_w as i32 || cy < 0 || cy >= grid_h as i32 {
            continue;
        }

        let idx = (cy as u32 * grid_w + cx as u32) as usize;
        let ecps = ecp_maps
            .entry(faction)
            .or_insert_with(|| vec![0.0; total_cells]);
        ecps[idx] += hp * damage_mult;
    }

    ecp_maps
        .into_iter()
        .map(|(faction, ecps)| {
            let normalized: Vec<f32> = ecps
                .iter()
                .map(|&ecp| (ecp / max_ecp_per_cell).min(1.0))
                .collect();
            (faction, normalized)
        })
        .collect()
}

/// Builds summary statistics from entity data.
///
/// Returns (own_count, enemy_count, own_avg_stat0, enemy_avg_stat0)
/// normalized to [0.0, 1.0] for NN input.
pub fn build_summary_stats(
    entities: &[(f32, f32, u32, f32)],
    brain_faction: u32,
    max_entities: f32,
) -> [f32; 4] {
    let mut own_count = 0u32;
    let mut enemy_count = 0u32;
    let mut own_stat_sum = 0.0f32;
    let mut enemy_stat_sum = 0.0f32;

    for &(_, _, faction, stat0) in entities {
        if faction == brain_faction {
            own_count += 1;
            own_stat_sum += stat0;
        } else {
            enemy_count += 1;
            enemy_stat_sum += stat0;
        }
    }

    [
        (own_count as f32 / max_entities).min(1.0),
        (enemy_count as f32 / max_entities).min(1.0),
        if own_count > 0 {
            own_stat_sum / own_count as f32
        } else {
            0.0
        },
        if enemy_count > 0 {
            enemy_stat_sum / enemy_count as f32
        } else {
            0.0
        },
    ]
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_density_map_single_entity() {
        // Arrange
        let entities = vec![(15.0, 25.0, 0)]; // cell size 10 -> cx = 1, cy = 2. idx = 2 * 10 + 1 = 21. grid_w = 10, grid_h = 10
        let grid_w = 10;
        let grid_h = 10;
        let cell_size = 10.0;
        let max_density = 50.0;

        // Act
        let maps = build_density_maps(&entities, grid_w, grid_h, cell_size, max_density);

        // Assert
        assert!(maps.contains_key(&0), "Map should contain faction 0");
        let map = &maps[&0];
        assert_eq!(map.len(), 100, "Map size should be 100");
        assert!(
            (map[21] - (1.0 / 50.0)).abs() < f32::EPSILON,
            "Cell 21 density incorrect"
        );
        assert!(
            (map[22] - 0.0).abs() < f32::EPSILON,
            "Cell 22 density should be 0"
        );
    }

    #[test]
    fn test_density_map_multiple_factions() {
        // Arrange
        let entities = vec![(15.0, 25.0, 0), (25.0, 35.0, 1)];

        // Act
        let maps = build_density_maps(&entities, 10, 10, 10.0, 50.0);

        // Assert
        assert_eq!(maps.len(), 2, "Should have 2 faction maps");
        assert!(maps.contains_key(&0), "Map should contain faction 0");
        assert!(maps.contains_key(&1), "Map should contain faction 1");
    }

    #[test]
    fn test_density_map_sub_faction() {
        // Arrange
        let entities = vec![(15.0, 25.0, 101)];

        // Act
        let maps = build_density_maps(&entities, 10, 10, 10.0, 50.0);

        // Assert
        assert!(
            maps.contains_key(&101),
            "Map should contain sub-faction 101"
        );
    }

    #[test]
    fn test_density_map_normalization() {
        // Arrange
        let mut entities = Vec::new();
        for _ in 0..50 {
            entities.push((15.0, 25.0, 0));
        }

        // Act
        let maps = build_density_maps(&entities, 10, 10, 10.0, 50.0);

        // Assert
        let map = &maps[&0];
        assert!(
            (map[21] - 1.0).abs() < f32::EPSILON,
            "50 entities should normalize to 1.0"
        );
    }

    #[test]
    fn test_density_map_clamping() {
        // Arrange
        let mut entities = Vec::new();
        for _ in 0..100 {
            entities.push((15.0, 25.0, 0));
        }

        // Act
        let maps = build_density_maps(&entities, 10, 10, 10.0, 50.0);

        // Assert
        let map = &maps[&0];
        assert!(
            (map[21] - 1.0).abs() < f32::EPSILON,
            "100 entities should clamp to 1.0"
        );
    }

    #[test]
    fn test_density_map_out_of_bounds_ignored() {
        // Arrange
        let entities = vec![
            (-15.0, -25.0, 0),
            (115.0, 125.0, 0),
            (5.0, 5.0, 0), // Valid Entity
        ];

        // Act
        let maps = build_density_maps(&entities, 10, 10, 10.0, 50.0);

        // Assert
        let map = &maps[&0];
        assert!(
            (map[0] - (1.0 / 50.0)).abs() < f32::EPSILON,
            "Only valid entity should be counted"
        );
    }

    #[test]
    fn test_density_map_empty_entities() {
        // Arrange
        let entities: Vec<(f32, f32, u32)> = Vec::new();

        // Act
        let maps = build_density_maps(&entities, 10, 10, 10.0, 50.0);

        // Assert
        assert!(maps.is_empty(), "Map should be empty");
    }

    #[test]
    fn test_density_map_grid_boundaries() {
        // Arrange
        let entities = vec![
            (99.9, 99.9, 0),   // In bounds, idx = 9 * 10 + 9 = 99
            (100.0, 100.0, 0), // Out of bounds
        ];

        // Act
        let maps = build_density_maps(&entities, 10, 10, 10.0, 50.0);

        // Assert
        let map = &maps[&0];
        assert!(
            (map[99] - (1.0 / 50.0)).abs() < f32::EPSILON,
            "Boundary edge should be computed correctly"
        );
        // Ensure no panic, and 100.0 is skipped
    }

    #[test]
    fn test_summary_stats_basic() {
        // Arrange
        let entities = vec![
            (0.0, 0.0, 0, 100.0), // Faction 0, health 100
            (0.0, 0.0, 0, 80.0),  // Faction 0, health 80
            (0.0, 0.0, 1, 50.0),  // Enemy, health 50
        ];
        let max_entities = 10.0;

        // Act
        let stats = build_summary_stats(&entities, 0, max_entities);

        // Assert
        assert!(
            (stats[0] - 0.2).abs() < f32::EPSILON,
            "Own count norm expected 0.2"
        );
        assert!(
            (stats[1] - 0.1).abs() < f32::EPSILON,
            "Enemy count norm expected 0.1"
        );
        assert!(
            (stats[2] - 90.0).abs() < f32::EPSILON,
            "Own avg health expected 90.0"
        );
        assert!(
            (stats[3] - 50.0).abs() < f32::EPSILON,
            "Enemy avg health expected 50.0"
        );
    }

    #[test]
    fn test_summary_stats_empty() {
        // Arrange
        let entities: Vec<(f32, f32, u32, f32)> = Vec::new();

        // Act
        let stats = build_summary_stats(&entities, 0, 10.0);

        // Assert
        assert_eq!(
            stats,
            [0.0, 0.0, 0.0, 0.0],
            "Empty stats should return array of zero floats"
        );
    }

    #[test]
    fn test_ecp_density_single_entity() {
        // Arrange
        let entities = vec![
            (15.0, 15.0, 0, 80.0, 1.0), // Faction 0
        ];
        let max_ecp = 1000.0;

        // Act
        let maps = build_ecp_density_maps(&entities, 10, 10, 10.0, max_ecp);

        // Assert
        let map = &maps[&0];
        assert!(
            (map[11] - (80.0 / 1000.0)).abs() < f32::EPSILON,
            "ECP should be hp * mult / max_ecp"
        );
    }

    #[test]
    fn test_ecp_density_tanker_vs_glass_cannon() {
        // Arrange
        let entities = vec![
            (15.0, 15.0, 0, 100.0, 1.0),   // Tanker (100 ECP)
            (25.0, 15.0, 1, 20.0, 5.0),    // Glass Cannon (100 ECP)
        ];
        let max_ecp = 1000.0;

        // Act
        let maps = build_ecp_density_maps(&entities, 10, 10, 10.0, max_ecp);

        // Assert
        assert!(
            (maps[&0][11] - 0.1).abs() < f32::EPSILON,
            "Tanker ECP norm should be 0.1"
        );
        assert!(
            (maps[&1][12] - 0.1).abs() < f32::EPSILON,
            "Glass Cannon ECP norm should be 0.1"
        );
    }

    #[test]
    fn test_ecp_density_debuffed_units() {
        // Arrange
        let entities = vec![
            (15.0, 15.0, 0, 50.0, 1.0),   // Normal (50 ECP)
            (25.0, 15.0, 1, 50.0, 0.25),  // Debuffed (12.5 ECP)
        ];
        let max_ecp = 100.0;

        // Act
        let maps = build_ecp_density_maps(&entities, 10, 10, 10.0, max_ecp);

        // Assert
        assert!(
            (maps[&0][11] - 0.5).abs() < f32::EPSILON,
            "Normal unit ECP norm should be 0.5"
        );
        assert!(
            (maps[&1][12] - 0.125).abs() < f32::EPSILON,
            "Debuffed unit ECP norm should be 0.125"
        );
    }

    #[test]
    fn test_ecp_density_normalization() {
        // Arrange
        let entities = vec![
            (15.0, 15.0, 0, 2000.0, 2.0), // 4000 ECP
        ];
        let max_ecp = 1000.0;

        // Act
        let maps = build_ecp_density_maps(&entities, 10, 10, 10.0, max_ecp);

        // Assert
        assert!(
            (maps[&0][11] - 1.0).abs() < f32::EPSILON,
            "Values exceeding max_ecp should be clamped to 1.0"
        );
    }
}
