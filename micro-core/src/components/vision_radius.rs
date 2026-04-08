use bevy::prelude::*;

#[derive(Component, Debug, Clone)]
pub struct VisionRadius(pub f32);

impl Default for VisionRadius {
    fn default() -> Self {
        Self(1000.0)
    }
}
