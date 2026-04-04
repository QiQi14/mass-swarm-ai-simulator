//! # ZMQ Bridge — Background I/O Loop
//!
//! Async ZMQ REQ/REP communication loop running in a dedicated
//! background thread. Handles timeout-based fallback to HOLD action
//! and socket recreation on failure.
//!
//! ## Ownership
//! - **Task:** task_07_zmq_bridge_plugin
//! - **Contract:** implementation_plan.md → Proposed Changes → 3. Rust System Layer

use std::sync::mpsc;

/// Default fallback action when ZMQ times out or disconnects.
pub(super) const FALLBACK_ACTION: &str =
    r#"{"type":"macro_action","action":"HOLD","params":{}}"#;

/// Async ZMQ I/O loop running in a dedicated background thread.
///
/// Receives serialized state snapshots from Bevy via `state_rx`,
/// sends them to Python via ZMQ REQ, waits for the REP response
/// with a timeout, and forwards it back to Bevy via `action_tx`.
///
/// On timeout or error, sends a default HOLD fallback and recreates
/// the ZMQ socket (required to reset the strict REQ send/recv alternation).
pub(super) async fn zmq_io_loop(
    state_rx: mpsc::Receiver<String>,
    action_tx: mpsc::SyncSender<String>,
    timeout_secs: u64,
) {
    use tokio::time::{timeout, Duration};
    use zeromq::{ReqSocket, Socket, SocketRecv, SocketSend};

    let mut socket = ReqSocket::new();
    socket
        .connect("tcp://127.0.0.1:5555")
        .await
        .expect("Failed to connect ZMQ REQ socket to tcp://127.0.0.1:5555");

    println!("[ZMQ Bridge] Connected to tcp://127.0.0.1:5555");

    let zmq_timeout = Duration::from_secs(timeout_secs);

    while let Ok(state_json) = state_rx.recv() {
        // Attempt send with timeout
        let send_result: Result<Result<(), zeromq::ZmqError>, _> =
            timeout(zmq_timeout, socket.send(state_json.into())).await;
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
        let recv_result: Result<Result<zeromq::ZmqMessage, zeromq::ZmqError>, _> =
            timeout(zmq_timeout, socket.recv()).await;
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
