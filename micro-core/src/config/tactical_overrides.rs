use bevy::prelude::*;
use std::collections::HashMap;
use crate::config::unit_registry::TacticalBehavior;

#[derive(Resource, Default, Debug, Clone)]
pub struct FactionTacticalOverrides {
    pub overrides: HashMap<u32, Vec<TacticalBehavior>>,
}
