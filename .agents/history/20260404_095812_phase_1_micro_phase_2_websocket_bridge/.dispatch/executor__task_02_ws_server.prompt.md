# AGENT ROLE: EXECUTION SPECIALIST

You are an **Execution Specialist** in a multi-agent DAG workflow.
You have been assigned ONE specific task. You implement it with surgical precision.

---

## Your Assignment

| Field   | Value |
|---------|-------|
| Task ID | `task_02_ws_server` |
| Feature | Phase 1 Micro-Phase 2: WebSocket Bridge |
| Tier    | standard |

## Context Loading (Tier-Dependent)

**If your tier is `basic`:**
- Skip all external file reading. Your Task Brief below IS your complete instruction.
- Write the code exactly as specified, then create a changelog and run `./task_tool.sh done task_02_ws_server`.

**If your tier is `standard` or `advanced`:**
1. Read `.agents/context.md` — Thin index pointing to context sub-files
2. Load ONLY the `context/*` sub-files listed in your `Context_Bindings` below
3. Scan `.agents/knowledge/` — Lessons from previous sessions relevant to your task

**Workflow:**
- `.agents/workflows/execution-lifecycle.md` — Your 4-step execution loop

**Rules:**
- `.agents/rules/execution-boundary.md` — Scope and contract constraints
- `./.agents/context/ipc-protocol.md`
- `./.agents/context/architecture.md`

---

## Task Brief

---
Task_ID: 02_ws_server
Execution_Phase: Phase B (Parallelizable)
Model_Tier: standard
Target_Files:
  - micro-core/src/bridges/ws_server.rs
  - micro-core/src/bridges/mod.rs
Dependencies:
  - Task 01 (ws_protocol definitions)
Context_Bindings:
  - context/ipc-protocol.md
  - context/architecture.md
---

# STRICT INSTRUCTIONS

1. **Create `micro-core/src/bridges/ws_server.rs`**
   - This module will be responsible for hosting the WebSocket server.
   - You need to add the following imports:
     ```rust
     use futures_util::{SinkExt, StreamExt};
     use tokio::net::{TcpListener, TcpStream};
     use tokio_tungstenite::tungstenite::Message;
     use std::sync::Arc;
     use tokio::sync::Mutex;
     ```
   - Implement `pub async fn start_server(mut rx: tokio::sync::broadcast::Receiver<String>)`.
   - Inside `start_server`:
     - Bind a `TcpListener` to `127.0.0.1:8080`.
     - Create a shared collection of WebSocket client sinks (e.g. `Arc<Mutex<Vec<futures_util::stream::SplitSink<tokio_tungstenite::WebSocketStream<TcpStream>, Message>>>>`).
     - Spawn a Tokio task that loops over `rx.recv()`. For each `Ok(msg)`, send a `Message::Text(msg.into())` to every sink in the clients list. If a send fails (client disconnected), remove that sink from the vector.
     - While accepting new connections `listener.accept().await`, accept the WebSocket stream using `tokio_tungstenite::accept_async`.
     - Split the stream, store the `Sink` in the shared clients vector. A separate spawned task can be used to handle incoming messages (just discard them for now, or print them) and handle disconnects cleanly if needed. Note: if reading incoming stream yields `None` (connection closed), remove the sink. The broadcast loop alone also prunes dead connections if sending fails.

2. **Update `micro-core/src/bridges/mod.rs`**
   - Add `pub mod ws_server;` so it is compiled.

---

# Verification_Strategy
Test_Type: unit
Test_Stack: cargo
Acceptance_Criteria:
  - "Cargo check compiles the server logic successfully."
  - "Zero Clippy warnings."
Suggested_Test_Commands:
  - `cd micro-core && cargo check`
  - `cd micro-core && cargo clippy`

---

## Shared Contracts

# Phase 1 — Micro-Phase 2: WebSocket Bridge & Delta-Sync

Provide a brief description of the problem, any background context, and what the change accomplishes.
> **Parent:** Phase 1 (Vertical Slice)
> **Scope:** Add a local WebSocket server to track state changes in the headless simulation and broadcast delta updates to connected clients at 60 TPS without blocking the main Bevy thread.

## User Review Required

> [!IMPORTANT]
> **Performance vs Accuracy:** For now (MP2), we will run at 60 TPS and send delta updates on every frame. We will keep the entity count to a small baseline (a few hundred) to ensure smooth operation. We'll introduce bandwidth optimization (throttling or binary protocols) in a later algorithmic phase when we scale to 10k+.

> [!WARNING]
> **Smoke Test Auto-Exit:** Per user feedback, we will NOT remove the smoke test system. Instead, we will wrap it behind a simple command-line flag check (e.g., `if std::env::args().any(|arg| arg == "--smoke-test")`). If the flag is present, the app will auto-exit after `SMOKE_TEST_MAX_TICKS`. Otherwise, it will run forever, allowing clients to connect to the WS server.

## Proposed Changes

### Cargo.toml & Bridge Scaffold

#### [MODIFY] [Cargo.toml](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/micro-core/Cargo.toml)
- Add `tokio = { version = "1.51.0", features = ["rt-multi-thread", "macros", "sync"] }`
- Add `tokio-tungstenite = "0.29.0"`
- Add `futures-util = "0.3.32"` (for Stream splitting)

#### [NEW] [mod.rs](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/micro-core/src/bridges/mod.rs)
- Module barrel file for `ws_server` and `ws_protocol`.

#### [NEW] [ws_protocol.rs](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/micro-core/src/bridges/ws_protocol.rs)
- Defines the `WsMessage` and `EntityState` DTOs (Data Transfer Objects) for JSON serialization.

### Server & System Boundaries

#### [NEW] [ws_server.rs](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/micro-core/src/bridges/ws_server.rs)
- Asynchronous Tokio WS server listening on `127.0.0.1:8080`.
- Listens to a `tokio::sync::broadcast::Receiver<String>`.
- Forwards any received string to all connected WebSocket clients.

#### [NEW] [ws_sync.rs](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/micro-core/src/systems/ws_sync.rs)
- Bevy system that extracts changed entities `Query<(&EntityId, &Position, &Team), Changed<Position>>`.
- Builds a `WsMessage::SyncDelta`.
- Serializes to JSON and sends it via a `BroadcastSender` resource (which wraps `tokio::sync::broadcast::Sender<String>`).

#### [MODIFY] [mod.rs](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/micro-core/src/systems/mod.rs)
- Export `ws_sync.rs`.

#### [MODIFY] [main.rs](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/micro-core/src/main.rs)
- Setup channel: `let (tx, _) = tokio::sync::broadcast::channel::<String>(100);`
- Spawn an OS thread that creates a Tokio runtime and starts `ws_server::start_server`.
- Expose `tx` as a `BroadcastSender` Resource to Bevy.
- Register `ws_sync_system` to `Update`.
- Disable `smoke_test_exit_system`.

---

## Shared Contracts (The Handshake Protocol)

### WebSocket Message Schema (`ws_protocol.rs`)
```rust
use serde::{Deserialize, Serialize};
use crate::components::team::Team;

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct EntityState {
    pub id: u32,
    pub x: f32,
    pub y: f32,
    pub team: Team,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
#[serde(tag = "type")]
pub enum WsMessage {
    SyncDelta {
        tick: u64,
        moved: Vec<EntityState>,
        // Note: For MP2 simplicity, 'spawned' and 'died' are omitted in this initial iteration.
        // We will just send 'moved' since all entities spawn at tick 0 and none die yet.
    }
}
```

### Channel Dependency Injection (`ws_sync.rs`)
```rust
use bevy::prelude::Resource;
use tokio::sync::broadcast::Sender;

#[derive(Resource, Clone)]
pub struct BroadcastSender(pub Sender<String>);
```

### Function Signatures
```rust
// bridges/ws_server.rs
pub async fn start_server(mut rx: tokio::sync::broadcast::Receiver<String>)

// systems/ws_sync.rs
pub fn ws_sync_system(
    query: Query<(&EntityId, &Position, &Team), Changed<Position>>,
    tick: Res<TickCounter>,
    sender: Res<BroadcastSender>,
)
```

---

## DAG Execution Graph

```mermaid
graph TD
    T1["Task 01<br/>Deps & Contracts<br/>(basic)"]
    T2["Task 02<br/>WS Server Task<br/>(standard)"]
    T3["Task 03<br/>Bevy WS Sync System<br/>(standard)"]
    T4["Task 04<br/>Integration Wiring<br/>(standard)"]

    T1 --> T2
    T1 --> T3
    T2 --> T4
    T3 --> T4
```

### Task Splitting & Verification

#### Task 01: Deps & Contracts
- **Tier:** `basic`
- **Output:** Add crates to Cargo.toml. Write `src/bridges/mod.rs` and `src/bridges/ws_protocol.rs`.
- **Verification Strategy:**
  - `Test_Type`: unit
  - `Test_Stack`: cargo
  - `Acceptance_Criteria`: "cargo check succeeds. Structs serialize correctly to JSON."

#### Task 02: WS Server Task
- **Tier:** `standard`
- **Context Bindings:** `context/ipc-protocol.md`, `context/architecture.md`
- **Output:** Write `src/bridges/ws_server.rs`. Implements `start_server`. Uses `tokio::net::TcpListener` and `tokio-tungstenite`. Loops over `rx.recv()` and broadcasts to a managed list of active WebSocket Sink connections. Wait for client disconnects cleanly.
- **Verification Strategy:**
  - `Test_Type`: unit
  - `Test_Stack`: cargo
  - `Acceptance_Criteria`: "cargo clippy succeeds with zero warnings."

#### Task 03: Bevy WS Sync System
- **Tier:** `standard`
- **Context Bindings:** `context/architecture.md`
- **Output:** Write `src/systems/ws_sync.rs`. Extracts `Changed<Position>`, maps to `EntityState`, packages into `WsMessage::SyncDelta`, serializes to string, and sends via `BroadcastSender` resource. Include `BroadcastSender` definition here.
- **Verification Strategy:**
  - `Test_Type`: unit
  - `Test_Stack`: cargo test
  - `Acceptance_Criteria`: "A unit test with a mock Bevy App and mocked Sender successfully catches the emitted JSON string when an entity's Position is manually changed."

#### Task 04: Integration Wiring
- **Tier:** `standard`
- **Context Bindings:** `context/tech-stack.md`
- **Output:** Update `main.rs`. Initialize tokio runtime in a background `std::thread`, pass `rx`, insert `tx` as `BroadcastSender`. Add `ws_sync_system`. Update `main.rs` to only run the `smoke_test_exit_system` if `std::env::args().any(|a| a == "--smoke-test")`.
- **Verification Strategy:**
  - `Test_Type`: manual_steps
  - `Test_Stack`: none
  - `Acceptance_Criteria`: "Run binary without flags, verify it runs forever. Run binary with `--smoke-test`, verify it exits after 5s. With binary running, connect WS client and verify JSON tick streams."
  - `Manual_Steps`:
      - Run `cargo run` in one terminal process via tools.
      - Wait 2 seconds.
      - Use tool to read `ws://localhost:8080` (or `wscat` if available in the environment) to see received JSON stream.

---

## Verification Plan

### Automated Tests
- `cd micro-core && cargo check`
- `cd micro-core && cargo test`

### Manual Verification
- We will write a small python/bash scratch script to connect as a WebSocket client and assert we receive `{"type":"SyncDelta", "tick": <...>, "moved": [...]}` exactly matching our DTO format.
