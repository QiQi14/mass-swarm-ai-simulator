---
Task_ID: 07_zmq_bridge_plugin
Execution_Phase: Phase B (Sequential — after Task 06)
Model_Tier: standard
Target_Files:
  - micro-core/src/bridges/zmq_bridge.rs
Dependencies:
  - Task 06 (zmq_protocol_cargo)
Context_Bindings:
  - context/architecture.md
  - context/ipc-protocol.md
  - skills/rust-code-standards
---

# STRICT INSTRUCTIONS

> **Feature:** P1_MP3 — ZeroMQ Bridge + Stub AI Round-Trip
> **Role:** Implement the `ZmqBridgePlugin` — the Bevy plugin that manages the non-blocking AI communication lifecycle using a State Machine pattern.

## Architecture Overview

The plugin uses a **non-blocking State Machine** to pause/resume simulation while waiting for AI:

```
SimState::Running
  └─ ai_trigger_system: every N ticks → serialize state → send to channel → transition to WaitingForAI
  └─ (movement_system is gated behind Running — handled by Task 08)

SimState::WaitingForAI
  └─ ai_poll_system: try_recv() → if response: parse action, resume → transition to Running
```

A background `std::thread` runs a tokio runtime with the async ZMQ I/O loop. Communication between Bevy (sync) and the background thread (async) uses `std::sync::mpsc` channels.

## File: `micro-core/src/bridges/zmq_bridge.rs`

Implement the following items exactly as specified. Follow `skills/rust-code-standards` for all doc comments, test structure, and naming conventions.

### Module doc comment

```rust
//! # ZMQ Bridge Plugin
//!
//! Non-blocking AI communication bridge using ZeroMQ REQ/REP.
//! Uses a Bevy State Machine (SimState) to gate simulation systems
//! while waiting for the Python Macro-Brain to respond.
//!
//! ## Ownership
//! - **Task:** task_07_zmq_bridge_plugin
//! - **Contract:** implementation_plan.md → Proposed Changes → 3. Rust System Layer
//!
//! ## Depends On
//! - `crate::bridges::zmq_protocol::{StateSnapshot, MacroAction, EntitySnapshot, SummarySnapshot, WorldSize}`
//! - `crate::components::{EntityId, Position, Team}`
//! - `crate::config::{SimulationConfig, TickCounter}`
//! - `std::sync::mpsc`
//! - `tokio` (background runtime)
//! - `zeromq` (REQ socket)
```

### 1. SimState Enum

```rust
/// Simulation state for AI communication gating.
///
/// Systems like `movement_system` only run in `Running` state.
/// When `WaitingForAI`, the simulation pauses movement but keeps
/// ticking (tick counter, WS sync, logging continue).
#[derive(States, Debug, Clone, PartialEq, Eq, Hash, Default)]
pub enum SimState {
    #[default]
    Running,
    WaitingForAI,
}
```

### 2. AiBridgeConfig Resource

```rust
/// Configuration for AI bridge timing and resilience.
///
/// Public and serializable so the Debug Visualizer GUI can
/// reconfigure it at runtime via the WS command bridge.
#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct AiBridgeConfig {
    /// Send state to Python every N ticks (default: 30 → ~2 Hz at 60 TPS).
    pub send_interval_ticks: u64,
    /// Timeout in seconds for ZMQ send/recv before falling back to
    /// the default HOLD action. Prevents simulation hang on AI disconnect.
    pub zmq_timeout_secs: u64,
}

impl Default for AiBridgeConfig {
    fn default() -> Self {
        Self {
            send_interval_ticks: 30,
            zmq_timeout_secs: 5,
        }
    }
}
```

### 3. AiBridgeChannels Resource

```rust
/// Channel endpoints for Bevy ↔ background thread communication.
///
/// Capacity is 1 (bounded) — the bridge processes one REQ/REP cycle at a time.
#[derive(Resource)]
pub struct AiBridgeChannels {
    /// Send serialized state snapshots TO the background ZMQ thread.
    pub state_tx: mpsc::SyncSender<String>,
    /// Receive macro action responses FROM the background ZMQ thread.
    pub action_rx: mpsc::Receiver<String>,
}
```

### 4. ZmqBridgePlugin

```rust
/// Bevy plugin that initializes the ZMQ AI bridge.
///
/// Spawns a background thread with a tokio runtime for async ZMQ I/O.
/// Registers `SimState`, `AiBridgeConfig`, `AiBridgeChannels`, and
/// the trigger/poll systems.
pub struct ZmqBridgePlugin;

impl Plugin for ZmqBridgePlugin {
    fn build(&self, app: &mut App) {
        let config = AiBridgeConfig::default();
        let timeout_secs = config.zmq_timeout_secs;

        let (state_tx, state_rx) = mpsc::sync_channel::<String>(1);
        let (action_tx, action_rx) = mpsc::sync_channel::<String>(1);

        std::thread::spawn(move || {
            let rt = tokio::runtime::Runtime::new().unwrap();
            rt.block_on(zmq_io_loop(state_rx, action_tx, timeout_secs));
        });

        app.init_state::<SimState>()
           .insert_resource(config)
           .insert_resource(AiBridgeChannels { state_tx, action_rx })
           .add_systems(Update, (
               ai_trigger_system.run_if(in_state(SimState::Running)),
               ai_poll_system.run_if(in_state(SimState::WaitingForAI)),
           ));
    }
}
```

### 5. Background I/O Loop (with timeout + fallback)

```rust
/// Default fallback action when ZMQ times out or disconnects.
const FALLBACK_ACTION: &str =
    r#"{"type":"macro_action","action":"HOLD","params":{}}"#;

/// Async ZMQ I/O loop running in a dedicated background thread.
///
/// Receives serialized state snapshots from Bevy via `state_rx`,
/// sends them to Python via ZMQ REQ, waits for the REP response
/// with a timeout, and forwards it back to Bevy via `action_tx`.
///
/// On timeout or error, sends a default HOLD fallback and recreates
/// the ZMQ socket (required to reset the strict REQ send/recv alternation).
async fn zmq_io_loop(
    state_rx: mpsc::Receiver<String>,
    action_tx: mpsc::SyncSender<String>,
    timeout_secs: u64,
) {
    use zeromq::{ReqSocket, SocketSend, SocketRecv};
    use tokio::time::{timeout, Duration};

    let mut socket = ReqSocket::new();
    socket.connect("tcp://127.0.0.1:5555")
        .await
        .expect("Failed to connect ZMQ REQ socket to tcp://127.0.0.1:5555");

    println!("[ZMQ Bridge] Connected to tcp://127.0.0.1:5555");

    let zmq_timeout = Duration::from_secs(timeout_secs);

    while let Ok(state_json) = state_rx.recv() {
        // Attempt send with timeout
        let send_result = timeout(zmq_timeout, socket.send(state_json.into())).await;
        match send_result {
            Ok(Ok(())) => {}
            Ok(Err(e)) => {
                eprintln!("[ZMQ Bridge] Send error: {}. Falling back to HOLD.", e);
                let _ = action_tx.send(FALLBACK_ACTION.to_string());
                continue;
            }
            Err(_) => {
                eprintln!(
                    "[ZMQ Bridge] Send timeout ({}s). Python may not be running. Falling back to HOLD.",
                    timeout_secs
                );
                socket = ReqSocket::new();
                let _ = socket.connect("tcp://127.0.0.1:5555").await;
                let _ = action_tx.send(FALLBACK_ACTION.to_string());
                continue;
            }
        }

        // Attempt recv with timeout
        let recv_result = timeout(zmq_timeout, socket.recv()).await;
        match recv_result {
            Ok(Ok(reply)) => {
                let reply_str = String::from_utf8_lossy(&reply.into_vec()[0]).to_string();
                if action_tx.send(reply_str).is_err() {
                    break; // Bevy has shut down
                }
            }
            Ok(Err(e)) => {
                eprintln!("[ZMQ Bridge] Recv error: {}. Falling back to HOLD.", e);
                let _ = action_tx.send(FALLBACK_ACTION.to_string());
            }
            Err(_) => {
                eprintln!(
                    "[ZMQ Bridge] Recv timeout ({}s). Python may be stuck. Falling back to HOLD.",
                    timeout_secs
                );
                socket = ReqSocket::new();
                let _ = socket.connect("tcp://127.0.0.1:5555").await;
                let _ = action_tx.send(FALLBACK_ACTION.to_string());
            }
        }
    }
}
```

### 6. Helper: build_state_snapshot

```rust
/// Builds a StateSnapshot from the current ECS state.
///
/// Queries all entities with EntityId, Position, and Team components
/// and packages them into the IPC-compatible StateSnapshot format.
///
/// # Arguments
/// * `tick` - Current simulation tick
/// * `sim_config` - World dimensions for the world_size field
/// * `query` - All entities with EntityId, Position, and Team
fn build_state_snapshot(
    tick: &TickCounter,
    sim_config: &SimulationConfig,
    query: &Query<(&EntityId, &Position, &Team)>,
) -> StateSnapshot {
    let mut swarm_count: u32 = 0;
    let mut defender_count: u32 = 0;
    let mut entities = Vec::new();

    for (eid, pos, team) in query.iter() {
        let team_str = match team {
            Team::Swarm => {
                swarm_count += 1;
                "swarm"
            }
            Team::Defender => {
                defender_count += 1;
                "defender"
            }
        };

        entities.push(EntitySnapshot {
            id: eid.id,
            x: pos.x,
            y: pos.y,
            team: team_str.to_string(),
        });
    }

    StateSnapshot {
        msg_type: "state_snapshot".to_string(),
        tick: tick.tick,
        world_size: WorldSize {
            w: sim_config.world_width,
            h: sim_config.world_height,
        },
        entities,
        summary: SummarySnapshot {
            swarm_count,
            defender_count,
            // Health is not yet implemented — default to 1.0
            avg_swarm_health: 1.0,
            avg_defender_health: 1.0,
        },
    }
}
```

### 7. Bevy Systems

```rust
/// Triggers AI communication every N ticks.
///
/// Runs only when `SimState::Running`. Builds a state snapshot from
/// the current ECS state, serializes it to JSON, and sends it to the
/// background ZMQ thread. Transitions to `WaitingForAI` on success.
///
/// # Arguments
/// * `tick` - Current tick counter
/// * `config` - AI bridge configuration (send interval)
/// * `sim_config` - World dimensions
/// * `channels` - Channel to background ZMQ thread
/// * `query` - All entities with EntityId, Position, and Team
/// * `next_state` - State transition handle
fn ai_trigger_system(
    tick: Res<TickCounter>,
    config: Res<AiBridgeConfig>,
    sim_config: Res<SimulationConfig>,
    channels: Res<AiBridgeChannels>,
    query: Query<(&EntityId, &Position, &Team)>,
    mut next_state: ResMut<NextState<SimState>>,
) {
    if tick.tick == 0 || tick.tick % config.send_interval_ticks != 0 {
        return;
    }

    let snapshot = build_state_snapshot(&tick, &sim_config, &query);
    let json = serde_json::to_string(&snapshot).unwrap();

    // try_send is non-blocking. If the channel is full (previous request
    // still in flight), skip this tick.
    if channels.state_tx.try_send(json).is_ok() {
        next_state.set(SimState::WaitingForAI);
    }
}

/// Polls for AI response from the background ZMQ thread.
///
/// Runs only when `SimState::WaitingForAI`. Uses non-blocking
/// `try_recv()` so other systems (tick counter, WS sync) keep running.
/// On response (real or fallback HOLD), transitions back to `Running`.
///
/// # Arguments
/// * `channels` - Channel from background ZMQ thread
/// * `next_state` - State transition handle
fn ai_poll_system(
    channels: Res<AiBridgeChannels>,
    mut next_state: ResMut<NextState<SimState>>,
) {
    match channels.action_rx.try_recv() {
        Ok(reply_json) => {
            match serde_json::from_str::<MacroAction>(&reply_json) {
                Ok(action) => {
                    println!("[AI Bridge] Received action: {} (tick resume)", action.action);
                    // TODO: In Phase 3 (Macro-Brain), apply the action to ECS
                }
                Err(e) => {
                    eprintln!("[AI Bridge] Failed to parse macro action: {}", e);
                }
            }
            next_state.set(SimState::Running);
        }
        Err(mpsc::TryRecvError::Empty) => {
            // Still waiting — do nothing, system will run again next tick
        }
        Err(mpsc::TryRecvError::Disconnected) => {
            eprintln!("[AI Bridge] Background thread disconnected!");
            next_state.set(SimState::Running);
        }
    }
}
```

### 8. Required Imports

The file needs these imports at the top (after the module doc comment):

```rust
use bevy::prelude::*;
use serde::{Deserialize, Serialize};
use std::sync::mpsc;

use crate::bridges::zmq_protocol::{
    EntitySnapshot, MacroAction, StateSnapshot, SummarySnapshot, WorldSize,
};
use crate::components::{EntityId, Position, Team};
use crate::config::{SimulationConfig, TickCounter};
```

### 9. Unit Tests

Add tests in the standard `#[cfg(test)] mod tests` block:

1. **`test_ai_bridge_config_default`** — Assert `send_interval_ticks == 30` and `zmq_timeout_secs == 5`.
2. **`test_ai_bridge_config_serialization_roundtrip`** — Serialize `AiBridgeConfig::default()` to JSON, deserialize back, assert equality.
3. **`test_ai_trigger_system_skips_non_interval_ticks`** — Create a minimal Bevy `App` with `ai_trigger_system`, set `TickCounter.tick = 15` (not divisible by 30), run `app.update()`, verify `SimState` is still `Running`.
4. **`test_ai_trigger_system_fires_on_interval`** — Set `TickCounter.tick = 30`, run `app.update()`, verify `SimState` transitions to `WaitingForAI`.

> **Note for test 3 & 4:** You need to insert `AiBridgeConfig`, `AiBridgeChannels` (with real mpsc channels), `SimulationConfig`, and `TickCounter` as resources in the test app. You also need to `init_state::<SimState>()`. Spawn at least one entity with `(EntityId, Position, Team)` components so the query isn't empty.

---

# Verification_Strategy
Test_Type: unit
Test_Stack: cargo test
Acceptance_Criteria:
  - "`cargo check` succeeds."
  - "`cargo clippy` has zero warnings."
  - "`cargo test zmq_bridge` passes all 4 unit tests."
  - "All public items have doc comments per `skills/rust-code-standards`."
Suggested_Test_Commands:
  - `cd micro-core && cargo check`
  - `cd micro-core && cargo clippy`
  - `cd micro-core && cargo test zmq_bridge`
