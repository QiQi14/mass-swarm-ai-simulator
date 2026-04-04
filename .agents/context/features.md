# Feature Ledger (Logic Ledger)

> A concise registry of implemented features. Each entry is 3-5 lines max.
> For deep context, follow the archive pointer.
>
> **Who updates this:** The Planner agent, at the START of each new planning session,
> summarizes the previous completed feature before planning the next one.

<!-- 
FORMAT for each entry:

### [Feature Name]
**Completed:** YYYY-MM-DD | **Archive:** `.agents/history/[folder]/`

[2-3 line summary: what it does, key design decisions, non-obvious behavior]

**Key files:** `path/to/file.ts`, `path/to/other.ts`  
**Depends on:** [other features, or "None"]
-->

---

### Phase 1 Micro-Phase 1: Minimal ECS Skeleton
**Completed:** 2026-04-03 | **Archive:** `.agents/history/20260403_171957_p1_mp1_rust_bevy_scaffold_minimal_ecs/`

Sets up headless Bevy 0.18 app running at 60 TPS with minimal ECS capabilities (Position, Velocity, Team) and basic movement/spawn logic. Serves as the foundation for bridges.

**Key files:** `micro-core/src/main.rs`, `micro-core/src/components/*.rs`, `micro-core/src/systems/*.rs`
**Depends on:** None

---

### Phase 1 Micro-Phase 2: WebSocket Bridge & Delta-Sync
**Completed:** 2026-04-03 | **Archive:** `.agents/history/20260404_095812_phase_1_micro_phase_2_websocket_bridge/`

Adds a tokio-powered WebSocket server (`ws_server.rs`) broadcasting entity delta-sync updates to connected browser clients. Introduces `BroadcastSender` resource, `ws_sync_system` (queries `Changed<Position>`), and `ws_protocol.rs` with `SyncDelta` message envelope. Non-blocking — runs in a background thread alongside the Bevy ECS loop.

**Key files:** `micro-core/src/bridges/ws_server.rs`, `micro-core/src/bridges/ws_protocol.rs`, `micro-core/src/systems/ws_sync.rs`
**Depends on:** Phase 1 MP1

---

### Phase 1 Micro-Phase 3: ZeroMQ Bridge + Stub AI Round-Trip
**Completed:** 2026-04-04 | **Archive:** `.agents/history/20260404_095812_phase_1_micro_phase_2_websocket_bridge/`

Adds the ZeroMQ REQ/REP AI bridge (`zmq_bridge/`) with a Bevy state machine (`SimState::Running`/`WaitingForAI`) to gate movement during AI inference. Background tokio thread handles async ZMQ I/O with timeout+fallback to HOLD. Python stub AI (`macro-brain/src/stub_ai.py`) proves the round-trip. `movement_system` is now gated behind `SimState::Running`.

**Key files:** `micro-core/src/bridges/zmq_bridge/`, `micro-core/src/bridges/zmq_protocol.rs`, `macro-brain/src/stub_ai.py`
**Depends on:** Phase 1 MP1, Phase 1 MP2

---

### Phase 1 Micro-Phase 4: Debug Visualizer + Bidirectional WS
**Completed:** 2026-04-04 | **Archive:** `.agents/history/20260404_115529_phase_1_micro_phase_4_debug_visualizer_bidirectional_ws/`

Browser-based debug dashboard (`debug-visualizer/`) with real-time entity rendering on HTML5 Canvas. Features: pan/zoom viewport with 100×100 grid, velocity vector overlay, click-to-spawn, Play/Pause toggle, step-mode (advance N ticks then auto-pause), speed multiplier. WS server upgraded for bidirectional communication — incoming commands parsed and executed on ECS via `ws_command_system`. Adds `SimPaused`, `SimSpeed`, `SimStepRemaining` resources. SyncDelta extended with velocity (`dx`/`dy`) data.

**Key files:** `debug-visualizer/index.html`, `debug-visualizer/style.css`, `debug-visualizer/visualizer.js`, `micro-core/src/systems/ws_command.rs`, `micro-core/src/bridges/ws_server.rs`
**Depends on:** Phase 1 MP1, Phase 1 MP2, Phase 1 MP3
