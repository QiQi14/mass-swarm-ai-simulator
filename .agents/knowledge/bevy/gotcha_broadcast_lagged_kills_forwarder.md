# Rule: Tokio Broadcast RecvError::Lagged Silently Kills Forwarder

**Category:** Architecture, IPC, Bevy-Tokio Bridge

## Context
The WS server forwarder task used `while let Ok(msg) = rx.recv().await` to forward
broadcast messages to connected clients. When the broadcast channel buffer overflowed
(100 messages at 60 TPS = 1.67s), `recv()` returned `Err(RecvError::Lagged)`, which
broke the `while let Ok` loop and **permanently killed the forwarder task**.

This caused ALL entities to be invisible in the debug visualizer — the WS server
accepted connections but never forwarded any messages.

## Strict Directive
When using `tokio::sync::broadcast`, NEVER use `while let Ok(msg) = rx.recv().await`.
Always explicitly match on `RecvError::Lagged` and `continue` (skip lost messages).
Only break on `RecvError::Closed` (sender dropped).

## Example
- **❌ Anti-pattern:**
```rust
while let Ok(msg) = rx.recv().await {
    // Dies silently on Lagged
}
```
- **✅ Best Practice:**
```rust
loop {
    match rx.recv().await {
        Ok(msg) => { /* forward */ }
        Err(RecvError::Lagged(n)) => {
            eprintln!("Skipped {} lagged messages", n);
            continue;
        }
        Err(RecvError::Closed) => break,
    }
}
```
