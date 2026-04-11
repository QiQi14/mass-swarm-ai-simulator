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
}

/// A single stat override for spawn configuration.
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct SpawnStatEntry {
    pub index: usize,
    pub value: f32,
}
