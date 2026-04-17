# Feature 0: Rust Core — WS Command Enhancements (Tasks R01, R02)

> [!NOTE]
> These tasks modify **only Rust code** in `micro-core/`. They are fully independent of all frontend tasks and can run in parallel with Phase 1. They touch the same file (`ws_command.rs`) but different match arms, so they can be serialized trivially.

---

## Task R01: `spawn_wave` WS Command Enhancement

**Language:** Rust
**Execution Phase:** 0 (Parallel with Phase 1 frontend)
**Live System Impact:** `backward-compatible` — new fields are all `Option`, existing payloads unchanged

### Target Files
- `micro-core/src/systems/ws_command.rs` — MODIFY (`"spawn_wave"` match arm, lines 104–191)

### Context Bindings
- `.agents/context/engine/navigation.md` — §7 Movement System
- `.agents/context/engine/combat.md` — §1 Entity Model (UnitClassId)
- `.agents/skills/rust-code-standards/SKILL.md`
- `micro-core/src/components/movement_config.rs` — `MovementConfig` struct fields
- `micro-core/src/components/unit_class.rs` — `UnitClassId(pub u32)`

### Problem

The current `spawn_wave` handler hardcodes:
```rust
// Line 142-148 — hardcoded defaults, ignoring WS payload
let default_mc = MovementConfig {
    max_speed: 60.0,
    steering_factor: 5.0,
    separation_radius: 6.0,
    separation_weight: 1.5,
    flow_weight: 1.0,
};
// Line 180 — always default class
UnitClassId::default(),
```

The frontend node editor needs to specify per-spawn `class_id` and `movement_config` so that different unit types within the same faction can have different speeds and combat classes.

### Required Changes

#### 1. Parse optional `class_id` from params

```rust
let class_id = cmd
    .params
    .get("class_id")
    .and_then(|v| v.as_u64())
    .map(|v| UnitClassId(v as u32))
    .unwrap_or_default();
```

#### 2. Parse optional `movement` object from params

```rust
let movement_config = if let Some(mc_json) = cmd.params.get("movement") {
    MovementConfig {
        max_speed: mc_json.get("max_speed").and_then(|v| v.as_f64()).unwrap_or(60.0) as f32,
        steering_factor: mc_json.get("steering_factor").and_then(|v| v.as_f64()).unwrap_or(5.0) as f32,
        separation_radius: mc_json.get("separation_radius").and_then(|v| v.as_f64()).unwrap_or(6.0) as f32,
        separation_weight: mc_json.get("separation_weight").and_then(|v| v.as_f64()).unwrap_or(1.5) as f32,
        flow_weight: mc_json.get("flow_weight").and_then(|v| v.as_f64()).unwrap_or(1.0) as f32,
    }
} else {
    // When no movement config in payload, use the same defaults as before
    MovementConfig {
        max_speed: 60.0,
        steering_factor: 5.0,
        separation_radius: 6.0,
        separation_weight: 1.5,
        flow_weight: 1.0,
    }
};
```

#### 3. Parse optional `engagement_range` for TacticalState

```rust
let engagement_range = cmd
    .params
    .get("engagement_range")
    .and_then(|v| v.as_f64())
    .unwrap_or(0.0) as f32;
```

#### 4. Update the spawn bundle

Replace:
```rust
commands.spawn((
    ...
    default_mc,
    UnitClassId::default(),
    crate::components::TacticalState::default(),
    ...
));
```

With:
```rust
commands.spawn((
    ...
    movement_config,
    class_id,
    crate::components::TacticalState {
        engagement_range,
        ..Default::default()
    },
    ...
));
```

#### 5. Update log line

```rust
println!(
    "[WS Command] Spawned {}/{} faction_{} class_{} at ({}, {}) spread {}",
    spawned_count, amount, faction_id, class_id.0, x, y, spread
);
```

### New WS Payload Format (Backward Compatible)

```json
{
  "cmd": "spawn_wave",
  "params": {
    "faction_id": 0,
    "amount": 200,
    "x": 400, "y": 500,
    "spread": 100,
    "stats": [{"index": 0, "value": 100}],
    "class_id": 1,
    "engagement_range": 150.0,
    "movement": {
      "max_speed": 50.0,
      "steering_factor": 5.0,
      "separation_radius": 6.0,
      "separation_weight": 1.5,
      "flow_weight": 0.8
    }
  }
}
```

All new fields are optional — existing payloads without `class_id`, `movement`, or `engagement_range` continue to work identically (defaults applied).

### Unit Tests

Add to the existing `#[cfg(test)] mod tests` block in `ws_command.rs`:

```rust
#[test]
fn test_spawn_wave_with_class_id() {
    // Arrange
    let (mut app, tx) = setup_app();

    let cmd = serde_json::json!({
        "type": "command",
        "cmd": "spawn_wave",
        "params": {
            "amount": 5,
            "faction_id": 1,
            "x": 100.0, "y": 100.0,
            "spread": 20.0,
            "class_id": 3
        }
    });
    tx.send(cmd.to_string()).unwrap();

    // Act
    app.update();

    // Assert
    let mut found_class = false;
    for class in app.world_mut().query::<&UnitClassId>().iter(app.world()) {
        assert_eq!(class.0, 3, "Spawned entity should have class_id 3");
        found_class = true;
    }
    assert!(found_class, "Should have spawned at least one entity with class_id");
}

#[test]
fn test_spawn_wave_with_movement_config() {
    // Arrange
    let (mut app, tx) = setup_app();

    let cmd = serde_json::json!({
        "type": "command",
        "cmd": "spawn_wave",
        "params": {
            "amount": 1,
            "x": 100.0, "y": 100.0,
            "spread": 0.0,
            "movement": {
                "max_speed": 42.0,
                "steering_factor": 3.0,
                "separation_radius": 8.0,
                "separation_weight": 2.0,
                "flow_weight": 0.5
            }
        }
    });
    tx.send(cmd.to_string()).unwrap();

    // Act
    app.update();

    // Assert
    let mc = app.world_mut().query::<&MovementConfig>()
        .iter(app.world())
        .next()
        .expect("Should have spawned one entity with MovementConfig");
    assert!((mc.max_speed - 42.0).abs() < f32::EPSILON, "max_speed should be 42.0");
    assert!((mc.flow_weight - 0.5).abs() < f32::EPSILON, "flow_weight should be 0.5");
}

#[test]
fn test_spawn_wave_without_class_id_defaults_to_zero() {
    // Arrange
    let (mut app, tx) = setup_app();

    let cmd = serde_json::json!({
        "type": "command",
        "cmd": "spawn_wave",
        "params": {
            "amount": 1,
            "x": 50.0, "y": 50.0,
            "spread": 0.0
        }
    });
    tx.send(cmd.to_string()).unwrap();

    // Act
    app.update();

    // Assert — backward compatibility
    let class = app.world_mut().query::<&UnitClassId>()
        .iter(app.world())
        .next()
        .expect("Should have spawned one entity");
    assert_eq!(class.0, 0, "Default class_id should be 0 for backward compatibility");
}

#[test]
fn test_spawn_wave_with_engagement_range() {
    // Arrange
    let (mut app, tx) = setup_app();

    let cmd = serde_json::json!({
        "type": "command",
        "cmd": "spawn_wave",
        "params": {
            "amount": 1,
            "x": 100.0, "y": 100.0,
            "spread": 0.0,
            "engagement_range": 150.0
        }
    });
    tx.send(cmd.to_string()).unwrap();

    // Act
    app.update();

    // Assert
    let ts = app.world_mut().query::<&crate::components::TacticalState>()
        .iter(app.world())
        .next()
        .expect("Should have spawned one entity with TacticalState");
    assert!((ts.engagement_range - 150.0).abs() < f32::EPSILON,
        "engagement_range should be 150.0, got {}", ts.engagement_range);
}
```

### Verification Strategy
```
Test_Type: cargo_test
Test_Stack: Rust/Bevy
Commands:
  - "cd micro-core && cargo test spawn_wave"
  - "cd micro-core && cargo clippy"
  - "cd micro-core && cargo build"
Acceptance_Criteria:
  - "All 4 new tests pass"
  - "All existing spawn_wave tests still pass (backward compat)"
  - "No clippy warnings"
  - "cargo build succeeds"
```

---

## Task R02: `set_interaction` WS Command Enhancement

**Language:** Rust
**Execution Phase:** 0 (Parallel with Phase 1 frontend)
**Live System Impact:** `backward-compatible` — new fields are all `Option` with `#[serde(default)]`

### Target Files
- `micro-core/src/systems/ws_command.rs` — MODIFY (`"set_interaction"` match arm, lines 526–573)

### Context Bindings
- `.agents/context/engine/combat.md` — §2 Combat System (InteractionRule fields)
- `.agents/skills/rust-code-standards/SKILL.md`
- `micro-core/src/rules/interaction.rs` — `InteractionRule` struct (already has all fields with `#[serde(default)]`)

### Problem

The current `set_interaction` handler manually picks out only 3 fields (`source_faction`, `target_faction`, `range`) and hardcodes all `Option` fields as `None`:
```rust
// Lines 558-565 — hardcoded None for all Option fields
source_class: None,
target_class: None,
range_stat_index: None,
mitigation: None,
cooldown_ticks: None,
aoe: None,
penetration: None,
```

The frontend Combat node now sends `source_class`, `target_class`, and `cooldown_ticks` in its compiled output. The `InteractionRule` struct already derives `Serialize, Deserialize` with `#[serde(default)]` on all `Option` fields, so the fix is to **use `serde_json::from_value` instead of manual field picking**.

### Required Changes

#### Replace manual field picking with serde deserialization

The `InteractionRule` struct already has perfect serde support. Replace the manual parsing with:

```rust
"set_interaction" => {
    if let Some(rules_array) = cmd.params.get("rules").and_then(|v| v.as_array()) {
        rule_sets.1.rules.clear();
        for rule_json in rules_array {
            match serde_json::from_value::<crate::rules::InteractionRule>(rule_json.clone()) {
                Ok(rule) => {
                    rule_sets.1.rules.push(rule);
                }
                Err(e) => {
                    eprintln!("[WS Command] Failed to parse InteractionRule: {}", e);
                }
            }
        }
        println!(
            "[WS Command] Set {} interaction rules",
            rule_sets.1.rules.len()
        );
    }
}
```

This is a **strictly superior approach** because:
1. All existing payloads work unchanged (serde defaults fill `None` for missing fields)
2. All new fields (`source_class`, `target_class`, `cooldown_ticks`, `range_stat_index`, `mitigation`, `aoe`, `penetration`) are automatically parsed
3. Error reporting is now per-rule instead of silently skipping malformed rules
4. Less code, less maintenance surface

### New WS Payload Format (Backward Compatible)

**Minimal (existing / backward compat):**
```json
{
  "cmd": "set_interaction",
  "params": {
    "rules": [
      {
        "source_faction": 0,
        "target_faction": 1,
        "range": 15.0,
        "effects": [{"stat_index": 0, "delta_per_second": -10.0}]
      }
    ]
  }
}
```

**Full (new fields from Combat node):**
```json
{
  "cmd": "set_interaction",
  "params": {
    "rules": [
      {
        "source_faction": 0,
        "target_faction": 1,
        "range": 15.0,
        "effects": [{"stat_index": 0, "delta_per_second": -10.0}],
        "source_class": 1,
        "target_class": null,
        "cooldown_ticks": 60,
        "range_stat_index": null,
        "mitigation": null,
        "aoe": null,
        "penetration": null
      }
    ]
  }
}
```

### Unit Tests

Add to the existing `#[cfg(test)] mod tests` block:

```rust
#[test]
fn test_set_interaction_with_class_filter() {
    // Arrange
    let (mut app, tx) = setup_app();

    let cmd = serde_json::json!({
        "type": "command",
        "cmd": "set_interaction",
        "params": {
            "rules": [{
                "source_faction": 0,
                "target_faction": 1,
                "range": 30.0,
                "effects": [{"stat_index": 0, "delta_per_second": -5.0}],
                "source_class": 1,
                "target_class": 2,
                "cooldown_ticks": 60
            }]
        }
    });
    tx.send(cmd.to_string()).unwrap();

    // Act
    app.update();

    // Assert
    let rules = app.world().get_resource::<crate::rules::InteractionRuleSet>().unwrap();
    assert_eq!(rules.rules.len(), 1, "Should have 1 interaction rule");
    let rule = &rules.rules[0];
    assert_eq!(rule.source_class, Some(1), "source_class should be Some(1)");
    assert_eq!(rule.target_class, Some(2), "target_class should be Some(2)");
    assert_eq!(rule.cooldown_ticks, Some(60), "cooldown_ticks should be Some(60)");
}

#[test]
fn test_set_interaction_backward_compat_no_optional_fields() {
    // Arrange
    let (mut app, tx) = setup_app();

    // Legacy payload — no source_class, target_class, cooldown_ticks
    let cmd = serde_json::json!({
        "type": "command",
        "cmd": "set_interaction",
        "params": {
            "rules": [{
                "source_faction": 0,
                "target_faction": 1,
                "range": 15.0,
                "effects": [{"stat_index": 0, "delta_per_second": -10.0}]
            }]
        }
    });
    tx.send(cmd.to_string()).unwrap();

    // Act
    app.update();

    // Assert — backward compatibility
    let rules = app.world().get_resource::<crate::rules::InteractionRuleSet>().unwrap();
    assert_eq!(rules.rules.len(), 1, "Should have 1 interaction rule");
    let rule = &rules.rules[0];
    assert_eq!(rule.source_class, None, "source_class should default to None");
    assert_eq!(rule.target_class, None, "target_class should default to None");
    assert_eq!(rule.cooldown_ticks, None, "cooldown_ticks should default to None");
    assert_eq!(rule.range_stat_index, None, "range_stat_index should default to None");
    assert_eq!(rule.mitigation, None, "mitigation should default to None");
    assert_eq!(rule.aoe, None, "aoe should default to None");
    assert_eq!(rule.penetration, None, "penetration should default to None");
}

#[test]
fn test_set_interaction_malformed_rule_skipped() {
    // Arrange
    let (mut app, tx) = setup_app();

    let cmd = serde_json::json!({
        "type": "command",
        "cmd": "set_interaction",
        "params": {
            "rules": [
                {"source_faction": 0, "target_faction": 1, "range": 10.0, "effects": []},
                {"broken": true},
                {"source_faction": 1, "target_faction": 0, "range": 20.0, "effects": []}
            ]
        }
    });
    tx.send(cmd.to_string()).unwrap();

    // Act
    app.update();

    // Assert — malformed rule skipped, 2 valid rules parsed
    let rules = app.world().get_resource::<crate::rules::InteractionRuleSet>().unwrap();
    assert_eq!(rules.rules.len(), 2, "Should have 2 valid rules, 1 skipped");
}
```

### Verification Strategy
```
Test_Type: cargo_test
Test_Stack: Rust/Bevy
Commands:
  - "cd micro-core && cargo test set_interaction"
  - "cd micro-core && cargo clippy"
  - "cd micro-core && cargo build"
Acceptance_Criteria:
  - "All 3 new tests pass"
  - "All existing tests still pass (backward compat)"
  - "test_interaction_rule_backward_compat in interaction.rs still passes"
  - "No clippy warnings"
  - "cargo build succeeds"
```

---

## Execution Notes

### File Collision

Both R01 and R02 modify `ws_command.rs`, but they touch **different match arms** (lines 104–191 for R01, lines 526–573 for R02). They should be executed **sequentially** within the same dispatch session to avoid merge conflicts.

**Recommended ordering:** R02 first (simpler — replaces ~40 lines with ~12 lines), then R01 (more additive).

### Regression Safety

Both changes are designed with strict backward compatibility:
- **R01:** All new `spawn_wave` fields use `.unwrap_or_default()` — missing fields produce identical behavior to pre-change.
- **R02:** `serde_json::from_value` with `#[serde(default)]` on all `Option` fields — missing fields resolve to `None`, exactly matching the previous hardcoded behavior.

The existing test matrix (`test_fibonacci_spiral_no_overlap`, `test_fibonacci_spiral_skips_walls`, `test_set_terrain_updates_grid`, `test_clear_terrain_resets_all`, `test_load_scenario_updates_next_entity_id`) is completely unaffected.
