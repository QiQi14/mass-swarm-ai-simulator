# Lesson: Bevy ECS Systems Trigger Clippy too_many_arguments

**Category:** convention
**Discovered:** task_03_ws_bidirectional_commands (2026-04-04)
**Severity:** low

## Context
During QA of the WebSocket bidirectional command system, `cargo clippy` flagged `ws_command_system` for having 8 parameters (exceeding the default limit of 7).

## Problem
Bevy ECS systems commonly require many resource/query parameters since dependency injection is done via function arguments. This is an expected pattern but will always trigger `clippy::too_many_arguments`.

## Correct Approach
For Bevy systems that genuinely need many parameters, suppress the warning with an attribute rather than refactoring into an inferior design:

## Example
- ❌ What happens without suppression: `warning: this function has too many arguments (8/7)`
- ✅ What it should be:
```rust
#[allow(clippy::too_many_arguments)]
pub fn ws_command_system(
    receiver: Res<WsCommandReceiver>,
    mut commands: Commands,
    mut next_id: ResMut<NextEntityId>,
    mut paused: ResMut<SimPaused>,
    mut speed: ResMut<SimSpeed>,
    mut step: ResMut<SimStepRemaining>,
    _config: Res<SimulationConfig>,
    team_query: Query<(Entity, &Team)>,
) { ... }
```
