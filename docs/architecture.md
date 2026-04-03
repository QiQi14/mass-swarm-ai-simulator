# Architecture Guide

> For human developers. If you're an AI agent, read `.agents/context/architecture.md` instead.

## Overview

The system is a **Tri-Node Decoupled Architecture** — three independent OS processes connected by message passing over localhost. No shared memory, no direct function calls, no tight coupling.

```
┌─────────────────────────┐
│    Micro-Core (Rust)    │  ← Source of Truth
│    60 TPS ECS ticks     │
│    10,000+ entities     │
└─────┬───────────┬───────┘
      │ ZeroMQ    │ WebSocket
      │ REQ/REP   │ (async)
      ▼           ▼
┌───────────┐  ┌──────────────────┐
│  Python   │  │  Browser (Canvas) │
│  ML/RL    │  │  Debug Dashboard  │
│  ≈2 Hz    │  │  60 FPS render    │
└───────────┘  └──────────────────┘
```

## The Three Nodes

### Micro-Core (Rust / Bevy ECS)

**Role:** The simulation engine and absolute source of truth for all entity state.

- Runs **headless** — no window, no GPU, no rendering
- Uses Bevy's `MinimalPlugins` + `ScheduleRunnerPlugin` for a fixed 60 TPS loop
- Entity Component System: `Position`, `Velocity`, `Team`, `Health`, `FlowFieldFollower`
- Spatial partitioning via Hash Grid for O(1) neighbor queries at scale
- Vector Flow Fields (Dijkstra Maps) for mass pathfinding — no per-entity A*
- Hosts both IPC servers (ZMQ on `:5555`, WebSocket on `:8080`)

**Why Rust?** Memory safety, no garbage collector pauses, deterministic tick timing, and the ability to compile to both native C-ABI (`.dylib`) and WASM for engine integration.

### Macro-Brain (Python / PyTorch)

**Role:** The strategic "director" that evaluates the global battlefield and issues high-level commands.

- Wraps the Rust simulation as a standard `gymnasium.Env` via ZeroMQ
- Trains using PPO (Proximal Policy Optimization) via Ray RLlib
- Receives compressed state every N ticks (≈2 Hz), **not** every frame
- Issues macro-actions: `FLANK_LEFT`, `TRIGGER_FRENZY`, `RETREAT`, etc.
- Trained model exports to ONNX for production deployment

**Why Python?** The entire ML ecosystem (PyTorch, Ray, Gymnasium) is Python-native. We use Python strictly for training — the trained model is exported to ONNX and runs natively in the game engine.

### Debug Visualizer (Browser / HTML5 Canvas)

**Role:** A lightweight, zero-installation dashboard for observing and controlling the simulation in real-time.

- Single static `index.html` — no build step, no npm, no framework
- Canvas rendering with `requestAnimationFrame()` at the monitor's native refresh rate
- Receives **delta updates** (only entities that changed) to avoid bandwidth bottlenecks
- Bidirectional: send JSON commands back to Rust (spawn, pause, speed, kill)

**Why browser?** Zero installation barrier. Game designers, QA, and stakeholders open a URL and immediately see the simulation. No engine knowledge required.

## Data Flow

### AI Training (Rust ↔ Python)

```
Rust ticks at 60 TPS
  │
  ├─ Every N ticks (~2 Hz):
  │   1. Serialize state snapshot → JSON
  │   2. Send via ZMQ REQ to Python
  │   3. Python: vectorize state → neural net inference
  │   4. Python: return macro-action via ZMQ REP
  │   5. Rust: apply action to ECS (modify flow field, behaviors)
  │
  └─ Between AI evaluations:
      Rust handles all per-frame movement, collision, combat autonomously
```

### Debug Observation (Rust → Browser)

```
Rust ticks at 60 TPS
  │
  └─ Async tokio task (non-blocking):
      1. Diff entity state since last broadcast
      2. Build delta update: { spawned, moved, died }
      3. Broadcast via WebSocket to all connected clients
      4. Browser: buffer payload → redraw on requestAnimationFrame()
```

### Debug Control (Browser → Rust)

```
User clicks "Spawn 500" button
  │
  1. Browser sends: { "type": "command", "cmd": "spawn_wave", "params": {...} }
  2. WebSocket → Rust
  3. Rust: insert command into ECS resource
  4. Next tick: spawning system reads resource and creates entities
```

## Key Design Decisions

### Why Headless? (No GPU)
Running 10,000 entities in a game engine means competing for GPU time with rendering. By going headless, 100% of the CPU is dedicated to simulation logic and AI training. The Debug Visualizer uses its own rendering pipeline (browser's GPU compositor) completely independently.

### Why ZeroMQ? (Not HTTP, not gRPC)
- **Low latency:** ZMQ is a socket library, not a web server — no HTTP overhead
- **REQ/REP pattern:** Natural fit for "send state, get action" synchronous loop
- **No dependencies:** The Rust `zeromq` crate is pure async Rust, no C `libzmq` needed
- **Future-proof:** Can swap to PUB/SUB if we ever need async inference

### Why Delta Syncing? (Not Full State)
Broadcasting 10,000 entity positions 60 times per second = ~24 MB/s of raw JSON. Delta updates (only entities that moved, spawned, or died) reduce this by 90%+ in typical scenarios.

### Why JSON First? (Not Binary)
JSON is human-readable in browser DevTools and Python REPLs. During Phases 1–3, debuggability matters more than throughput. In Phase 4, we swap to Bincode/MessagePack when profiling shows serialization as a bottleneck.

## The Endgame: Engine Integration (Phase 5)

The prototype nodes (Python, Debug Visualizer) are disposable tools. The final production pipeline:

```
 PROTOTYPE                         PRODUCTION
┌──────────────┐                 ┌──────────────────────────┐
│ Rust Core    │  ──wasm-pack──▶ │ WASM module in browser   │
│ (ECS logic)  │  ──cargo lib──▶ │ C-ABI .dylib for Unity   │
└──────────────┘                 └──────────────────────────┘

┌──────────────┐                 ┌──────────────────────────┐
│ Python Model │  ──onnx.export──▶│ ONNX Runtime Web         │
│ (trained AI) │                 │ Unity Sentis / Unreal NNI │
└──────────────┘                 └──────────────────────────┘
```

The game engine's only job becomes: rendering 3D models at the X/Y coordinates provided by the WASM/DLL, playing animations, triggering VFX/audio, and managing user input.

## Scale Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Entity count | **10,000+** | Hard minimum — 1K is trivial without optimization |
| Simulation tick rate | 60 TPS | Deterministic, fixed timestep |
| AI evaluation rate | ≈2 Hz | Every ~30 ticks (configurable) |
| Debug render rate | 60 FPS | Browser's native refresh rate via `requestAnimationFrame` |
| Sustained stability | >10 min | All three nodes running simultaneously |
