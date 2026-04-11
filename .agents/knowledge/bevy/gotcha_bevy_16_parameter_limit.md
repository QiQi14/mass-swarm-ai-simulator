# Lesson: Bevy System Parameter Limit Workaround

**Category:** gotcha
**Discovered:** task_b1_ws_rule_commands
**Severity:** medium

## Context
When expanding large ECS systems like `ws_command_system` or `ws_sync_system`, you may suddenly encounter compiler errors indicating that the function cannot be used as a Bevy system.

## Problem
Bevy systems have a hard limit of 16 parameters. If you try to pass 17 or more parameters (such as `ResMut`, `Query`, `Commands`), the compiler will produce cryptic trait bound errors or indicate that the function doesn't implement `IntoSystem`.

## Solution A: `#[derive(SystemParam)]` (Recommended)

Bundle related resources into a named struct. This is the preferred approach for large, stable systems.

```rust
#[derive(bevy::ecs::system::SystemParam)]
pub struct WsSyncTelemetry<'w> {
    pub fog_faction: Res<'w, ActiveFogFaction>,
    pub visibility: Res<'w, FactionVisibility>,
    pub telemetry: Option<ResMut<'w, PerfTelemetry>>,
    pub config: Option<Res<'w, SimulationConfig>>,
    // ... more fields
}

pub fn ws_sync_system(
    query: Query<(&EntityId, &Position)>,
    tick: Res<TickCounter>,
    sender: Res<BroadcastSender>,
    telem: WsSyncTelemetry,  // single param wraps 12+ resources
) { ... }
```

**Used in:** `ws_sync_system` (ws_sync.rs), `reset_environment_system` (reset.rs)

## Solution B: Tuple Grouping (Quick Fix)

Group related parameters into tuples. Simpler but less readable.

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

**Used in:** `ws_command_system` (ws_command.rs)

