use serde::{Deserialize, Serialize};

/// Terrain data payload for ZMQ atomic environment reset.
///
/// Contains the full terrain grid that Rust applies to `TerrainGrid`.
/// Uses the 3-tier cost encoding:
/// - Tier 0 (100-60,000): passable
/// - Tier 1 (60,001-65,534): destructible walls
/// - Tier 2 (65,535 / u16::MAX): permanent walls
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct TerrainPayload {
    pub hard_costs: Vec<u16>,
    pub soft_costs: Vec<u16>,
    pub width: u32,
    pub height: u32,
    pub cell_size: f32,
}

/// Combat rule from game profile (replaces InteractionRuleSet::default).
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct CombatRulePayload {
    pub source_faction: u32,
    pub target_faction: u32,
    pub range: f32,
    pub effects: Vec<StatEffectPayload>,
    #[serde(default)]
    pub source_class: Option<u32>,
    #[serde(default)]
    pub target_class: Option<u32>,
    #[serde(default)]
    pub range_stat_index: Option<usize>,
    #[serde(default)]
    pub mitigation: Option<MitigationPayload>,
    #[serde(default)]
    pub cooldown_ticks: Option<u32>,
    #[serde(default)]
    pub aoe: Option<crate::rules::aoe::AoeConfig>,
    #[serde(default)]
    pub penetration: Option<crate::rules::aoe::PenetrationConfig>,
}

/// Mitigation configuration from game profile.
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct MitigationPayload {
    pub stat_index: usize,
    /// "PercentReduction" or "FlatReduction"
    pub mode: String,
}

/// Stat effect payload from game profile.
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct StatEffectPayload {
    pub stat_index: usize,
    pub delta_per_second: f32,
}

#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct MovementConfigPayload {
    pub max_speed: f32,
    pub steering_factor: f32,
    pub separation_radius: f32,
    pub separation_weight: f32,
    pub flow_weight: f32,
}

#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct TerrainThresholdsPayload {
    pub impassable_threshold: u16,
    pub destructible_min: u16,
}

#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct RemovalRulePayload {
    pub stat_index: usize,
    pub threshold: f32,
    pub condition: String,
}

/// Navigation rule from game profile (replaces NavigationRuleSet::default).
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct NavigationRulePayload {
    pub follower_faction: u32,
    pub target: super::NavigationTarget,
}

fn default_zone_duration() -> u32 { 120 }

/// Ability configuration from game profile.
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct AbilityConfigPayload {
    pub buff_cooldown_ticks: u32,
    #[serde(default)]
    pub movement_speed_stat: Option<usize>,
    #[serde(default)]
    pub combat_damage_stat: Option<usize>,
    /// Duration in ticks for SetZoneModifier effects.
    /// Sent from Python game profile. Default: 120 (~2 seconds at 60 TPS).
    #[serde(default = "default_zone_duration")]
    pub zone_modifier_duration_ticks: u32,
}

/// Faction spawn configuration for environment reset.
///
/// Entities are spawned around (x, y) within a `spread` radius.
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct SpawnConfig {
    pub faction_id: u32,
    pub count: u32,
    pub x: f32,
    pub y: f32,
    pub spread: f32,
    /// Per-spawn stat values. Each entry is {index, value}.
    /// If absent or empty, entities spawn with all-zero StatBlock.
    /// The adapter (game profile) should always provide explicit stat values.
    #[serde(default)]
    pub stats: Vec<SpawnStatEntry>,
    /// Optional unit class ID for spawned entities. Default: 0 (generic).
    /// When absent in JSON, entities spawn as class 0 (backward compatible).
    #[serde(default)]
    pub unit_class_id: u32,
    /// Per-spawn movement override. Highest priority in the resolution chain:
    /// spawn.movement > unit_type.movement > global movement_config > default.
    #[serde(default)]
    pub movement: Option<MovementConfigPayload>,
}

/// A single stat override for spawn configuration.
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct SpawnStatEntry {
    pub index: usize,
    pub value: f32,
}

/// Tactical behavior rule from game profile.
///
/// Each variant produces a V_tactical steering vector, evaluated at 10 Hz
/// by the tactical_sensor_system. Uses `serde(tag = "type")` for clean
/// JSON discriminator (e.g., `{"type": "Kite", "trigger_radius": 50.0}`).
///
/// # Examples
///
/// ```
/// use micro_core::bridges::zmq_protocol::TacticalBehaviorPayload;
/// use serde_json;
///
/// let json = r#"{"type": "Kite", "trigger_radius": 50.0, "weight": 2.0}"#;
/// let behavior: TacticalBehaviorPayload = serde_json::from_str(json).unwrap();
/// assert_eq!(behavior, TacticalBehaviorPayload::Kite { trigger_radius: 50.0, weight: 2.0 });
/// ```
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
#[serde(tag = "type")]
pub enum TacticalBehaviorPayload {
    /// Flee from nearest enemy within trigger_radius.
    /// V_tactical = normalize(self.pos - enemy.pos)
    Kite {
        trigger_radius: f32,
        weight: f32,
    },
    /// Rush toward a distressed ally of a specific class.
    /// V_tactical = normalize(ally.pos - self.pos)
    PeelForAlly {
        target_class: u32,
        search_radius: f32,
        #[serde(default)]
        require_recent_damage: bool,
        weight: f32,
    },
}

/// Unit type definition from game profile.
///
/// Maps a class_id to stats, movement, engagement range, and tactical behaviors.
/// Sent via the `unit_types` field of `AiResponse::ResetEnvironment`.
/// The Rust engine loads these into a `UnitTypeRegistry` resource at episode start.
///
/// # Examples
///
/// ```
/// use micro_core::bridges::zmq_protocol::{UnitTypeDefinition, TacticalBehaviorPayload};
/// use serde_json;
///
/// let json = r#"{
///     "class_id": 1,
///     "engagement_range": 150.0,
///     "tactical_behaviors": [
///         {"type": "Kite", "trigger_radius": 50.0, "weight": 2.0}
///     ]
/// }"#;
/// let ut: UnitTypeDefinition = serde_json::from_str(json).unwrap();
/// assert_eq!(ut.class_id, 1);
/// assert!((ut.engagement_range - 150.0).abs() < f32::EPSILON);
/// assert_eq!(ut.tactical_behaviors.len(), 1);
/// ```
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct UnitTypeDefinition {
    pub class_id: u32,
    #[serde(default)]
    pub stats: Vec<SpawnStatEntry>,
    #[serde(default)]
    pub movement: Option<MovementConfigPayload>,
    /// Distance at which this unit stops approaching enemies.
    /// When nearest enemy is within this range, W_flow drops to 0.
    /// 0.0 = charge to melee (default). 150.0 = ranger standoff.
    #[serde(default)]
    pub engagement_range: f32,
    /// Tactical micro-behaviors evaluated at 10 Hz by the tactical sensor.
    /// Empty = no tactical override (pure flow field follower).
    #[serde(default)]
    pub tactical_behaviors: Vec<TacticalBehaviorPayload>,
}

/// Stat indices whose PRODUCT forms the ECP threat value.
///
/// Sent via `ecp_formula` field of `AiResponse::ResetEnvironment`.
/// Example: `[0, 4]` → ECP = stat[0] × stat[4] (HP × armor).
/// Empty / absent = use single `ecp_stat_index` (backward compat).
///
/// # Examples
///
/// ```
/// use micro_core::bridges::zmq_protocol::EcpFormulaPayload;
/// use serde_json;
///
/// let json = r#"{"stat_indices": [0, 4]}"#;
/// let formula: EcpFormulaPayload = serde_json::from_str(json).unwrap();
/// assert_eq!(formula.stat_indices, vec![0, 4]);
/// ```
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct EcpFormulaPayload {
    pub stat_indices: Vec<usize>,
}
