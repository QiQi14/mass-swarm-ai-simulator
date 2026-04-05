//! # Terrain Grid
//!
//! Paintable terrain weight grid affecting pathfinding and movement.
//! Contract-based — core sees only integers, never named terrain types.
//!
//! ## Ownership
//! - **Task:** task_09_terrain_grid
//! - **Contract:** implementation_plan.md → Feature 3: Terrain Editor
//!
//! ## Dual-Weight Model
//! - `hard_costs`: Dijkstra cost multiplier (scale 100).
//!   100 = normal, 200 = double cost, u16::MAX = impassable wall.
//! - `soft_costs`: Movement speed percentage (0–100).
//!   100 = full speed, 50 = half speed, 0 = stopped.

use bevy::prelude::*;
use serde::{Deserialize, Serialize};

#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct TerrainGrid {
    pub width: u32,
    pub height: u32,
    pub cell_size: f32,
    pub hard_costs: Vec<u16>,
    pub soft_costs: Vec<u16>,
}

impl TerrainGrid {
    pub fn new(width: u32, height: u32, cell_size: f32) -> Self {
        let size = (width * height) as usize;
        Self {
            width,
            height,
            cell_size,
            hard_costs: vec![100u16; size],
            soft_costs: vec![100u16; size],
        }
    }

    pub fn get_hard_cost(&self, cell: IVec2) -> u16 {
        if !self.in_bounds(cell) {
            return u16::MAX;
        }
        self.hard_costs[(cell.y as u32 * self.width + cell.x as u32) as usize]
    }

    pub fn get_soft_cost(&self, cell: IVec2) -> u16 {
        if !self.in_bounds(cell) {
            return 0;
        }
        self.soft_costs[(cell.y as u32 * self.width + cell.x as u32) as usize]
    }

    pub fn set_cell(&mut self, x: u32, y: u32, hard: u16, soft: u16) {
        if x < self.width && y < self.height {
            let idx = (y * self.width + x) as usize;
            self.hard_costs[idx] = hard;
            self.soft_costs[idx] = soft;
        }
    }

    /// Returns cells with hard_cost == u16::MAX as IVec2 obstacles.
    pub fn hard_obstacles(&self) -> Vec<IVec2> {
        let mut obs = Vec::new();
        for y in 0..self.height {
            for x in 0..self.width {
                if self.hard_costs[(y * self.width + x) as usize] == u16::MAX {
                    obs.push(IVec2::new(x as i32, y as i32));
                }
            }
        }
        obs
    }

    fn in_bounds(&self, cell: IVec2) -> bool {
        cell.x >= 0 && cell.x < self.width as i32 && cell.y >= 0 && cell.y < self.height as i32
    }

    pub fn reset(&mut self) {
        for cost in &mut self.hard_costs {
            *cost = 100;
        }
        for cost in &mut self.soft_costs {
            *cost = 100;
        }
    }

    pub fn world_to_cell(&self, x: f32, y: f32) -> IVec2 {
        IVec2::new(
            (x / self.cell_size).floor() as i32,
            (y / self.cell_size).floor() as i32,
        )
    }
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_terrain_default_costs_are_100() {
        // Arrange & Act
        let grid = TerrainGrid::new(5, 5, 20.0);
        
        // Assert
        assert_eq!(grid.hard_costs.len(), 25);
        assert_eq!(grid.soft_costs.len(), 25);
        assert!(grid.hard_costs.iter().all(|&c| c == 100), "All default hard costs should be 100");
        assert!(grid.soft_costs.iter().all(|&c| c == 100), "All default soft costs should be 100");
    }

    #[test]
    fn test_terrain_wall_returns_max() {
        // Arrange
        let mut grid = TerrainGrid::new(5, 5, 20.0);
        
        // Act
        grid.set_cell(2, 2, u16::MAX, 0);

        // Assert
        assert_eq!(grid.get_hard_cost(IVec2::new(2, 2)), u16::MAX, "Hard cost should be u16::MAX");
    }

    #[test]
    fn test_terrain_oob_returns_wall() {
        // Arrange
        let grid = TerrainGrid::new(5, 5, 20.0);
        
        // Act & Assert
        assert_eq!(grid.get_hard_cost(IVec2::new(-1, 0)), u16::MAX, "OOB hard cost should be u16::MAX");
        assert_eq!(grid.get_hard_cost(IVec2::new(5, 0)), u16::MAX, "OOB hard cost should be u16::MAX");
    }

    #[test]
    fn test_terrain_oob_returns_frozen() {
        // Arrange
        let grid = TerrainGrid::new(5, 5, 20.0);
        
        // Act & Assert
        assert_eq!(grid.get_soft_cost(IVec2::new(-1, 0)), 0, "OOB soft cost should be 0");
        assert_eq!(grid.get_soft_cost(IVec2::new(0, 5)), 0, "OOB soft cost should be 0");
    }

    #[test]
    fn test_terrain_hard_obstacles_filters_walls() {
        // Arrange
        let mut grid = TerrainGrid::new(5, 5, 20.0);
        grid.set_cell(1, 1, u16::MAX, 0);
        grid.set_cell(2, 2, u16::MAX, 0);
        grid.set_cell(3, 3, u16::MAX, 0);
        
        // Act
        let obstacles = grid.hard_obstacles();

        // Assert
        assert_eq!(obstacles.len(), 3, "Should return exactly 3 obstacles");
        assert!(obstacles.contains(&IVec2::new(1, 1)), "Should contain (1, 1)");
        assert!(obstacles.contains(&IVec2::new(2, 2)), "Should contain (2, 2)");
        assert!(obstacles.contains(&IVec2::new(3, 3)), "Should contain (3, 3)");
    }

    #[test]
    fn test_terrain_set_cell_bounds_check() {
        // Arrange
        let mut grid = TerrainGrid::new(5, 5, 20.0);
        
        // Act
        grid.set_cell(5, 5, 200, 50); // OOB, should not panic
        
        // Assert
        // Verified by not panicking during 'Act' phase
    }

    #[test]
    fn test_terrain_reset_clears_all() {
        // Arrange
        let mut grid = TerrainGrid::new(5, 5, 20.0);
        grid.set_cell(1, 1, u16::MAX, 0);
        grid.set_cell(2, 2, 200, 30);
        
        // Act
        grid.reset();
        
        // Assert
        assert!(grid.hard_costs.iter().all(|&c| c == 100), "All hard costs should be reset to 100");
        assert!(grid.soft_costs.iter().all(|&c| c == 100), "All soft costs should be reset to 100");
    }

    #[test]
    fn test_terrain_serialization_roundtrip() {
        // Arrange
        let mut original = TerrainGrid::new(5, 5, 20.0);
        original.set_cell(2, 3, u16::MAX, 0);
        
        // Act
        let json = serde_json::to_string(&original).unwrap();
        let deserialized: TerrainGrid = serde_json::from_str(&json).unwrap();
        
        // Assert
        assert_eq!(original.width, deserialized.width, "Width should match");
        assert_eq!(original.height, deserialized.height, "Height should match");
        assert_eq!(original.hard_costs, deserialized.hard_costs, "Hard costs should match");
        assert_eq!(original.soft_costs, deserialized.soft_costs, "Soft costs should match");
    }

    #[test]
    fn test_terrain_world_to_cell_conversion() {
        // Arrange
        let grid = TerrainGrid::new(5, 5, 20.0);
        
        // Act
        let cell = grid.world_to_cell(25.0, 45.0);
        
        // Assert
        assert_eq!(cell, IVec2::new(1, 2), "World pos (25.0, 45.0) should map to cell (1, 2)");
    }
}
