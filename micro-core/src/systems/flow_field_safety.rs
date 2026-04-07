//! # Flow Field Safety Interventions
//!
//! Excluded from the core flow field computation logic to isolate safety/regression
//! patches from the primary algorithm layer.

/// Applies zone modifier cost overlays to a mutable cost map.
///
/// ## PATCH 2: MOSES EFFECT GUARD
/// Wall tiles (`u16::MAX`) are NEVER modified. A negative cost_modifier
/// on a wall would convert it to traversable terrain, allowing entities
/// to clip through solid rock.
pub fn apply_zone_overlays(
    cost_map: &mut [u16],
    active_zones: &crate::config::ActiveZoneModifiers,
    follower_faction: u32,
    cell_size: f32,
    grid_w: usize,
    grid_h: usize,
) {
    for zone in active_zones.zones.iter() {
        if zone.target_faction != follower_faction {
            continue;
        }

        let cx = (zone.x / cell_size).floor() as i32;
        let cy = (zone.y / cell_size).floor() as i32;
        let r_cells = (zone.radius / cell_size).ceil() as i32;

        for dy in -r_cells..=r_cells {
            for dx in -r_cells..=r_cells {
                let nx = cx + dx;
                let ny = cy + dy;
                if nx < 0 || nx >= grid_w as i32 || ny < 0 || ny >= grid_h as i32 {
                    continue;
                }
                let dist = ((dx * dx + dy * dy) as f32).sqrt() * cell_size;
                if dist > zone.radius {
                    continue;
                }

                let idx = (ny as u32 * grid_w as u32 + nx as u32) as usize;
                let current_cost = cost_map[idx];

                // ══════════════════════════════════════════════════════
                // PATCH 2: MOSES EFFECT GUARD
                // NEVER modify impassable tiles. A wall is a wall is a wall.
                // Without this, cost_modifier = -500 on a wall tile converts
                // u16::MAX (65535) → 65035, making it traversable.
                // ══════════════════════════════════════════════════════
                if current_cost == u16::MAX {
                    continue;
                }

                // Clamp upper to u16::MAX - 1 to prevent accidentally
                // creating phantom walls via positive cost_modifier
                let adjusted =
                    (current_cost as f32 + zone.cost_modifier).clamp(1.0, (u16::MAX - 1) as f32);
                cost_map[idx] = adjusted as u16;
            }
        }
    }
}
