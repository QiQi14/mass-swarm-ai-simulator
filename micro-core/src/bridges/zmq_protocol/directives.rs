use super::payloads::*;
use serde::{Deserialize, Serialize};

/// Macro action received from Python → Rust via ZMQ REP.
///
/// The `action` field contains the action vocabulary string
/// (e.g., "HOLD", "FLANK_LEFT"). The `params` field is a
/// flexible JSON object for action-specific parameters.
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct MacroAction {
    #[serde(rename = "type")]
    pub msg_type: String,
    pub action: String,
    pub params: serde_json::Value,
}

/// Navigation target: dynamic (chase a faction) or static (go to a point).
///
/// # Examples
/// ```rust
/// use micro_core::bridges::zmq_protocol::NavigationTarget;
/// use serde_json;
///
/// let faction_target = NavigationTarget::Faction { faction_id: 2 };
/// let json = serde_json::to_string(&faction_target).unwrap();
/// assert_eq!(json, r#"{"type":"Faction","faction_id":2}"#);
///
/// let waypoint_target = NavigationTarget::Waypoint { x: 10.0, y: 20.0 };
/// let json = serde_json::to_string(&waypoint_target).unwrap();
/// assert_eq!(json, r#"{"type":"Waypoint","x":10.0,"y":20.0}"#);
///
/// let deserialized: NavigationTarget = serde_json::from_str(&json).unwrap();
/// assert_eq!(deserialized, waypoint_target);
/// ```
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
#[serde(tag = "type")]
pub enum NavigationTarget {
    Faction { faction_id: u32 },
    Waypoint { x: f32, y: f32 },
}

#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub enum ModifierType {
    Multiplier,
    FlatAdd,
}

#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct StatModifierPayload {
    pub stat_index: usize,
    pub modifier_type: ModifierType,
    pub value: f32,
}

/// Macro-level strategic directives from ML Brain → Rust Core.
/// 8-action vocabulary enabling all three swarm-splitting strategies:
/// - Pheromone Gravity Wells (SetZoneModifier)
/// - Dynamic Sub-Faction Tagging (SplitFaction/MergeFaction)
/// - Boids Self-Organizing Flanking (emergent, no directive needed)
///
/// # Examples
/// ```rust
/// use micro_core::bridges::zmq_protocol::{MacroDirective, NavigationTarget};
/// use serde_json;
///
/// let json = r#"{
///     "directive": "UpdateNavigation",
///     "follower_faction": 1,
///     "target": {
///         "type": "Waypoint",
///         "x": 100.0,
///         "y": 200.0
///     }
/// }"#;
///
/// let directive: MacroDirective = serde_json::from_str(json).unwrap();
/// assert_eq!(
///     directive,
///     MacroDirective::UpdateNavigation {
///         follower_faction: 1,
///         target: NavigationTarget::Waypoint { x: 100.0, y: 200.0 },
///     }
/// );
/// ```
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
#[serde(tag = "directive")]
pub enum MacroDirective {
    Idle,
    Hold {
        faction_id: u32,
    },

    UpdateNavigation {
        follower_faction: u32,
        target: NavigationTarget,
    },

    ActivateBuff {
        faction: u32,
        modifiers: Vec<StatModifierPayload>,
        duration_ticks: u32,
        #[serde(default)]
        targets: Option<Vec<u32>>,
    },

    Retreat {
        faction: u32,
        retreat_x: f32,
        retreat_y: f32,
    },

    /// Positive cost_modifier = repel, Negative = attract
    SetZoneModifier {
        target_faction: u32,
        x: f32,
        y: f32,
        radius: f32,
        cost_modifier: f32,
    },

    /// Rust selects entities nearest to epicenter first (Quickselect O(N))
    SplitFaction {
        source_faction: u32,
        new_sub_faction: u32,
        percentage: f32,
        epicenter: [f32; 2],
        #[serde(default)]
        class_filter: Option<u32>,
    },

    MergeFaction {
        source_faction: u32,
        target_faction: u32,
    },

    SetAggroMask {
        source_faction: u32,
        target_faction: u32,
        allow_combat: bool,
    },

    SetTacticalOverride {
        faction: u32,
        behavior: Option<TacticalBehaviorPayload>,
    },
}

/// Discriminated union for ZMQ responses from Python.
///
/// Python can respond with either a normal directive (99% of frames)
/// or a reset command (during `SwarmEnv.reset()`).
/// Uses `type` field as the JSON discriminator.
#[derive(Serialize, Deserialize, Debug, Clone)]
#[serde(tag = "type")]
pub enum AiResponse {
    /// Normal directive — maps to a MacroDirective variant.
    #[serde(rename = "macro_directive")]
    Directive {
        #[serde(flatten)]
        directive: MacroDirective,
    },

    /// Reset command — Rust rebuilds environment atomically.
    /// Sent only during SwarmEnv.reset().
    /// Optionally includes combat rules and ability config from the game profile.
    #[serde(rename = "reset_environment")]
    ResetEnvironment {
        terrain: Option<TerrainPayload>,
        spawns: Vec<SpawnConfig>,
        #[serde(default)]
        combat_rules: Option<Vec<CombatRulePayload>>,
        #[serde(default)]
        ability_config: Option<AbilityConfigPayload>,
        #[serde(default)]
        movement_config: Option<MovementConfigPayload>,
        #[serde(default)]
        max_density: Option<f32>,
        #[serde(default)]
        max_entity_ecp: Option<f32>,
        #[serde(default)]
        terrain_thresholds: Option<TerrainThresholdsPayload>,
        #[serde(default)]
        removal_rules: Option<Vec<RemovalRulePayload>>,
        #[serde(default)]
        navigation_rules: Option<Vec<NavigationRulePayload>>,
        /// Which stat index feeds ECP density computation.
        /// `None` in JSON = keep current default. `null` = disable ECP.
        #[serde(default)]
        ecp_stat_index: Option<Option<usize>>,
        /// Unit type definitions for heterogeneous swarms.
        /// Each entry defines a class_id with stats, movement, engagement range,
        /// and tactical behaviors. Loaded into `UnitTypeRegistry` at episode start.
        #[serde(default)]
        unit_types: Option<Vec<UnitTypeDefinition>>,
        /// Multi-stat ECP formula. Product of stat values at these indices.
        /// When present, overrides single `ecp_stat_index`.
        #[serde(default)]
        ecp_formula: Option<EcpFormulaPayload>,
    },
}

#[cfg(test)]
#[path = "directives_tests.rs"]
mod tests;
