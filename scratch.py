import re

with open("/Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/micro-core/src/systems/interaction.rs", "r") as f:
    content = f.read()

# 1. Update imports
content = content.replace("use crate::components::{EntityId, FactionId, Position, StatBlock};", "use crate::components::{EntityId, FactionId, Position, StatBlock, UnitClassId};")

# 2. Update interaction_system param/signature and body
old_body = """pub fn interaction_system(
    telemetry: Option<ResMut<crate::plugins::telemetry::PerfTelemetry>>,
    grid: Res<SpatialHashGrid>,
    rules: Res<InteractionRuleSet>,
    aggro: Res<crate::config::AggroMaskRegistry>,
    combat_buffs: Res<FactionBuffs>,
    buff_config: Res<crate::config::BuffConfig>,
    // Query 1: Purely immutable spatial data.
    // Safe to iterate AND random-access simultaneously (multiple &self borrows).
    q_ro: Query<(Entity, &Position, &FactionId, &EntityId)>,
    // Query 2: Purely mutable stat data.
    // Disjoint from Query 1 (StatBlock ∩ {Position, FactionId} = ∅).
    mut q_rw: Query<&mut StatBlock>,
) {
    let start = telemetry.as_ref().map(|_| std::time::Instant::now());
    if rules.rules.is_empty() {
        if let (Some(mut t), Some(s)) = (telemetry, start) {
            t.interaction_us = s.elapsed().as_micros() as u32;
        }
        return;
    }

    // Pre-calculate fixed delta — ML determinism requires strict fixed timestep
    let tick_delta = 1.0 / 60.0;

    for (source_entity, source_pos, source_faction, source_id) in q_ro.iter() {
        for rule in &rules.rules {
            // Only process rules where this entity is the source faction
            if rule.source_faction != source_faction.0 {
                continue;
            }

            // "The Blinders" — SetAggroMask can disable combat between
            // specific faction pairs (e.g., flanking unit ignores frontline)
            if !aggro.is_combat_allowed(rule.source_faction, rule.target_faction) {
                continue;
            }

            // Abstract damage multiplier via configurable stat index + entity targeting
            let damage_mult = buff_config
                .combat_damage_stat
                .map(|stat_idx| {
                    combat_buffs.get_multiplier(source_faction.0, source_id.id, stat_idx)
                })
                .unwrap_or(1.0);

            // O(K) spatial lookup — only allocation is grid.query_radius's return Vec
            let center = Vec2::new(source_pos.x, source_pos.y);
            let neighbors = grid.query_radius(center, rule.range);

            for &(neighbor_entity, _) in &neighbors {
                // CRITICAL: Prevent self-interaction
                if neighbor_entity == source_entity {
                    continue;
                }

                // O(1) read-only lookup inside iter() — safe: multiple &self borrows
                if let Ok((_, _, neighbor_faction, _)) = q_ro.get(neighbor_entity) {
                    if neighbor_faction.0 != rule.target_faction {
                        continue;
                    }

                    // O(1) mutable lookup — safe: disjoint component set from q_ro
                    // Mut<StatBlock> is dropped at end of this scope before next get_mut()
                    if let Ok(mut stat_block) = q_rw.get_mut(neighbor_entity) {
                        for effect in &rule.effects {
                            if effect.stat_index < stat_block.0.len() {
                                stat_block.0[effect.stat_index] +=
                                    effect.delta_per_second * tick_delta * damage_mult;
                            }
                        }
                    }
                }
            }
        }
    }
    if let (Some(mut t), Some(s)) = (telemetry, start) {
        t.interaction_us = s.elapsed().as_micros() as u32;
    }
}"""

new_body = """pub fn interaction_system(
    telemetry: Option<ResMut<crate::plugins::telemetry::PerfTelemetry>>,
    grid: Res<SpatialHashGrid>,
    rules: Res<InteractionRuleSet>,
    aggro: Res<crate::config::AggroMaskRegistry>,
    combat_buffs: Res<FactionBuffs>,
    buff_config: Res<crate::config::BuffConfig>,
    mut cooldowns: ResMut<crate::config::CooldownTracker>,
    // Query 1: Purely immutable spatial data.
    // Safe to iterate AND random-access simultaneously (multiple &self borrows).
    q_ro: Query<(Entity, &Position, &FactionId, &EntityId, &crate::components::UnitClassId)>,
    // Query 2: Purely mutable stat data.
    // Disjoint from Query 1 (StatBlock ∩ {Position, FactionId} = ∅).
    mut q_rw: Query<&mut StatBlock>,
) {
    let start = telemetry.as_ref().map(|_| std::time::Instant::now());
    
    cooldowns.tick();

    if rules.rules.is_empty() {
        if let (Some(mut t), Some(s)) = (telemetry, start) {
            t.interaction_us = s.elapsed().as_micros() as u32;
        }
        return;
    }

    // Pre-calculate fixed delta — ML determinism requires strict fixed timestep
    let tick_delta = 1.0 / 60.0;

    for (source_entity, source_pos, source_faction, source_id, source_class) in q_ro.iter() {
        for (rule_idx, rule) in rules.rules.iter().enumerate() {
            // Only process rules where this entity is the source faction
            if rule.source_faction != source_faction.0 {
                continue;
            }

            // Unit class filtering — skip if source class doesn't match
            if let Some(required_class) = rule.source_class {
                if source_class.0 != required_class {
                    continue;
                }
            }

            // "The Blinders" — SetAggroMask can disable combat between
            // specific faction pairs (e.g., flanking unit ignores frontline)
            if !aggro.is_combat_allowed(rule.source_faction, rule.target_faction) {
                continue;
            }

            if rule.cooldown_ticks.is_some() {
                if !cooldowns.can_fire(source_id.id, rule_idx) {
                    continue;
                }
            }

            // Abstract damage multiplier via configurable stat index + entity targeting
            let damage_mult = buff_config
                .combat_damage_stat
                .map(|stat_idx| {
                    combat_buffs.get_multiplier(source_faction.0, source_id.id, stat_idx)
                })
                .unwrap_or(1.0);

            let effective_range = if let Some(stat_idx) = rule.range_stat_index {
                q_rw.get(source_entity)
                    .ok()
                    .and_then(|sb| sb.0.get(stat_idx).copied())
                    .unwrap_or(rule.range)
            } else {
                rule.range
            };

            // O(K) spatial lookup — only allocation is grid.query_radius's return Vec
            let center = Vec2::new(source_pos.x, source_pos.y);
            let neighbors = grid.query_radius(center, effective_range);

            let mut applied_any_effect = false;

            for &(neighbor_entity, _) in &neighbors {
                // CRITICAL: Prevent self-interaction
                if neighbor_entity == source_entity {
                    continue;
                }

                // O(1) read-only lookup inside iter() — safe: multiple &self borrows
                if let Ok((_, _, neighbor_faction, _, neighbor_class)) = q_ro.get(neighbor_entity) {
                    if neighbor_faction.0 != rule.target_faction {
                        continue;
                    }

                    if let Some(required_class) = rule.target_class {
                        if neighbor_class.0 != required_class {
                            continue;
                        }
                    }

                    for effect in &rule.effects {
                        let base_delta = effect.delta_per_second * tick_delta * damage_mult;
                        let final_delta = if let Some(ref mit) = rule.mitigation {
                            // Read mitigation stat from target BEFORE get_mut
                            let mit_value = q_rw.get(neighbor_entity)
                                .ok()
                                .and_then(|sb| sb.0.get(mit.stat_index).copied())
                                .unwrap_or(0.0);
                            match mit.mode {
                                crate::rules::MitigationMode::PercentReduction => {
                                    base_delta * (1.0 - mit_value.clamp(0.0, 1.0))
                                }
                                crate::rules::MitigationMode::FlatReduction => {
                                    // mitigation stat acts as flat mitigation *per second*
                                    let abs_reduced = (base_delta.abs() - mit_value * tick_delta).max(0.0);
                                    abs_reduced * base_delta.signum()
                                }
                            }
                        } else {
                            base_delta
                        };

                        if let Ok(mut stat_block) = q_rw.get_mut(neighbor_entity) {
                            if effect.stat_index < stat_block.0.len() {
                                stat_block.0[effect.stat_index] += final_delta;
                                applied_any_effect = true;
                            }
                        }
                    }
                }
            }

            if let Some(cd_ticks) = rule.cooldown_ticks {
                if applied_any_effect {
                    cooldowns.start_cooldown(source_id.id, rule_idx, cd_ticks);
                }
            }
        }
    }
    if let (Some(mut t), Some(s)) = (telemetry, start) {
        t.interaction_us = s.elapsed().as_micros() as u32;
    }
}"""

content = content.replace(old_body, new_body)

# 3. Update tests

# 3.1 setup_app()
content = content.replace("app.init_resource::<crate::config::BuffConfig>();", "app.init_resource::<crate::config::BuffConfig>();\n        app.init_resource::<crate::config::CooldownTracker>();")

# 3.2 Add UnitClassId to spawns
content = content.replace("StatBlock::with_defaults(&[(0, 100.0)]),\n            ))", "StatBlock::with_defaults(&[(0, 100.0)]),\n                crate::components::UnitClassId::default(),\n            ))")

# Append new tests just before the last brace
new_tests_block = """
    #[test]
    fn test_class_filtering_source() {
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 15.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -10.0 }],
                source_class: Some(1), target_class: None, range_stat_index: None, mitigation: None, cooldown_ticks: None,
            }],
        });
        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), crate::components::UnitClassId(0),
        )).id();
        let target = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 5.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), crate::components::UnitClassId::default(),
        )).id();
        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[(source, Vec2::new(0.0, 0.0)), (target, Vec2::new(5.0, 0.0))]);
        }
        app.update();
        let stat = app.world().get::<StatBlock>(target).unwrap();
        assert_eq!(stat.0[0], 100.0);

        *app.world_mut().get_mut::<crate::components::UnitClassId>(source).unwrap() = crate::components::UnitClassId(1);
        app.update();
        let stat = app.world().get::<StatBlock>(target).unwrap();
        assert!(stat.0[0] < 100.0);
    }

    #[test]
    fn test_class_filtering_target() {
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 15.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -10.0 }],
                source_class: None, target_class: Some(2), range_stat_index: None, mitigation: None, cooldown_ticks: None,
            }],
        });
        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), crate::components::UnitClassId::default(),
        )).id();
        let target = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 5.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), crate::components::UnitClassId(0),
        )).id();
        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[(source, Vec2::new(0.0, 0.0)), (target, Vec2::new(5.0, 0.0))]);
        }
        app.update();
        let stat = app.world().get::<StatBlock>(target).unwrap();
        assert_eq!(stat.0[0], 100.0);

        *app.world_mut().get_mut::<crate::components::UnitClassId>(target).unwrap() = crate::components::UnitClassId(2);
        app.update();
        let stat = app.world().get::<StatBlock>(target).unwrap();
        assert!(stat.0[0] < 100.0);
    }

    #[test]
    fn test_dynamic_range() {
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 10.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -10.0 }],
                source_class: None, target_class: None, range_stat_index: Some(3), mitigation: None, cooldown_ticks: None,
            }],
        });
        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0), (3, 50.0)]), crate::components::UnitClassId::default(),
        )).id();
        let target = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 30.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), crate::components::UnitClassId::default(),
        )).id();
        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[(source, Vec2::new(0.0, 0.0)), (target, Vec2::new(30.0, 0.0))]);
        }
        app.update();
        let stat = app.world().get::<StatBlock>(target).unwrap();
        assert!(stat.0[0] < 100.0);
    }

    #[test]
    fn test_mitigation_percent() {
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 15.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -10.0 }],
                source_class: None, target_class: None, range_stat_index: None,
                mitigation: Some(crate::rules::MitigationRule { stat_index: 4, mode: crate::rules::MitigationMode::PercentReduction }),
                cooldown_ticks: None,
            }],
        });
        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), crate::components::UnitClassId::default(),
        )).id();
        let target = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 5.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0), (4, 0.5)]), crate::components::UnitClassId::default(),
        )).id();
        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[(source, Vec2::new(0.0, 0.0)), (target, Vec2::new(5.0, 0.0))]);
        }
        app.update();
        let stat = app.world().get::<StatBlock>(target).unwrap();
        let expected = 100.0 - (10.0 * (1.0 / 60.0) * 0.5);
        assert!((stat.0[0] - expected).abs() < 1e-4);
    }

    #[test]
    fn test_mitigation_flat() {
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 15.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -10.0 }],
                source_class: None, target_class: None, range_stat_index: None,
                mitigation: Some(crate::rules::MitigationRule { stat_index: 4, mode: crate::rules::MitigationMode::FlatReduction }),
                cooldown_ticks: None,
            }],
        });
        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), crate::components::UnitClassId::default(),
        )).id();
        let target = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 5.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0), (4, 5.0)]), crate::components::UnitClassId::default(),
        )).id();
        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[(source, Vec2::new(0.0, 0.0)), (target, Vec2::new(5.0, 0.0))]);
        }
        app.update();
        let stat = app.world().get::<StatBlock>(target).unwrap();
        let expected = 100.0 - (5.0 * (1.0 / 60.0));
        assert!((stat.0[0] - expected).abs() < 1e-4);
    }

    #[test]
    fn test_cooldown_prevents_rapid_fire() {
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 15.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -60.0 }],
                source_class: None, target_class: None, range_stat_index: None, mitigation: None, cooldown_ticks: Some(60),
            }],
        });
        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), crate::components::UnitClassId::default(),
        )).id();
        let target = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 5.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), crate::components::UnitClassId::default(),
        )).id();
        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[(source, Vec2::new(0.0, 0.0)), (target, Vec2::new(5.0, 0.0))]);
        }
        app.update();
        let stat = app.world().get::<StatBlock>(target).unwrap();
        assert!((stat.0[0] - 99.0).abs() < 1e-4);

        for _ in 1..60 {
            app.update();
        }
        let stat = app.world().get::<StatBlock>(target).unwrap();
        assert!((stat.0[0] - 99.0).abs() < 1e-4);

        app.update();
        let stat = app.world().get::<StatBlock>(target).unwrap();
        assert!((stat.0[0] - 98.0).abs() < 1e-4);
    }

    #[test]
    fn test_backward_compat_no_new_fields() {
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 15.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -10.0 }],
                source_class: None, target_class: None, range_stat_index: None, mitigation: None, cooldown_ticks: None,
            }],
        });
        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), crate::components::UnitClassId::default(),
        )).id();
        let target = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 5.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), crate::components::UnitClassId::default(),
        )).id();
        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[(source, Vec2::new(0.0, 0.0)), (target, Vec2::new(5.0, 0.0))]);
        }
        app.update();
        let stat = app.world().get::<StatBlock>(target).unwrap();
        let expected = 100.0 - (10.0 * (1.0 / 60.0));
        assert!((stat.0[0] - expected).abs() < 1e-4);
    }
"""

content = content.replace("}\n}", "}\n" + new_tests_block + "\n}")

with open("/Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/micro-core/src/systems/interaction.rs", "w") as f:
    f.write(content)
