# Task 03: WS Bidirectional Command System

Task_ID: task_03_ws_bidirectional_commands
Execution_Phase: A
Model_Tier: advanced

## Target_Files
- `micro-core/src/bridges/ws_protocol.rs` [MODIFY]
- `micro-core/src/bridges/ws_server.rs` [MODIFY]
- `micro-core/src/systems/ws_sync.rs` [MODIFY]
- `micro-core/src/systems/ws_command.rs` [NEW]
- `micro-core/src/config.rs` [MODIFY]
- `micro-core/src/systems/movement.rs` [MODIFY]
- `micro-core/src/systems/mod.rs` [MODIFY]
- `micro-core/src/main.rs` [MODIFY]

## Dependencies
- MP2/MP3 complete (already done)

## Context_Bindings
- context/ipc-protocol
- context/tech-stack
- skills/rust-code-standards

## Strict_Instructions

### Step 1: Extend EntityState in ws_protocol.rs with velocity data

The Debug Visualizer needs velocity data to render direction vectors. Add `dx` and `dy` to `EntityState`:

```rust
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct EntityState {
    pub id: u32,
    pub x: f32,
    pub y: f32,
    pub dx: f32,  // NEW: velocity X component
    pub dy: f32,  // NEW: velocity Y component
    pub team: Team,
}
```

Also add the incoming command type:

```rust
/// Incoming command from the Debug Visualizer (Browser → Rust).
#[derive(Deserialize, Debug, Clone)]
pub struct WsCommand {
    #[serde(rename = "type")]
    pub msg_type: String,
    pub cmd: String,
    #[serde(default)]
    pub params: serde_json::Value,
}
```

### Step 2: Update ws_sync.rs to include velocity

Update the query in `ws_sync_system` to also fetch `&Velocity` and populate `dx`/`dy` in `EntityState`:

```rust
pub fn ws_sync_system(
    query: Query<(&EntityId, &Position, &Velocity, &Team), Changed<Position>>,
    // ...
) {
    for (id, pos, vel, team) in query.iter() {
        moved.push(EntityState {
            id: id.id, x: pos.x, y: pos.y,
            dx: vel.dx, dy: vel.dy,
            team: team.clone(),
        });
    }
}
```

Update the existing ws_sync test to include a `Velocity` component in the spawned test entity.

### Step 3: Add SimPaused, SimSpeed, SimStepRemaining to config.rs

```rust
/// User-controlled simulation pause (from Debug Visualizer).
/// Independent of `SimState::WaitingForAI`.
#[derive(Resource, Debug, Clone, PartialEq)]
pub struct SimPaused(pub bool);

impl Default for SimPaused {
    fn default() -> Self { Self(false) }
}

/// Speed multiplier for entity movement.
#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct SimSpeed {
    pub multiplier: f32,
}

impl Default for SimSpeed {
    fn default() -> Self { Self { multiplier: 1.0 } }
}

/// Step mode: when > 0, movement runs for this many ticks even if paused,
/// then auto-pauses when it reaches 0. Used for single-step debugging.
#[derive(Resource, Debug, Clone, Default)]
pub struct SimStepRemaining(pub u32);
```

Add unit tests for all defaults.

### Step 4: Upgrade ws_server.rs for bidirectional communication

Modify `start_server` signature to accept a command sender:

```rust
pub async fn start_server(
    mut rx: tokio::sync::broadcast::Receiver<String>,
    cmd_tx: std::sync::mpsc::Sender<String>,
) { ... }
```

In the per-connection handler, forward incoming `Message::Text` to Bevy:

```rust
while let Some(Ok(msg)) = stream.next().await {
    if let Message::Text(text) = msg {
        let _ = cmd_tx_clone.send(text.to_string());
    }
}
```

Clone `cmd_tx` for each connection. Update existing test to pass a dummy sender.

### Step 5: Create systems/ws_command.rs

Implement `WsCommandReceiver` resource and `ws_command_system` with these commands:

| Command | Params | Action |
|---------|--------|--------|
| `toggle_sim` | `{}` | Toggle `SimPaused.0` |
| `step` | `{ "count": N }` | Set `SimStepRemaining(N)`, works even when paused |
| `spawn_wave` | `{ "team", "amount", "x", "y" }` | Spawn N entities at (x,y) |
| `set_speed` | `{ "multiplier": F }` | Set `SimSpeed.multiplier` |
| `kill_all` | `{ "team" }` | Despawn all entities of given team |

```rust
#[derive(Resource)]
pub struct WsCommandReceiver(pub Mutex<mpsc::Receiver<String>>);

pub fn ws_command_system(
    receiver: Res<WsCommandReceiver>,
    mut commands: Commands,
    mut next_id: ResMut<NextEntityId>,
    mut paused: ResMut<SimPaused>,
    mut speed: ResMut<SimSpeed>,
    mut step: ResMut<SimStepRemaining>,
    config: Res<SimulationConfig>,
    team_query: Query<(Entity, &Team)>,
) {
    let rx = receiver.0.lock().unwrap();
    while let Ok(json) = rx.try_recv() {
        // Parse and dispatch commands...
        match cmd.cmd.as_str() {
            "toggle_sim" => {
                paused.0 = !paused.0;
                println!("[WS Command] Simulation {}", if paused.0 { "paused" } else { "resumed" });
            }
            "step" => {
                let count = cmd.params.get("count")
                    .and_then(|v| v.as_u64()).unwrap_or(1) as u32;
                step.0 = count;
                println!("[WS Command] Stepping {} tick(s)", count);
            }
            "spawn_wave" => { /* spawn entities at x,y with team */ }
            "set_speed" => { /* update SimSpeed.multiplier */ }
            "kill_all" => { /* despawn entities by team */ }
            other => { eprintln!("[WS Command] Unknown: {}", other); }
        }
    }
}
```

### Step 6: Update systems/mod.rs

Add `pub mod ws_command;`

### Step 7: Update movement.rs

Accept `Res<SimSpeed>` and multiply velocity by `speed.multiplier`:

```rust
pos.x += vel.dx * speed.multiplier;
pos.y += vel.dy * speed.multiplier;
```

Update existing movement tests to insert `SimSpeed::default()`.

### Step 8: Create step_system for step mode

Create a system that decrements `SimStepRemaining` and auto-pauses when done:

```rust
/// Decrements step counter and auto-pauses when step mode completes.
/// Runs every tick when steps remain (regardless of SimPaused).
pub fn step_tick_system(
    mut step: ResMut<SimStepRemaining>,
    mut paused: ResMut<SimPaused>,
) {
    if step.0 > 0 {
        step.0 -= 1;
        if step.0 == 0 {
            paused.0 = true;
            println!("[Step Mode] Step complete, auto-paused");
        }
    }
}
```

This system should run AFTER the movement system in the Update schedule.

### Step 9: Update main.rs

1. Create `mpsc::channel` for WS commands, pass `cmd_tx` to `start_server()`
2. Register resources: `SimPaused`, `SimSpeed`, `SimStepRemaining`, `WsCommandReceiver`
3. Movement system gated by: `in_state(SimState::Running)` AND (`!paused` OR `step_remaining > 0`)
4. Add `ws_command_system` and `step_tick_system` to Update
5. `step_tick_system` must run AFTER movement (use `.after(movement_system)`)

Movement gating logic:
```rust
movement_system
    .run_if(in_state(SimState::Running))
    .run_if(|paused: Res<SimPaused>, step: Res<SimStepRemaining>| !paused.0 || step.0 > 0)
```

Step tick system:
```rust
step_tick_system
    .run_if(in_state(SimState::Running))
    .after(movement_system)
```

## Verification_Strategy
  Test_Type: unit + integration
  Test_Stack: cargo test (Rust)
  Acceptance_Criteria:
    - "cargo check succeeds with zero errors"
    - "cargo clippy has zero warnings"
    - "cargo test passes all existing + new tests"
    - "WsCommand deserializes from JSON with and without params"
    - "SimPaused::default() is false, SimSpeed::default().multiplier is 1.0, SimStepRemaining::default().0 is 0"
    - "EntityState now includes dx, dy fields"
    - "SyncDelta messages include velocity data"
    - "Movement system multiplies velocity by SimSpeed.multiplier"
    - "toggle_sim toggles SimPaused"
    - "step sets SimStepRemaining and movement runs for N ticks then auto-pauses"
    - "cargo run starts without errors"
  Suggested_Test_Commands:
    - "cd micro-core && cargo check"
    - "cd micro-core && cargo clippy"
    - "cd micro-core && cargo test"
