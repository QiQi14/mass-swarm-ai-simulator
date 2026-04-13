# Task 01: Rust Zone Duration Config

```yaml
Task_ID: task_01_rust_zone_duration_config
Execution_Phase: 1
Model_Tier: advanced
Feature: "Curriculum Stage 2 & 3 Adjustment"
Dependencies: None
Context_Bindings:
  - context/engine-mechanics
  - context/ipc-protocol
  - skills/rust-code-standards
Target_Files:
  - micro-core/src/bridges/zmq_protocol/payloads.rs
  - micro-core/src/config/buff.rs
  - micro-core/src/bridges/zmq_bridge/reset.rs
  - micro-core/src/systems/directive_executor/executor.rs
```

## Objective

Make the `SetZoneModifier` duration **configurable** via the `AbilityConfigPayload` instead of being hardcoded to `120` ticks. The value will be sent from Python in the reset payload and stored in the existing `BuffConfig` resource.

---

## Strict Instructions

### Step 1: Add field to `AbilityConfigPayload`

**File:** `micro-core/src/bridges/zmq_protocol/payloads.rs`

Add a new field `zone_modifier_duration_ticks` to the `AbilityConfigPayload` struct with a serde default for backward compatibility:

```rust
// Add this free function ABOVE the struct or at module level:
fn default_zone_duration() -> u32 { 120 }

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
```

**Critical:** Use `#[serde(default = "default_zone_duration")]` so that old reset payloads (without the field) still deserialize correctly with `120` as the default.

### Step 2: Add field to `BuffConfig`

**File:** `micro-core/src/config/buff.rs`

Add `zone_modifier_duration_ticks: u32` to the `BuffConfig` struct:

```rust
#[derive(Resource, Debug, Clone)]
pub struct BuffConfig {
    /// Cooldown ticks after any buff expires. Default: 0.
    pub cooldown_ticks: u32,
    /// Which stat_index in active buffs controls movement speed multiplier.
    pub movement_speed_stat: Option<usize>,
    /// Which stat_index in active buffs controls combat damage multiplier.
    pub combat_damage_stat: Option<usize>,
    /// Duration in ticks for SetZoneModifier effects. Default: 120.
    pub zone_modifier_duration_ticks: u32,
}
```

**Update the `Default` impl** (BuffConfig currently derives `Default`, which gives `0` for `u32`). You MUST replace `#[derive(Default)]` with a manual `Default` impl:

```rust
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
```

### Step 3: Wire the field in reset handler

**File:** `micro-core/src/bridges/zmq_bridge/reset.rs`

In the `reset_environment_system` function, find the existing block (around line 218-222):

```rust
if let Some(cfg) = &reset.ability_config {
    buff_config.cooldown_ticks = cfg.buff_cooldown_ticks;
    buff_config.movement_speed_stat = cfg.movement_speed_stat;
    buff_config.combat_damage_stat = cfg.combat_damage_stat;
}
```

Add one line:

```rust
if let Some(cfg) = &reset.ability_config {
    buff_config.cooldown_ticks = cfg.buff_cooldown_ticks;
    buff_config.movement_speed_stat = cfg.movement_speed_stat;
    buff_config.combat_damage_stat = cfg.combat_damage_stat;
    buff_config.zone_modifier_duration_ticks = cfg.zone_modifier_duration_ticks;
}
```

### Step 4: Use config in directive executor

**File:** `micro-core/src/systems/directive_executor/executor.rs`

**4a.** Add `Res<BuffConfig>` to the system parameters of `directive_executor_system`. The `BuffConfig` type is already importable from `crate::config::BuffConfig`. Add it alongside the existing parameters:

```rust
pub fn directive_executor_system(
    mut latest: ResMut<LatestDirective>,
    mut nav_rules: ResMut<NavigationRuleSet>,
    mut int_rules: ResMut<crate::rules::InteractionRuleSet>,
    mut buffs: ResMut<FactionBuffs>,
    mut zones: ResMut<ActiveZoneModifiers>,
    mut aggro: ResMut<AggroMaskRegistry>,
    mut sub_factions: ResMut<ActiveSubFactions>,
    mut faction_query: Query<(Entity, &Position, &mut FactionId)>,
    buff_config: Res<crate::config::BuffConfig>,  // NEW
) {
```

**4b.** In the `SetZoneModifier` match arm (around line 133-148), replace the hardcoded `120`:

```rust
MacroDirective::SetZoneModifier {
    target_faction,
    x, y, radius, cost_modifier,
} => {
    zones.zones.push(ZoneModifier {
        target_faction,
        x, y, radius, cost_modifier,
        ticks_remaining: buff_config.zone_modifier_duration_ticks,
    });
}
```

---

## Anti-Patterns

- **DO NOT** add a `ticks_remaining` field to `MacroDirective::SetZoneModifier`. The duration is a game-config parameter, not a per-cast decision.
- **DO NOT** change the serde schema of `MacroDirective::SetZoneModifier` — it stays as-is.
- **DO NOT** touch any existing test assertions about `ticks_remaining: 120` in `executor_tests.rs` unless they fail. If they fail because of the new system param, update only the system param setup (add `BuffConfig` to the test app). The test's zone duration should use `BuffConfig::default()` which is 120.

---

## Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: unit
  Test_Stack: Rust (cargo test)
  Acceptance_Criteria:
    - "AbilityConfigPayload deserializes with zone_modifier_duration_ticks when present"
    - "AbilityConfigPayload deserializes WITHOUT zone_modifier_duration_ticks (backward compat → 120)"
    - "BuffConfig::default() has zone_modifier_duration_ticks = 120"
    - "directive_executor_system uses buff_config.zone_modifier_duration_ticks for SetZoneModifier"
    - "All existing tests in micro-core pass (cargo test)"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test"
    - "cd micro-core && cargo test --lib config::buff"
    - "cd micro-core && cargo test --lib bridges::zmq_protocol"
    - "cd micro-core && cargo test --lib systems::directive_executor"
```
