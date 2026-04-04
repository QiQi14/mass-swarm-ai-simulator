# Target Task: task_02_ws_server

## Touched Files
- `micro-core/src/bridges/ws_server.rs` (created)
- `micro-core/src/bridges/mod.rs` (modified)

## Contract Fulfillment
- Implemented `pub async fn start_server(mut rx: tokio::sync::broadcast::Receiver<String>)`.
- Used Tokio and tungstenite to create a WebSocket server on `127.0.0.1:8080`.
- Broadcasted strings extracted from `rx` to all actively connected clients.
- Ensured any disconnected clients are detected and removed from broadcast list.
- `cargo clippy` and `cargo check` compile successfully with 0 warnings.

## Deviations/Notes
- Ignored return value `let _ = clients_lock.remove(i);` to prevent `futures_util::stream::SplitSink` unused must-use clippy warning.
