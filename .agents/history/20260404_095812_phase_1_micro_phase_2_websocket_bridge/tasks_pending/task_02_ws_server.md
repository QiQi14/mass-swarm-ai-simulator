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
