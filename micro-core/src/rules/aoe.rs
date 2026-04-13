//! # Area-of-Effect Configuration
//!
//! Contract types for AoE damage shapes, falloff gradients,
//! and precomputed polygon edge data. All geometry is O(1) or O(V).
//!
//! ## Ownership
//! - **Task:** phase_b1_aoe_damage
//! - **Contract:** implementation_plan.md → Phase B.1
//!
//! ## Depends On
//! - `serde::{Deserialize, Serialize}`

use serde::{Deserialize, Serialize};

/// Area-of-Effect damage configuration.
///
/// Attached to an `InteractionRule`. When present, the rule uses area-based
/// damage centered on the nearest valid target. All targets within the shape
/// take damage scaled by the falloff gradient.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct AoeConfig {
    pub shape: AoeShape,
    pub falloff: AoeFalloff,
}

/// Geometric shapes for AoE damage zones.
///
/// All shapes centered on impact point. Orientation-dependent shapes
/// (Ellipse, ConvexPolygon) rotate according to `rotation_mode`.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "type")]
pub enum AoeShape {
    /// Perfect circle. O(1) hit test — `dist² ≤ radius²`.
    Circle { radius: f32 },

    /// Axis-aligned ellipse. O(1) hit test.
    /// `semi_major` along source→target, `semi_minor` perpendicular.
    Ellipse {
        semi_major: f32,
        semi_minor: f32,
        #[serde(default = "default_rotation_mode")]
        rotation_mode: RotationMode,
    },

    /// Convex polygon ≤ 6 vertices. O(V) hit test.
    /// Vertices are (dx, dy) offsets from impact center, wound CCW.
    ConvexPolygon {
        vertices: Vec<[f32; 2]>,
        #[serde(default = "default_rotation_mode")]
        rotation_mode: RotationMode,
    },
}

/// How orientation-dependent shapes are rotated.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum RotationMode {
    /// Align shape's major axis with source→impact direction (default).
    TargetAligned,
    /// Fixed world-space angle in radians (for environmental zones).
    Fixed(f32),
}

fn default_rotation_mode() -> RotationMode {
    RotationMode::TargetAligned
}

/// How damage scales with normalized distance from impact center.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum AoeFalloff {
    /// Factor = 1.0 everywhere inside (uniform damage, e.g. grenade).
    None,
    /// Factor = max(0, 1.0 - d_norm) — linear dropoff.
    Linear,
    /// Factor = max(0, 1.0 - d_norm²) — steep center, gentle edge.
    Quadratic,
}

/// Precomputed edge data for O(V) convex polygon gradient.
///
/// For each edge AB of the polygon, stores the outward normal (nx, ny)
/// and the half-plane constant `c = A.x * B.y - A.y * B.x`.
///
/// At runtime, `d_norm = max_i(P.x * nx_i + P.y * ny_i) / c_i`.
/// If `d_norm ≤ 1.0`, the point is inside and `d_norm` is the gradient.
///
/// (Correction #1: proper polygon gradient using half-plane math,
///  NOT circular d/max_vertex_distance which is geometrically wrong.)
#[derive(Debug, Clone)]
pub struct PrecomputedPolygonEdges {
    /// (nx, ny, 1/c) per edge — reciprocal stored to avoid division at runtime.
    pub edges: Vec<(f32, f32, f32)>,
}

impl PrecomputedPolygonEdges {
    /// Build edge normals from CCW-wound vertex list. Called once at rule load time.
    ///
    /// For edge A→B: nx = B.y - A.y, ny = A.x - B.x (inward normal for CCW).
    /// c = A.x * B.y - A.y * B.x (perpendicular distance from origin to edge).
    /// We store 1/c to avoid division at runtime.
    pub fn from_vertices(vertices: &[[f32; 2]]) -> Self {
        let n = vertices.len();
        let mut edges = Vec::with_capacity(n);
        for i in 0..n {
            let a = vertices[i];
            let b = vertices[(i + 1) % n];
            let nx = b[1] - a[1];
            let ny = a[0] - b[0];
            let c = a[0] * b[1] - a[1] * b[0];
            // c must be positive for inward-facing normals on CCW polygon
            let inv_c = if c.abs() > 1e-8 { 1.0 / c } else { 0.0 };
            edges.push((nx, ny, inv_c));
        }
        Self { edges }
    }

    /// O(V) hit-test + gradient. Returns `Some(d_norm)` in [0, 1] if inside.
    ///
    /// `d_norm = max_i(P.x * nx_i + P.y * ny_i) * inv_c_i`
    /// If `d_norm ≤ 1.0`, point is inside. `d_norm` = distance to nearest edge
    /// as fraction of polygon extent (0 = center, 1 = edge).
    pub fn hit_test_and_gradient(&self, px: f32, py: f32) -> Option<f32> {
        let mut max_ratio: f32 = f32::NEG_INFINITY;
        for &(nx, ny, inv_c) in &self.edges {
            let ratio = (px * nx + py * ny) * inv_c;
            if ratio > 1.0 {
                return None; // Outside this edge
            }
            max_ratio = max_ratio.max(ratio);
        }
        // Clamp to [0, 1] — center can be slightly negative due to float
        Some(max_ratio.clamp(0.0, 1.0))
    }
}

impl AoeConfig {
    /// Hit-test a point in shape-local coordinates (centered on impact, rotated).
    /// Returns `Some(d_norm)` in [0, 1] if hit, `None` if outside.
    pub fn hit_test(
        &self,
        local_x: f32,
        local_y: f32,
        precomputed: Option<&PrecomputedPolygonEdges>,
    ) -> Option<f32> {
        match &self.shape {
            AoeShape::Circle { radius } => {
                let dist_sq = local_x * local_x + local_y * local_y;
                let r_sq = radius * radius;
                if dist_sq <= r_sq {
                    Some(dist_sq.sqrt() / radius)
                } else {
                    None
                }
            }
            AoeShape::Ellipse {
                semi_major,
                semi_minor,
                ..
            } => {
                let e = (local_x / semi_major).powi(2) + (local_y / semi_minor).powi(2);
                if e <= 1.0 {
                    Some(e.sqrt())
                } else {
                    None
                }
            }
            AoeShape::ConvexPolygon { .. } => {
                precomputed?.hit_test_and_gradient(local_x, local_y)
            }
        }
    }

    /// Compute damage factor from `d_norm` using falloff mode.
    pub fn falloff_factor(&self, d_norm: f32) -> f32 {
        match &self.falloff {
            AoeFalloff::None => 1.0,
            AoeFalloff::Linear => (1.0 - d_norm).max(0.0),
            AoeFalloff::Quadratic => (1.0 - d_norm * d_norm).max(0.0),
        }
    }

    /// Bounding radius for spatial grid query.
    /// All targets within this radius MIGHT be inside the shape.
    pub fn bounding_radius(&self) -> f32 {
        match &self.shape {
            AoeShape::Circle { radius } => *radius,
            AoeShape::Ellipse {
                semi_major,
                semi_minor,
                ..
            } => semi_major.max(*semi_minor),
            AoeShape::ConvexPolygon { vertices, .. } => {
                vertices
                    .iter()
                    .map(|v| (v[0] * v[0] + v[1] * v[1]).sqrt())
                    .fold(0.0f32, f32::max)
            }
        }
    }

    /// Extract the rotation mode for this shape.
    pub fn rotation_mode(&self) -> &RotationMode {
        match &self.shape {
            AoeShape::Circle { .. } => &RotationMode::TargetAligned,
            AoeShape::Ellipse { rotation_mode, .. } => rotation_mode,
            AoeShape::ConvexPolygon { rotation_mode, .. } => rotation_mode,
        }
    }
}

// ── Penetration Types ─────────────────────────────────────────────────

fn default_true() -> bool {
    true
}

/// Penetration configuration for straight-line piercing attacks.
///
/// When attached to an `InteractionRule`, the rule casts a ray from the
/// source through the nearest valid target. All valid targets along the
/// ray (within `ray_width`) take damage, with energy absorbed per hit.
///
/// **Composable with AoE:** When both `aoe` and `penetration` are set on
/// a rule, the AoE shape filters the hit zone and the penetration system
/// handles sequential energy absorption along the ray direction. This
/// enables cone-shaped shotguns, fan-shaped beams, etc.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PenetrationConfig {
    /// Half-width of the penetration ray (perpendicular to direction).
    /// 0.0 = infinitely thin line (point-on-line test only).
    /// Ignored when composing with AoE (AoE shape provides the spatial filter).
    pub ray_width: f32,

    /// Maximum number of targets the ray can pierce.
    /// `None` = unlimited (ray continues until energy depleted).
    #[serde(default)]
    pub max_targets: Option<u32>,

    /// How energy is modeled for the piercing attack.
    pub energy_model: EnergyModel,

    /// If true (default), absorption uses the target's RAW stat value,
    /// ignoring mitigation. This means tanks body-block with their full
    /// survivability stat even if they have damage reduction.
    #[serde(default = "default_true")]
    pub absorption_ignores_mitigation: bool,

    /// Which stat index is used for absorption calculation.
    /// Usually stat[0] (survivability). The ray loses energy proportional
    /// to how much of this stat the target has remaining.
    pub absorption_stat_index: usize,
}

/// Energy model for penetration attacks.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum EnergyModel {
    /// Burst damage: normalized energy starts at 1.0, consumed per target.
    /// `base_energy` is the total damage potential (e.g., 100.0).
    /// Each target absorbs `min(remaining_energy, target_stat / base_energy)`.
    Kinetic { base_energy: f32 },

    /// Sustained drain: energy is per-tick (`delta_per_second / 60`).
    /// No absorption — all targets in the ray take full damage.
    /// Useful for lasers/beams that pass through everything.
    Beam,
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    // ── Circle ──

    #[test]
    fn test_circle_hit_center() {
        let aoe = AoeConfig {
            shape: AoeShape::Circle { radius: 10.0 },
            falloff: AoeFalloff::None,
        };
        let d = aoe.hit_test(0.0, 0.0, None).unwrap();
        assert!(d.abs() < 1e-6, "Center should have d_norm ≈ 0.0, got {}", d);
    }

    #[test]
    fn test_circle_hit_halfway() {
        let aoe = AoeConfig {
            shape: AoeShape::Circle { radius: 10.0 },
            falloff: AoeFalloff::None,
        };
        let d = aoe.hit_test(5.0, 0.0, None).unwrap();
        assert!((d - 0.5).abs() < 1e-4, "Halfway should have d_norm ≈ 0.5, got {}", d);
    }

    #[test]
    fn test_circle_miss_outside() {
        let aoe = AoeConfig {
            shape: AoeShape::Circle { radius: 10.0 },
            falloff: AoeFalloff::None,
        };
        assert!(aoe.hit_test(11.0, 0.0, None).is_none(), "Outside circle should miss");
    }

    // ── Ellipse ──

    #[test]
    fn test_ellipse_major_axis_edge() {
        let aoe = AoeConfig {
            shape: AoeShape::Ellipse {
                semi_major: 20.0,
                semi_minor: 5.0,
                rotation_mode: RotationMode::TargetAligned,
            },
            falloff: AoeFalloff::None,
        };
        // At edge of major axis
        let d = aoe.hit_test(19.9, 0.0, None).unwrap();
        assert!(d > 0.99, "Major edge should be ≈ 1.0, got {}", d);
    }

    #[test]
    fn test_ellipse_minor_axis_edge() {
        let aoe = AoeConfig {
            shape: AoeShape::Ellipse {
                semi_major: 20.0,
                semi_minor: 5.0,
                rotation_mode: RotationMode::TargetAligned,
            },
            falloff: AoeFalloff::None,
        };
        // At edge of minor axis
        let d = aoe.hit_test(0.0, 4.9, None).unwrap();
        assert!(d > 0.97, "Minor edge should be ≈ 1.0, got {}", d);
    }

    #[test]
    fn test_ellipse_miss_beyond_minor() {
        let aoe = AoeConfig {
            shape: AoeShape::Ellipse {
                semi_major: 20.0,
                semi_minor: 5.0,
                rotation_mode: RotationMode::TargetAligned,
            },
            falloff: AoeFalloff::None,
        };
        assert!(
            aoe.hit_test(0.0, 6.0, None).is_none(),
            "Beyond minor axis should miss"
        );
    }

    // ── ConvexPolygon (Correction #1: proper gradient) ──

    #[test]
    fn test_polygon_triangle_center() {
        // Equilateral-ish triangle centered at origin
        let vertices = vec![[0.0, 10.0], [-8.66, -5.0], [8.66, -5.0]];
        let pre = PrecomputedPolygonEdges::from_vertices(&vertices);
        let aoe = AoeConfig {
            shape: AoeShape::ConvexPolygon {
                vertices,
                rotation_mode: RotationMode::TargetAligned,
            },
            falloff: AoeFalloff::None,
        };
        let d = aoe.hit_test(0.0, 0.0, Some(&pre)).unwrap();
        assert!(d < 0.1, "Center of triangle should have low d_norm, got {}", d);
    }

    #[test]
    fn test_polygon_lateral_edge_gradient_correction_1() {
        // THIN CONE: long and narrow (Correction #1 test case)
        // length=100 along X, width=20 along Y
        let vertices = vec![
            [100.0, 10.0],   // far right, upper
            [100.0, -10.0],  // far right, lower
            [0.0, -10.0],    // near left, lower
            [0.0, 10.0],     // near left, upper
        ];
        let pre = PrecomputedPolygonEdges::from_vertices(&vertices);
        let aoe = AoeConfig {
            shape: AoeShape::ConvexPolygon {
                vertices,
                rotation_mode: RotationMode::TargetAligned,
            },
            falloff: AoeFalloff::Linear,
        };

        // Point at the lateral edge (x=50, y=9.5) — near the top boundary
        // With the WRONG circular gradient: d = 9.5/100 = 0.095 → 90.5% damage!
        // With the CORRECT polygon gradient: d ≈ 0.95 → 5% damage (near edge)
        let d = aoe.hit_test(50.0, 9.5, Some(&pre)).unwrap();
        assert!(
            d > 0.9,
            "Lateral edge of thin cone should have d_norm > 0.9, got {} (Correction #1)",
            d
        );
        let factor = aoe.falloff_factor(d);
        assert!(
            factor < 0.15,
            "Damage at lateral edge should be < 15%, got {} (Correction #1)",
            factor
        );
    }

    #[test]
    fn test_polygon_miss_outside() {
        let vertices = vec![[10.0, 0.0], [0.0, 10.0], [-10.0, 0.0], [0.0, -10.0]];
        let pre = PrecomputedPolygonEdges::from_vertices(&vertices);
        let aoe = AoeConfig {
            shape: AoeShape::ConvexPolygon {
                vertices,
                rotation_mode: RotationMode::TargetAligned,
            },
            falloff: AoeFalloff::None,
        };
        assert!(
            aoe.hit_test(11.0, 0.0, Some(&pre)).is_none(),
            "Outside polygon should miss"
        );
    }

    // ── Falloff functions ──

    #[test]
    fn test_falloff_none_always_one() {
        let aoe = AoeConfig {
            shape: AoeShape::Circle { radius: 10.0 },
            falloff: AoeFalloff::None,
        };
        assert!((aoe.falloff_factor(0.0) - 1.0).abs() < 1e-6, "None falloff at center");
        assert!((aoe.falloff_factor(0.5) - 1.0).abs() < 1e-6, "None falloff at mid");
        assert!((aoe.falloff_factor(1.0) - 1.0).abs() < 1e-6, "None falloff at edge");
    }

    #[test]
    fn test_falloff_linear() {
        let aoe = AoeConfig {
            shape: AoeShape::Circle { radius: 10.0 },
            falloff: AoeFalloff::Linear,
        };
        assert!((aoe.falloff_factor(0.0) - 1.0).abs() < 1e-6, "Linear at center = 1.0");
        assert!((aoe.falloff_factor(0.3) - 0.7).abs() < 1e-6, "Linear at 0.3 = 0.7");
        assert!((aoe.falloff_factor(1.0) - 0.0).abs() < 1e-6, "Linear at edge = 0.0");
    }

    #[test]
    fn test_falloff_quadratic() {
        let aoe = AoeConfig {
            shape: AoeShape::Circle { radius: 10.0 },
            falloff: AoeFalloff::Quadratic,
        };
        assert!((aoe.falloff_factor(0.0) - 1.0).abs() < 1e-6, "Quadratic at center = 1.0");
        assert!((aoe.falloff_factor(0.5) - 0.75).abs() < 1e-6, "Quadratic at 0.5 = 0.75");
        assert!((aoe.falloff_factor(1.0) - 0.0).abs() < 1e-6, "Quadratic at edge = 0.0");
    }

    // ── Bounding radius ──

    #[test]
    fn test_bounding_radius_circle() {
        let aoe = AoeConfig {
            shape: AoeShape::Circle { radius: 15.0 },
            falloff: AoeFalloff::None,
        };
        assert!((aoe.bounding_radius() - 15.0).abs() < 1e-6, "Circle bounding radius");
    }

    #[test]
    fn test_bounding_radius_ellipse() {
        let aoe = AoeConfig {
            shape: AoeShape::Ellipse {
                semi_major: 20.0,
                semi_minor: 5.0,
                rotation_mode: RotationMode::TargetAligned,
            },
            falloff: AoeFalloff::None,
        };
        assert!((aoe.bounding_radius() - 20.0).abs() < 1e-6, "Ellipse bounding radius is max axis");
    }

    // ── Serde roundtrip ──

    #[test]
    fn test_aoe_config_serde_roundtrip_circle() {
        let aoe = AoeConfig {
            shape: AoeShape::Circle { radius: 25.0 },
            falloff: AoeFalloff::Linear,
        };
        let json = serde_json::to_string(&aoe).unwrap();
        let deserialized: AoeConfig = serde_json::from_str(&json).unwrap();
        assert_eq!(aoe, deserialized, "Circle AoeConfig should roundtrip");
    }

    #[test]
    fn test_aoe_config_serde_roundtrip_polygon() {
        let aoe = AoeConfig {
            shape: AoeShape::ConvexPolygon {
                vertices: vec![[10.0, 0.0], [0.0, 10.0], [-10.0, 0.0]],
                rotation_mode: RotationMode::Fixed(1.57),
            },
            falloff: AoeFalloff::Quadratic,
        };
        let json = serde_json::to_string(&aoe).unwrap();
        let deserialized: AoeConfig = serde_json::from_str(&json).unwrap();
        assert_eq!(aoe, deserialized, "Polygon AoeConfig should roundtrip");
    }
}
