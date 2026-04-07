use bevy::prelude::*;

/// Active zone modifiers (flow field cost overlays).
#[derive(Resource, Debug, Default)]
pub struct ActiveZoneModifiers {
    pub zones: Vec<ZoneModifier>,
}

#[derive(Debug, Clone)]
pub struct ZoneModifier {
    pub target_faction: u32,
    pub x: f32,
    pub y: f32,
    pub radius: f32,
    pub cost_modifier: f32,
    pub ticks_remaining: u32,
}

/// Tracks active Tier 1 overrides for intervention flag.
#[derive(Resource, Debug, Default)]
pub struct InterventionTracker {
    pub active: bool,
}

/// Aggro mask: controls which faction pairs can fight.
/// Missing entry = combat allowed (default true).
#[derive(Resource, Debug, Default)]
pub struct AggroMaskRegistry {
    pub masks: std::collections::HashMap<(u32, u32), bool>,
}

impl AggroMaskRegistry {
    /// Missing entry = true (combat allowed by default).
    ///
    /// # Examples
    ///
    /// ```
    /// use micro_core::config::AggroMaskRegistry;
    ///
    /// let reg = AggroMaskRegistry::default();
    /// assert!(reg.is_combat_allowed(0, 1)); // default: all pairs allowed
    /// ```
    pub fn is_combat_allowed(&self, source: u32, target: u32) -> bool {
        *self.masks.get(&(source, target)).unwrap_or(&true)
    }
}

/// Tracks currently active sub-factions.
#[derive(Resource, Debug, Default)]
pub struct ActiveSubFactions {
    pub factions: Vec<u32>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_aggro_mask_default_allows_combat() {
        let mask = AggroMaskRegistry::default();
        assert!(mask.is_combat_allowed(0, 1), "Default should allow combat");
    }

    #[test]
    fn test_aggro_mask_explicit_deny() {
        let mut mask = AggroMaskRegistry::default();
        mask.masks.insert((0, 1), false);
        assert!(!mask.is_combat_allowed(0, 1), "Should deny combat");
        assert!(
            mask.is_combat_allowed(1, 0),
            "Other direction should still allow unless explicitly denied"
        );
    }

    #[test]
    fn test_zone_modifier_fields() {
        let zone = ZoneModifier {
            target_faction: 0,
            x: 10.0,
            y: 20.0,
            radius: 5.0,
            cost_modifier: -50.0,
            ticks_remaining: 10,
        };
        assert_eq!(zone.cost_modifier, -50.0);
    }

    #[test]
    fn test_all_resources_impl_default() {
        let _z = ActiveZoneModifiers::default();
        let _i = InterventionTracker::default();
        let _a = AggroMaskRegistry::default();
        let _s = ActiveSubFactions::default();
    }
}
