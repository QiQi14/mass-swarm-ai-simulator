//! # Zone Tick System
//!
//! Decrements zone modifier durations each tick.
//! Removes expired zone modifiers.

use crate::config::ActiveZoneModifiers;
use bevy::prelude::*;

pub fn zone_tick_system(mut zones: ResMut<ActiveZoneModifiers>) {
    zones.zones.retain_mut(|z| {
        z.ticks_remaining = z.ticks_remaining.saturating_sub(1);
        z.ticks_remaining > 0
    });
}
