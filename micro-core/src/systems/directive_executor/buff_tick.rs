//! # Buff Tick System
//!
//! Decrements active buff group durations each tick.
//! Removes expired groups and starts cooldowns.

use crate::config::FactionBuffs;
use bevy::prelude::*;

pub fn buff_tick_system(
    mut buffs: ResMut<FactionBuffs>,
    buff_config: Res<crate::config::BuffConfig>,
) {
    let mut expired_factions = Vec::new();

    // Tick down all active buff groups per faction
    for (faction, groups) in buffs.buffs.iter_mut() {
        groups.retain_mut(|group| {
            group.remaining_ticks = group.remaining_ticks.saturating_sub(1);
            group.remaining_ticks > 0
        });
        if groups.is_empty() {
            expired_factions.push(*faction);
        }
    }

    // Remove empty faction entries and start cooldowns
    for faction in expired_factions {
        buffs.buffs.remove(&faction);
        if buff_config.cooldown_ticks > 0 {
            buffs.cooldowns.insert(faction, buff_config.cooldown_ticks);
        }
    }

    // Tick cooldowns
    buffs.cooldowns.retain(|_, ticks| {
        *ticks = ticks.saturating_sub(1);
        *ticks > 0
    });
}
