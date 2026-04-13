//! # Unit Type Registry
//!
//! Bevy ECS resource mapping `class_id → UnitTypeDef` for heterogeneous swarms.
//! Populated from the `unit_types` field of `AiResponse::ResetEnvironment`.
//! Cleared and rebuilt at each episode reset.
//!
//! ## Ownership
//! - **Task:** T03 — ECS Components + Registry (Boids 2.0)
//! - **Contract:** implementation_plan.md → T03
//!
//! ## Depends On
//! - `crate::bridges::zmq_protocol::{UnitTypeDefinition, TacticalBehaviorPayload, MovementConfigPayload}`

use bevy::prelude::*;
use std::collections::HashMap;

/// Runtime tactical behavior, converted from `TacticalBehaviorPayload`.
///
/// This is the engine-internal representation; the payload struct is
/// the wire format. They are intentionally identical for now but kept
/// separate to allow future divergence (e.g. precomputed look-up tables).
#[derive(Debug, Clone)]
pub enum TacticalBehavior {
    /// Flee from nearest enemy within trigger_radius.
    Kite {
        trigger_radius: f32,
        weight: f32,
    },
    /// Rush toward a distressed ally of a specific class.
    PeelForAlly {
        target_class: u32,
        search_radius: f32,
        require_recent_damage: bool,
        weight: f32,
    },
}

/// Runtime unit type definition, keyed by class_id.
#[derive(Debug, Clone)]
pub struct UnitTypeDef {
    /// Distance at which this unit stops approaching enemies.
    /// 0.0 = charge to melee (default).
    pub engagement_range: f32,
    /// Optional per-class movement override.
    pub movement: Option<crate::bridges::zmq_protocol::MovementConfigPayload>,
    /// Tactical behaviors in priority order (highest weight wins via subsumption).
    pub behaviors: Vec<TacticalBehavior>,
}

/// Registry of all unit types for the current episode.
///
/// Lookup is O(1) via HashMap. The registry is rebuilt on every
/// `ResetEnvironment` and remains immutable during the episode.
///
/// ## Default
/// Empty registry — all entities are treated as generic class 0
/// with zero engagement_range and no tactical behaviors.
#[derive(Resource, Debug, Clone, Default)]
pub struct UnitTypeRegistry {
    pub types: HashMap<u32, UnitTypeDef>,
}

impl UnitTypeRegistry {
    /// Rebuilds the registry from a list of `UnitTypeDefinition` payloads.
    ///
    /// Converts wire-format `TacticalBehaviorPayload` to runtime `TacticalBehavior`.
    pub fn rebuild_from_payloads(
        &mut self,
        defs: &[crate::bridges::zmq_protocol::UnitTypeDefinition],
    ) {
        self.types.clear();
        for def in defs {
            let behaviors: Vec<TacticalBehavior> = def
                .tactical_behaviors
                .iter()
                .map(|b| match b {
                    crate::bridges::zmq_protocol::TacticalBehaviorPayload::Kite {
                        trigger_radius,
                        weight,
                    } => TacticalBehavior::Kite {
                        trigger_radius: *trigger_radius,
                        weight: *weight,
                    },
                    crate::bridges::zmq_protocol::TacticalBehaviorPayload::PeelForAlly {
                        target_class,
                        search_radius,
                        require_recent_damage,
                        weight,
                    } => TacticalBehavior::PeelForAlly {
                        target_class: *target_class,
                        search_radius: *search_radius,
                        require_recent_damage: *require_recent_damage,
                        weight: *weight,
                    },
                })
                .collect();

            self.types.insert(
                def.class_id,
                UnitTypeDef {
                    engagement_range: def.engagement_range,
                    movement: def.movement.clone(),
                    behaviors,
                },
            );
        }
    }

    /// Returns the definition for a class_id, or `None` for generic units.
    pub fn get(&self, class_id: u32) -> Option<&UnitTypeDef> {
        self.types.get(&class_id)
    }
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::bridges::zmq_protocol::{
        TacticalBehaviorPayload, UnitTypeDefinition,
    };

    #[test]
    fn test_registry_default_is_empty() {
        // Arrange
        let registry = UnitTypeRegistry::default();

        // Assert
        assert!(registry.types.is_empty(), "Default registry should be empty");
        assert!(registry.get(0).is_none(), "Class 0 should not exist in empty registry");
    }

    #[test]
    fn test_registry_rebuild_from_payloads() {
        // Arrange
        let mut registry = UnitTypeRegistry::default();
        let defs = vec![
            UnitTypeDefinition {
                class_id: 1,
                stats: vec![],
                movement: None,
                engagement_range: 150.0,
                tactical_behaviors: vec![
                    TacticalBehaviorPayload::Kite {
                        trigger_radius: 50.0,
                        weight: 2.0,
                    },
                ],
            },
            UnitTypeDefinition {
                class_id: 2,
                stats: vec![],
                movement: None,
                engagement_range: 0.0,
                tactical_behaviors: vec![
                    TacticalBehaviorPayload::PeelForAlly {
                        target_class: 1,
                        search_radius: 80.0,
                        require_recent_damage: true,
                        weight: 3.0,
                    },
                ],
            },
        ];

        // Act
        registry.rebuild_from_payloads(&defs);

        // Assert
        assert_eq!(registry.types.len(), 2, "Should have 2 unit types");

        let ranger = registry.get(1).expect("Class 1 should exist");
        assert!((ranger.engagement_range - 150.0).abs() < f32::EPSILON,
            "Ranger engagement_range should be 150.0");
        assert_eq!(ranger.behaviors.len(), 1, "Ranger should have 1 behavior");

        let protector = registry.get(2).expect("Class 2 should exist");
        assert!((protector.engagement_range - 0.0).abs() < f32::EPSILON,
            "Protector engagement_range should be 0.0");
        assert_eq!(protector.behaviors.len(), 1, "Protector should have 1 behavior");
    }

    #[test]
    fn test_registry_rebuild_clears_previous() {
        // Arrange
        let mut registry = UnitTypeRegistry::default();
        let defs_v1 = vec![UnitTypeDefinition {
            class_id: 1,
            stats: vec![],
            movement: None,
            engagement_range: 100.0,
            tactical_behaviors: vec![],
        }];
        registry.rebuild_from_payloads(&defs_v1);
        assert!(registry.get(1).is_some());

        // Act — rebuild with different data
        let defs_v2 = vec![UnitTypeDefinition {
            class_id: 5,
            stats: vec![],
            movement: None,
            engagement_range: 50.0,
            tactical_behaviors: vec![],
        }];
        registry.rebuild_from_payloads(&defs_v2);

        // Assert
        assert!(registry.get(1).is_none(), "Old class 1 should be gone");
        assert!(registry.get(5).is_some(), "New class 5 should exist");
    }
}
