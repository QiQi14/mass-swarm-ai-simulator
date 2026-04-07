# Lesson: Bevy System Parameter Limit Workaround

**Category:** gotcha
**Discovered:** task_b1_ws_rule_commands
**Severity:** medium

## Context
When expanding large ECS systems like `ws_command_system`, you may suddenly encounter compiler errors indicating that the function cannot be used as a Bevy system.

## Problem
Bevy systems have a hard limit of 16 parameters. If you try to pass 17 or more parameters (such as `ResMut`, `Query`, `Commands`), the compiler will produce cryptic trait bound errors or indicate that the function doesn't implement `IntoSystem`.

## Correct Approach
Group related `Res`, `ResMut`, or `Option<ResMut>` parameters into tuples. Bevy treats a tuple of parameters as a single parameter, effectively bypassing the 16-parameter limit. When using this approach, be aware that you might trip the standard `clippy::type_complexity` lint.

## Example
- ❌ What fails (17 parameters):
```rust
pub fn large_system(
    receiver: Res<WsCommandReceiver>,
    mut commands: Commands,
    // ... 11 more params ...
    mut nav_rules: ResMut<NavigationRuleSet>,
    mut int_rules: ResMut<InteractionRuleSet>,
    mut rem_rules: ResMut<RemovalRuleSet>,
    mut active_fog: Option<ResMut<ActiveFogFaction>>,
) { ... }
```

- ✅ What works (Grouped into tuples):
```rust
#[allow(clippy::type_complexity)]
pub fn large_system(
    receiver: Res<WsCommandReceiver>,
    mut commands: Commands,
    // ... 11 more params ...
    mut optionals: (
        Option<ResMut<ActiveFogFaction>>,
        Option<ResMut<ActiveZoneModifiers>>,
    ),
    mut rule_sets: (
        ResMut<NavigationRuleSet>,
        ResMut<InteractionRuleSet>,
        ResMut<RemovalRuleSet>,
    ),
) {
    // Access via tuple indices: rule_sets.0, rule_sets.1, optionals.0
}
```
