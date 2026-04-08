use futures_util::{SinkExt, StreamExt};
use std::sync::Arc;
use tokio::net::{TcpListener, TcpStream};
use tokio::sync::Mutex;
use tokio_tungstenite::tungstenite::Message;

pub async fn start_server(
    mut rx: tokio::sync::broadcast::Receiver<String>,
    cmd_tx: std::sync::mpsc::Sender<String>,
) {
    let listener = TcpListener::bind("0.0.0.0:8080")
        .await
        .expect("Failed to bind WebSocket server");

    type WsSink =
        futures_util::stream::SplitSink<tokio_tungstenite::WebSocketStream<TcpStream>, Message>;
    let clients = Arc::new(Mutex::new(Vec::<WsSink>::new()));

    let clients_clone = clients.clone();
    tokio::spawn(async move {
        loop {
            match rx.recv().await {
                Ok(msg) => {
                    let mut clients_lock = clients_clone.lock().await;
                    let mut to_remove = Vec::new();

                    for (i, sink) in clients_lock.iter_mut().enumerate() {
                        if sink.send(Message::Text(msg.clone().into())).await.is_err() {
                            to_remove.push(i);
                        }
                    }

                    for i in to_remove.into_iter().rev() {
                        let _ = clients_lock.remove(i);
                    }
                }
                Err(tokio::sync::broadcast::error::RecvError::Lagged(n)) => {
                    // Buffer overflow — skip lost messages, keep running.
                    // This happens when no WS clients are connected yet.
                    eprintln!("[WS Server] Skipped {} lagged messages", n);
                    continue;
                }
                Err(tokio::sync::broadcast::error::RecvError::Closed) => {
                    // Sender dropped — simulation shut down
                    break;
                }
            }
        }
    });

    while let Ok((stream, _)) = listener.accept().await {
        let clients_clone = clients.clone();
        let cmd_tx_clone = cmd_tx.clone();
        tokio::spawn(async move {
            if let Ok(ws_stream) = tokio_tungstenite::accept_async(stream).await {
                let (sink, mut stream) = ws_stream.split();
                clients_clone.lock().await.push(sink);

                while let Some(msg) = stream.next().await {
                    match msg {
                        Ok(Message::Text(text)) => {
                            let _ = cmd_tx_clone.send(text.to_string());
                        }
                        Err(_) => break,
                        _ => {}
                    }
                }
            }
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use futures_util::StreamExt;
    use tokio::sync::broadcast;
    use tokio_tungstenite::connect_async;

    #[tokio::test]
    async fn test_ws_server_broadcast() {
        let (tx, rx) = broadcast::channel(10);
        let (cmd_tx, _cmd_rx) = std::sync::mpsc::channel();

        // Start server in background
        tokio::spawn(async move {
            start_server(rx, cmd_tx).await;
        });

        // Connect a client with retries
        let req = "ws://127.0.0.1:8080";
        let mut ws_stream = loop {
            match connect_async(req).await {
                Ok((stream, _)) => break stream,
                Err(_) => {
                    tokio::task::yield_now().await;
                }
            }
        };

        // Send a message
        tx.send("test_sync_msg".to_string()).unwrap();

        // Receive the message
        let msg = ws_stream.next().await.expect("Stream closed");
        match msg {
            Ok(Message::Text(text)) => {
                assert_eq!(text.to_string(), "test_sync_msg");
            }
            _ => panic!("Did not receive expected text message"),
        }
    }
}
