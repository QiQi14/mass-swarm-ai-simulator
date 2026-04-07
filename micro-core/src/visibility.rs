//! # Faction Visibility
//!
//! Per-faction fog of war state — bit-packed, self-contained resource.
//! Works without the debug visualizer. ML brain reads this via ZMQ.
//!
//! ## Ownership
//! - **Task:** task_10_faction_visibility
//! - **Contract:** implementation_plan.md → Feature 2: Fog of War
//!
//! ## Bit-Packing
//! Grid is stored as `Vec<u32>` — each u32 holds 32 cells.
//! 50×50 grid = 2,500 cells = 79 integers per faction.
//!
//! ## Depends On
//! - `crate::components::{Position, FactionId, VisionRadius}`

use bevy::prelude::*;
use std::collections::HashMap;

#[derive(Resource, Debug, Clone)]
pub struct FactionVisibility {
    pub grid_width: u32,
    pub grid_height: u32,
    pub cell_size: f32,
    /// explored[faction_id] = bit-packed grid of EVER-seen cells
    pub explored: HashMap<u32, Vec<u32>>,
    /// visible[faction_id] = bit-packed grid of CURRENTLY-seen cells
    pub visible: HashMap<u32, Vec<u32>>,
}

impl FactionVisibility {
    pub fn bitpack_len(grid_width: u32, grid_height: u32) -> usize {
        ((grid_width * grid_height) as usize).div_ceil(32)
    }

    pub fn set_bit(grid: &mut [u32], index: usize) {
        grid[index / 32] |= 1 << (index % 32);
    }

    pub fn get_bit(grid: &[u32], index: usize) -> bool {
        (grid[index / 32] >> (index % 32)) & 1 == 1
    }

    pub fn clear_all(grid: &mut [u32]) {
        grid.iter_mut().for_each(|v| *v = 0);
    }

    pub fn new(grid_width: u32, grid_height: u32, cell_size: f32) -> Self {
        Self {
            grid_width,
            grid_height,
            cell_size,
            explored: HashMap::default(),
            visible: HashMap::default(),
        }
    }

    pub fn ensure_faction(&mut self, faction_id: u32) {
        let size = Self::bitpack_len(self.grid_width, self.grid_height);
        self.explored
            .entry(faction_id)
            .or_insert_with(|| vec![0; size]);
        self.visible
            .entry(faction_id)
            .or_insert_with(|| vec![0; size]);
    }

    pub fn reset_explored(&mut self) {
        for grid in self.explored.values_mut() {
            Self::clear_all(grid);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::components::VisionRadius;

    #[test]
    fn test_bitpack_len_50x50() {
        assert_eq!(FactionVisibility::bitpack_len(50, 50), 79);
    }

    #[test]
    fn test_bitpack_len_edge_case_32() {
        assert_eq!(FactionVisibility::bitpack_len(4, 8), 1);
    }

    #[test]
    fn test_set_get_bit_roundtrip() {
        let mut grid = vec![0u32; FactionVisibility::bitpack_len(50, 50)];
        FactionVisibility::set_bit(&mut grid, 0);
        FactionVisibility::set_bit(&mut grid, 31);
        FactionVisibility::set_bit(&mut grid, 32);
        FactionVisibility::set_bit(&mut grid, 2499);

        assert!(FactionVisibility::get_bit(&grid, 0));
        assert!(FactionVisibility::get_bit(&grid, 31));
        assert!(FactionVisibility::get_bit(&grid, 32));
        assert!(FactionVisibility::get_bit(&grid, 2499));

        // check intermediate
        assert!(!FactionVisibility::get_bit(&grid, 1));
        assert!(!FactionVisibility::get_bit(&grid, 30));
        assert!(!FactionVisibility::get_bit(&grid, 33));
        assert!(!FactionVisibility::get_bit(&grid, 2498));
    }

    #[test]
    fn test_clear_all_zeros_grid() {
        let mut grid = vec![u32::MAX; 79];
        FactionVisibility::clear_all(&mut grid);
        for &val in grid.iter() {
            assert_eq!(val, 0);
        }
    }

    #[test]
    fn test_ensure_faction_creates_grids() {
        let mut vis = FactionVisibility::new(50, 50, 20.0);
        vis.ensure_faction(0);
        assert!(vis.explored.contains_key(&0));
        assert!(vis.visible.contains_key(&0));
        assert_eq!(vis.explored.get(&0).unwrap().len(), 79);
        assert_eq!(vis.visible.get(&0).unwrap().len(), 79);
    }

    #[test]
    fn test_ensure_faction_idempotent() {
        let mut vis = FactionVisibility::new(50, 50, 20.0);
        vis.ensure_faction(0);
        FactionVisibility::set_bit(vis.explored.get_mut(&0).unwrap(), 10);

        // second call should not reset
        vis.ensure_faction(0);
        assert!(FactionVisibility::get_bit(
            vis.explored.get(&0).unwrap(),
            10
        ));
    }

    #[test]
    fn test_reset_explored_clears_all_factions() {
        let mut vis = FactionVisibility::new(50, 50, 20.0);
        vis.ensure_faction(0);
        vis.ensure_faction(1);
        vis.ensure_faction(2);

        FactionVisibility::set_bit(vis.explored.get_mut(&0).unwrap(), 10);
        FactionVisibility::set_bit(vis.explored.get_mut(&1).unwrap(), 20);
        FactionVisibility::set_bit(vis.explored.get_mut(&2).unwrap(), 30);

        vis.reset_explored();

        assert!(!FactionVisibility::get_bit(
            vis.explored.get(&0).unwrap(),
            10
        ));
        assert!(!FactionVisibility::get_bit(
            vis.explored.get(&1).unwrap(),
            20
        ));
        assert!(!FactionVisibility::get_bit(
            vis.explored.get(&2).unwrap(),
            30
        ));
    }

    #[test]
    fn test_vision_radius_default() {
        assert_eq!(VisionRadius::default().0, 80.0);
    }
}
