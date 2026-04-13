//! # Cooldown Tracker
//!
//! Per-entity, per-rule cooldown tracking for interaction rules with cooldown_ticks.
//! The engine doesn't know what the cooldown represents — just a tick counter.
//!
//! ## Ownership
//! - **Task:** task_02_interaction_rule_expansion
//! - **Contract:** implementation_plan.md → Contract C3
//!
//! ## Depends On
//! - None

use bevy::prelude::*;
use std::collections::HashMap;

/// Tracks interaction cooldowns per entity per rule.
///
/// Key: (entity_id: u32, rule_index: usize)
/// Value: ticks remaining before this entity can fire this rule again.
///
/// Cleared on environment reset. Ticked each frame by interaction_system.
#[derive(Resource, Debug, Default)]
pub struct CooldownTracker {
    pub cooldowns: HashMap<(u32, usize), u32>,
}

impl CooldownTracker {
    /// Decrement all active cooldowns by 1 tick. Remove expired entries.
    pub fn tick(&mut self) {
        self.cooldowns.retain(|_, ticks| {
            *ticks = ticks.saturating_sub(1);
            *ticks > 0
        });
    }

    /// Check if an entity can fire a specific rule (not on cooldown).
    pub fn can_fire(&self, entity_id: u32, rule_index: usize) -> bool {
        !self.cooldowns.contains_key(&(entity_id, rule_index))
    }

    /// Start cooldown for an entity-rule pair.
    pub fn start_cooldown(&mut self, entity_id: u32, rule_index: usize, ticks: u32) {
        if ticks > 0 {
            self.cooldowns.insert((entity_id, rule_index), ticks);
        }
    }

    /// Remove all cooldowns for a specific entity (called on entity despawn).
    pub fn remove_entity(&mut self, entity_id: u32) {
        self.cooldowns.retain(|&(eid, _), _| eid != entity_id);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cooldown_tracker_default() {
        let tracker = CooldownTracker::default();
        assert!(tracker.cooldowns.is_empty());
    }

    #[test]
    fn test_cooldown_tick_decrements() {
        let mut tracker = CooldownTracker::default();
        tracker.start_cooldown(1, 0, 3);
        assert_eq!(tracker.cooldowns.get(&(1, 0)), Some(&3));
        
        tracker.tick();
        assert_eq!(tracker.cooldowns.get(&(1, 0)), Some(&2));
        
        tracker.tick();
        assert_eq!(tracker.cooldowns.get(&(1, 0)), Some(&1));
        
        tracker.tick();
        assert!(tracker.cooldowns.is_empty());
    }

    #[test]
    fn test_cooldown_can_fire() {
        let mut tracker = CooldownTracker::default();
        assert!(tracker.can_fire(1, 0));
        
        tracker.start_cooldown(1, 0, 1);
        assert!(!tracker.can_fire(1, 0));
        
        tracker.tick();
        assert!(tracker.can_fire(1, 0));
    }

    #[test]
    fn test_cooldown_remove_entity() {
        let mut tracker = CooldownTracker::default();
        tracker.start_cooldown(1, 0, 3);
        tracker.start_cooldown(1, 1, 3);
        tracker.start_cooldown(2, 0, 3);
        
        tracker.remove_entity(1);
        assert!(!tracker.cooldowns.contains_key(&(1, 0)));
        assert!(!tracker.cooldowns.contains_key(&(1, 1)));
        assert!(tracker.cooldowns.contains_key(&(2, 0)));
    }
}
