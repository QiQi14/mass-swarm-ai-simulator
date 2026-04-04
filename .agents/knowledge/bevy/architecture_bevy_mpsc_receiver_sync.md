# Lesson: Bevy Resource Thread Safety (`Send + Sync`)

**Category:** architecture
**Discovered:** task_07_zmq_bridge_plugin (2026-04-03)
**Severity:** high

## Context
When maintaining data structures or channels connecting the synchronous main Bevy ECS thread with an asynchronous or separate thread runtime (e.g. Tokio / WebSockets or ZeroMQ), you must embed these channels inside a standard Bevy `Resource`.

## Problem
In Rust `std::sync::mpsc::Receiver<T>` implements `Send` but explicitly does NOT implement `Sync`. 
Bevy's `Resource` trait, however, dictates that all Resources must implement both `Send + Sync`. Attempting to wrap an `mpsc::Receiver` directly as a field inside a struct that derives `Resource` will fail compilation, pointing to an unsatisfied `Resource` constraint. 

## Correct Approach
Wrap the `mpsc::Receiver` inside a `std::sync::Mutex` to satisfy the `Sync` marker for the Resource. Note that standard Bevy channel practices (e.g., crossbeam implementations or specific `bevy::tasks` channels) bypass this, but for raw `std::sync::mpsc`, a `Mutex` is strictly required.

*(Note: Since it's only meant to be polled by one unique Bevy system polling at a time or one exclusive thread, acquiring the lock is virtually contention-free).*

## Example
- ❌ What the executor did:
```rust
#[derive(Resource)]
pub struct AiBridgeChannels {
    pub state_tx: mpsc::SyncSender<String>,
    pub action_rx: mpsc::Receiver<String>, // COMPILE ERROR: missing `Sync` trait
}

// ... Using try_recv:
channels.action_rx.try_recv()
```

- ✅ What it should be:
```rust
#[derive(Resource)]
pub struct AiBridgeChannels {
    pub state_tx: mpsc::SyncSender<String>,
    pub action_rx: std::sync::Mutex<mpsc::Receiver<String>>, // satisfies Send + Sync
}

// ... Using try_recv:
channels.action_rx.lock().unwrap().try_recv()
```
