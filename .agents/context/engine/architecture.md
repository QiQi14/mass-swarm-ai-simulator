# Architecture

## Pattern
**Tri-Node Decoupled System** — Three independent OS processes communicate exclusively via IPC (ZeroMQ, WebSocket). No shared memory, no direct function calls between nodes. Each node can be replaced, scaled, or debugged independently.

**Endgame:** The Micro-Core compiles to WASM (or native C-ABI) and the trained AI model exports to ONNX, allowing any game engine to consume them with zero logic gaps.

## System Diagram

```
                    PROTOTYPE (Phases 1–4)
┌───────────────────────────────────┐
│       Micro-Core (Rust/Bevy)      │
│  ┌─────────────────────────────┐  │
│  │  ECS: Components + Systems  │  │
│  │  • Position, Velocity, Stat │  │
│  │  • FactionId, UnitClassId   │  │
│  │  • TacticalState, CombatSt  │  │
│  ├─────────────────────────────┤  │
│  │  Spatial Grid (Hash Grid)   │  │
│  ├─────────────────────────────┤  │
│  │  Flow Field (Pathfinding)   │  │
│  ├─────────────────────────────┤  │
│  │  Bridges                    │  │
│  │  • ZMQ Bridge (→ Python)    │  │
│  │  • WS Bridge  (→ Web UI)   │  │
│  └─────────────────────────────┘  │
└──────────┬──────────┬─────────────┘
           │ ZeroMQ   │ WebSocket
           │ REQ/REP  │ (async tokio)
           ▼          ▼
┌──────────────────┐  ┌─────────────────────┐
│ Macro-Brain      │  │ Debug Visualizer    │
│ (Python)         │  │ (Browser)           │
│ • Gymnasium Env  │  │ • Canvas Renderer   │
│ • PPO via RLlib  │  │ • Control Panel     │
│ • State → Tensor │  │ • Delta Sync Buffer │
│ • ONNX Export    │  │ • Bidirectional Cmd  │
└──────────────────┘  └─────────────────────┘

                    INTEGRATION TEST (Phase 5)
┌───────────────────────────────────────────┐
│       Web Engine Integration Demo         │
│  ┌─────────────────────────────────────┐  │
│  │  Micro-Core → WASM (wasm-pack)     │  │
│  │  Macro-Brain → ONNX Runtime Web    │  │
│  │  Renderer: Three.js / Babylon.js   │  │
│  │  All logic in WASM, engine = visuals│  │
│  └─────────────────────────────────────┘  │
└───────────────────────────────────────────┘
```

## Folder Structure

```
mass-swarm-ai-simulator/
├── micro-core/                    # Rust/Bevy headless simulation
│   ├── Cargo.toml
│   └── src/
│       ├── main.rs                # Bevy app entry (MinimalPlugins)
│       ├── components/            # ECS components (Position, Velocity, Team, Health)
│       ├── systems/               # ECS systems (movement, combat, spawning)
│       ├── spatial/               # Hash Grid spatial partitioning
│       ├── pathfinding/           # Dijkstra Maps / Vector Flow Fields
│       └── bridges/
│           ├── zmq_bridge.rs      # ZeroMQ AI bridge (Rust ↔ Python)
│           └── ws_bridge.rs       # WebSocket debug bridge (Rust ↔ Web UI)
├── macro-brain/                   # Python ML / RL training
│   ├── requirements.txt
│   ├── src/
│   │   ├── env/                   # Custom Gymnasium environment
│   │   ├── models/                # Neural network definitions
│   │   ├── training/              # Training loop, PPO config
│   │   └── utils/                 # State vectorization, heatmap compression
│   └── tests/
├── debug-visualizer/              # Browser-based debug UI
│   ├── index.html                 # Single-page static app
│   ├── style.css
│   └── visualizer.js              # Canvas rendering + WS client
├── engine-integration/            # Phase 5: Web engine integration demo
│   ├── index.html                 # Standalone demo page
│   ├── package.json               # Three.js/Babylon.js + onnxruntime-web
│   └── src/
│       ├── wasm/                   # Compiled WASM from micro-core
│       ├── onnx/                   # Exported macro_brain.onnx model
│       └── renderer.js             # 3D engine binding (Three.js or Babylon.js)
├── docs/                          # Human-facing project documentation
│   ├── README.md                  # Project overview & getting started
│   ├── architecture.md            # Architecture deep-dive for developers
│   └── ipc-protocol.md            # IPC message schema reference
├── .agents/                       # Multi-agent framework (docs & tooling)
├── task_tool.sh / .py             # Task state management CLI
├── dispatch.sh / .py              # Agent session dispatch CLI
├── implementation_plan.md         # Planning artifact (Planner-owned)
└── CASE_STUDY.md                  # Original TDD reference
```

## Data Flow

### AI Training Loop (Rust ↔ Python)
```
Rust ECS tick (60 TPS)
  → Every N ticks: serialize state snapshot (JSON)
  → ZMQ REQ → Python
  → Python: vectorize state → NN inference → macro-action
  → ZMQ REP → Rust
  → Rust: apply macro-action to ECS (modify flow field, entity behaviors)
  → Resume simulation
```

### Debug Observation (Rust → Web UI)
```
Rust ECS tick
  → Async tokio task: broadcast delta update (moved, spawned, died)
  → WebSocket → Browser
  → Browser: buffer state → requestAnimationFrame() → canvas redraw
```

### Debug Control (Web UI → Rust)
```
User clicks button / adjusts slider
  → JSON command via WebSocket → Rust
  → Rust: modify ECS resource (spawn, pause, speed, kill)
```

## Key Boundaries

- **Micro-Core is the Source of Truth.** All entity state lives exclusively in Bevy ECS. Python and Web UI are consumers/commanders, never state owners.
- **Python never runs at 60 FPS.** It evaluates every N ticks (≈2 Hz). Rust handles all per-frame movement, collision, and physics autonomously.
- **Web UI never blocks Rust.** The WebSocket bridge runs in an async tokio task alongside the Bevy app. No blocking I/O on the ECS thread.
- **No shared memory between nodes.** All communication is serialized message passing over network protocols (localhost).
- **Each node is independently replaceable.** The Debug Visualizer can be swapped for a Three.js/Babylon.js renderer. Python can be swapped for ONNX Runtime Web. The contracts (message schemas) are the stable interface.
- **10,000+ entities is the hard floor.** The architecture exists to solve the 10K+ entity problem. 1K entities runs trivially on any modern device without optimization — that is not a valid benchmark.
- **WASM-ready from the start.** Core logic should avoid platform-specific APIs that would prevent `wasm32-unknown-unknown` compilation (e.g., raw file I/O, threads). Use abstractions.
