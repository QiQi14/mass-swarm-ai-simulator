use bevy::prelude::*;

/// Buff system configuration from game profile.
///
/// Maps abstract stat indices to engine system behaviors.
/// The engine has movement and combat systems — those are engine mechanics.
/// But WHICH stat index drives speed vs damage is game design.
#[derive(Resource, Debug, Clone)]
pub struct BuffConfig {
    /// Cooldown ticks after any buff expires. Default: 0.
    pub cooldown_ticks: u32,
    /// Which stat_index in active buffs controls movement speed multiplier.
    /// None = buffs never affect movement speed.
    pub movement_speed_stat: Option<usize>,
    /// Which stat_index in active buffs controls combat damage multiplier.
    /// None = buffs never affect combat damage.
    pub combat_damage_stat: Option<usize>,
    /// Duration in ticks for SetZoneModifier effects. Default: 120.
    pub zone_modifier_duration_ticks: u32,
}

impl Default for BuffConfig {
    fn default() -> Self {
        Self {
            cooldown_ticks: 0,
            movement_speed_stat: None,
            combat_damage_stat: None,
            zone_modifier_duration_ticks: 120,
        }
    }
}

/// Active stat-multiplier buffs per faction — fully abstract.
///
/// Each buff group contains modifiers (stat_index + type + value), a duration,
/// and optional entity-level targeting. The engine doesn't know what
/// stat_index 0 means — the game profile defines that.
#[derive(Resource, Debug, Default)]
pub struct FactionBuffs {
    /// Active buff groups: faction → list of active buff groups.
    pub buffs: std::collections::HashMap<u32, Vec<ActiveBuffGroup>>,
    /// Cooldown: faction → ticks remaining before next buff activation.
    pub cooldowns: std::collections::HashMap<u32, u32>,
}

impl FactionBuffs {
    /// Get the cumulative multiplier for a specific stat, respecting entity targeting.
    ///
    /// Returns `1.0` if no active multiplier buff targets this entity.
    ///
    /// # Examples
    ///
    /// ```
    /// use micro_core::config::{FactionBuffs, ActiveBuffGroup, ActiveModifier, ModifierType};
    ///
    /// let mut buffs = FactionBuffs::default();
    /// assert!((buffs.get_multiplier(0, 1, 0) - 1.0).abs() < f32::EPSILON);
    ///
    /// buffs.buffs.insert(0, vec![ActiveBuffGroup {
    ///     modifiers: vec![ActiveModifier {
    ///         stat_index: 0,
    ///         modifier_type: ModifierType::Multiplier,
    ///         value: 1.5,
    ///     }],
    ///     remaining_ticks: 60,
    ///     targets: Some(vec![]),
    /// }]);
    /// assert!((buffs.get_multiplier(0, 1, 0) - 1.5).abs() < f32::EPSILON);
    /// ```
    pub fn get_multiplier(&self, faction: u32, entity_id: u32, stat_index: usize) -> f32 {
        let Some(groups) = self.buffs.get(&faction) else {
            return 1.0;
        };
        let mut product = 1.0f32;
        for group in groups {
            if !group.targets_entity(entity_id) {
                continue;
            }
            for m in &group.modifiers {
                if m.stat_index == stat_index && m.modifier_type == ModifierType::Multiplier {
                    product *= m.value;
                }
            }
        }
        product
    }

    /// Get the cumulative flat add for a specific stat, respecting entity targeting.
    ///
    /// # Examples
    ///
    /// ```
    /// use micro_core::config::{FactionBuffs, ActiveBuffGroup, ActiveModifier, ModifierType};
    ///
    /// let mut buffs = FactionBuffs::default();
    /// assert!((buffs.get_flat_add(0, 1, 0) - 0.0).abs() < f32::EPSILON);
    ///
    /// buffs.buffs.insert(0, vec![ActiveBuffGroup {
    ///     modifiers: vec![ActiveModifier {
    ///         stat_index: 0,
    ///         modifier_type: ModifierType::FlatAdd,
    ///         value: 5.0,
    ///     }],
    ///     remaining_ticks: 60,
    ///     targets: Some(vec![]),
    /// }]);
    /// assert!((buffs.get_flat_add(0, 1, 0) - 5.0).abs() < f32::EPSILON);
    /// ```
    pub fn get_flat_add(&self, faction: u32, entity_id: u32, stat_index: usize) -> f32 {
        let Some(groups) = self.buffs.get(&faction) else {
            return 0.0;
        };
        let mut sum = 0.0f32;
        for group in groups {
            if !group.targets_entity(entity_id) {
                continue;
            }
            for m in &group.modifiers {
                if m.stat_index == stat_index && m.modifier_type == ModifierType::FlatAdd {
                    sum += m.value;
                }
            }
        }
        sum
    }
}

/// A group of stat modifiers applied together with shared duration and targeting.
#[derive(Debug, Clone)]
pub struct ActiveBuffGroup {
    pub modifiers: Vec<ActiveModifier>,
    pub remaining_ticks: u32,
    /// Entity-level targeting:
    /// - None → no units affected (buff is dormant)
    /// - Some(empty vec) → all units in faction
    /// - Some(vec of ids) → only matching entity IDs
    pub targets: Option<Vec<u32>>,
}

impl ActiveBuffGroup {
    /// Check if this buff group targets a specific entity.
    ///
    /// # Examples
    ///
    /// ```
    /// use micro_core::config::{ActiveBuffGroup, ActiveModifier, ModifierType};
    ///
    /// let group_none = ActiveBuffGroup { modifiers: vec![], remaining_ticks: 10, targets: None };
    /// assert!(!group_none.targets_entity(1));
    ///
    /// let group_all = ActiveBuffGroup { modifiers: vec![], remaining_ticks: 10, targets: Some(vec![]) };
    /// assert!(group_all.targets_entity(1));
    ///
    /// let group_specific = ActiveBuffGroup { modifiers: vec![], remaining_ticks: 10, targets: Some(vec![1, 2]) };
    /// assert!(group_specific.targets_entity(1));
    /// assert!(!group_specific.targets_entity(3));
    /// ```
    pub fn targets_entity(&self, entity_id: u32) -> bool {
        match &self.targets {
            None => false,                         // Dormant — no units
            Some(ids) if ids.is_empty() => true,   // All units in faction
            Some(ids) => ids.contains(&entity_id), // Specific units
        }
    }
}

/// A single stat modifier within a buff group.
#[derive(Debug, Clone)]
pub struct ActiveModifier {
    pub stat_index: usize,
    pub modifier_type: ModifierType,
    pub value: f32,
}

/// How a modifier is applied to a stat.
#[derive(Debug, Clone, PartialEq)]
pub enum ModifierType {
    /// stat_effective = stat_base × value
    Multiplier,
    /// stat_effective = stat_base + value
    FlatAdd,
}

#[derive(Resource, Debug, Clone)]
pub struct DensityConfig {
    pub max_density: f32,
}
impl Default for DensityConfig {
    fn default() -> Self {
        Self { max_density: 50.0 }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_all_resources_impl_default() {
        let _f = FactionBuffs::default();
        let _b = BuffConfig::default();
        let _d = DensityConfig::default();
    }
}
