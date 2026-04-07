# Usage Guide — Mass-Swarm AI Simulator

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Rust | stable 1.82+ | `rustc --version` |
| Python | 3.8+ | `python3 --version` |
| Browser | Chrome/Firefox/Safari | Any modern browser with WebSocket support |

> [!NOTE]
> No Node.js, npm, or external JS bundlers are needed. The Debug Visualizer is pure HTML/CSS/JS served as static files.

---

## Quick Start

```bash
# Clone and enter the project
cd mass-swarm-ai-simulator

# Start everything (build + simulation + visualizer)
./dev.sh

# Open in browser
open http://127.0.0.1:3000
```

This starts:
1. **Micro-Core** — Rust simulation engine (port `8080` WebSocket)
2. **Debug Visualizer** — Browser dashboard (port `3000` HTTP)

Press `Ctrl+C` to stop all services.

---

## `dev.sh` Options

```bash
./dev.sh                # Normal dev mode
./dev.sh --watch        # Visualizer only (no Rust core)
./dev.sh --smoke        # Run 300-tick smoke test, then exit
./dev.sh --release      # Build with release optimizations
./dev.sh --prod         # Production build (no debug telemetry)
./dev.sh --clean        # Kill leftover processes and free ports
```

### Mode Details

| Mode | Telemetry | Performance | Use Case |
|------|-----------|-------------|----------|
| Default | ON | Debug | Development, debugging |
| `--release` | ON | Optimized | Performance testing |
| `--prod` | **OFF** | Optimized | Deployment, benchmarks |
| `--clean` | N/A | N/A | Kill orphaned processes from prior run |

> [!IMPORTANT]
> `--prod` disables the `debug-telemetry` Cargo feature. PerfTelemetry, FlowFieldSync, and all system timing are compiled out — **zero overhead**.

---

## Architecture Overview

```
┌──────────────────────────┐    WebSocket :8080     ┌───────────────────────────┐
│  Rust Micro-Core         │◄──────────────────────►│  Debug Visualizer (JS)    │
│  (Bevy ECS @ 60 TPS)     │     JSON messages      │  (Dual Canvas @ 60 FPS)   │
│                          │                        │                           │
│  Systems:                │     ┌──────────────┐   │  Layers:                  │
│  • SpatialHashGrid       │────►│  SyncDelta   │──►│  • #canvas-bg (2 TPS)     │
│  • FlowField             │     │  {moved, rem,│   │    - Spatial Grid         │
│  • Interaction (Combat)  │     │   telemetry} │   │    - Flow Field Arrows    │
│  • Removal               │     └──────────────┘   │  • #canvas-entities (60)  │
│  • Movement (Steering)   │     ┌──────────────┐   │    - Entity Dots          │
│  • WaveSpawner           │────►│FlowFieldSync │──►│    - Health Bars          │
│  • WsSync (Broadcast)    │     │ {vectors[]}  │   │    - Death Animations     │
│                          │     └──────────────┘   │    - Selection Highlight  │
│  TelemetryPlugin         │                        │                           │
│  (#[cfg] debug-telemetry)│     ┌──────────────┐   │  UI Panels:               │
│                          │◄────│  WsCommand   │◄──│  • Telemetry + Sparklines │
└──────────────────────────┘     │{cmd, params} │   │  • System Perf Bars       │
                                 └──────────────┘   │  • Entity Inspector       │
                                                    │  • Faction Toggles        │
                                                    │  • Sim Controls           │
                                                    └───────────────────────────┘
```

---

## Debug Visualizer Controls

### Canvas Viewport
| Action | Control |
|--------|---------|
| **Pan** | Click + drag |
| **Zoom** | Scroll wheel (toward pointer) |
| **Reset view** | Double-click |
| **Spawn swarm** | Click empty area |
| **Inspect entity** | Click near an entity |

### Sidebar Panels

| Panel | Description |
|-------|-------------|
| **Telemetry** | TPS, tick count, entity counts with sparkline graphs |
| **System Performance** | Color-coded bars: green <200µs, yellow <1ms, red >1ms |
| **Entity Inspector** | ID, faction, position, velocity, stats of selected entity |
| **Simulation Controls** | Play/Pause, Step N ticks |
| **Faction Behavior** | Toggle factions between Static/Brain modes |
| **Viewport Layers** | Toggle overlays: Grid, Spatial Hash, Flow Field, Velocity, Fog |

### Keyboard Reference
| Key | Action |
|-----|--------|
| — | All controls are mouse/button based |

### Layer Toggles
- **Coordinate Grid** — 100×100 world unit grid with major lines
- **Spatial Hash Grid** — Yellow overlay showing hash grid cell boundaries
- **Flow Field Arrows** — Directional arrows per faction (appears after Task 03 integration)
- **Velocity Vectors** — White lines showing each entity's movement direction
- **Fog of War** — Radial darkness gradient from center

---

## Running Individual Components

### Micro-Core Only (no visualizer)
```bash
cd micro-core
cargo run
```

### Micro-Core with Smoke Test
```bash
cd micro-core
cargo run -- --smoke-test
```

### Micro-Core with Custom Entity Count (after Task 08)
```bash
cd micro-core
cargo run -- --entity-count 10000
```

### Visualizer Only (connect to existing Micro-Core)
```bash
cd debug-visualizer
python3 -m http.server 3000 --bind 127.0.0.1
# Open http://127.0.0.1:3000
```

### Tests
```bash
cd micro-core
cargo test                        # All tests
cargo test ws_sync                # WS sync tests only
cargo test ws_command             # WS command tests only
cargo test spatial                # Spatial hash grid tests
cargo test flow_field             # Flow field tests
cargo test --no-default-features  # Test without telemetry (production path)
```

---

## Rust Logging

Set `RUST_LOG` environment variable for log verbosity:

```bash
RUST_LOG=info cargo run           # Info-level logs
RUST_LOG=debug cargo run          # Debug-level logs
RUST_LOG=micro_core=trace cargo run  # Trace-level for micro-core only
```

> [!TIP]
> Text logs go to the Terminal. Numeric telemetry goes to the Browser via WebSocket. This separation prevents V8 GC stutter from string parsing at 60 TPS.

---

## Troubleshooting

### Port Already in Use
```bash
# Recommended: use the built-in cleanup
./dev.sh --clean

# Manual alternative
lsof -ti:8080 | xargs kill   # Kill WS port user
lsof -ti:3000 | xargs kill   # Kill HTTP port user
```

> [!TIP]
> `dev.sh` automatically kills orphaned port processes on startup. If you closed
> the terminal without Ctrl+C, just re-run `./dev.sh` — it will self-heal.

### WebSocket Won't Connect
1. Ensure Micro-Core is running (`cargo run`)
2. Check browser console for connection errors
3. The visualizer auto-reconnects every 2 seconds

### No Entities Appear
1. Click on the canvas to spawn a wave
2. Or wait for the initial spawn system (spawns on tick 1)
3. Check terminal logs for `[WS Command] Spawned...`

### Performance Issues at 10K Entities
1. Use `./dev.sh --release` for optimized builds
2. Disable Velocity Vectors and Fog of War toggles
3. Zoom out to reduce per-entity rendering cost

---

## File Structure

```
mass-swarm-ai-simulator/
├── dev.sh                          # ← Start here
├── USAGE.md                        # ← You are here
├── TRAINING_STATUS.md              # Training run tracker
├── ROADMAP.md                      # Phase roadmap (1-3 ✅, 4-5 ⬜)
├── CASE_STUDY.md                   # Original technical design document
├── micro-core/                     # Rust simulation engine
│   ├── Cargo.toml                  # Features: debug-telemetry
│   └── src/
│       ├── main.rs                 # Bevy app entry point
│       ├── lib.rs                  # Module barrel
│       ├── config.rs               # SimulationConfig, Phase 3 resources
│       ├── terrain.rs              # 3-tier terrain (Passable/Destructible/Permanent)
│       ├── visibility.rs           # Bit-packed Fog of War
│       ├── plugins/                # Conditional compilation gates
│       ├── components/             # ECS components (Position, Velocity, Faction, etc.)
│       ├── systems/                # Bevy systems
│       │   ├── movement.rs         # Composite steering + soft cost
│       │   ├── flow_field_update.rs# Dijkstra flow fields + zone modifiers
│       │   ├── directive_executor.rs# Multi-Master Arbitration (8-action vocabulary)
│       │   ├── engine_override.rs  # Tier 1 per-entity velocity override
│       │   ├── state_vectorizer.rs # 50×50 density heatmaps
│       │   ├── ws_sync.rs          # State broadcast
│       │   ├── ws_command.rs       # WS command receiver
│       │   └── ...
│       ├── bridges/                # IPC bridges
│       │   ├── ws_server.rs        # Tokio WebSocket server
│       │   ├── ws_protocol.rs      # WS message DTOs
│       │   ├── zmq_bridge/         # ZeroMQ Python bridge
│       │   └── zmq_protocol.rs     # MacroDirective, AiResponse, StateSnapshot
│       ├── spatial/                # Spatial hash grid
│       └── pathfinding/            # Flow field navigation
├── macro-brain/                    # Python RL training
│   ├── requirements.txt            # SB3, sb3-contrib, gymnasium, torch
│   ├── src/
│   │   ├── env/
│   │   │   ├── swarm_env.py        # Gymnasium environment (ZMQ REP socket)
│   │   │   ├── rewards.py          # 5-component reward + P5 anti-exploit
│   │   │   └── spaces.py           # Observation & action space definitions
│   │   ├── training/
│   │   │   ├── train.py            # MaskablePPO entry point
│   │   │   ├── curriculum.py       # 2-stage curriculum callback
│   │   │   └── callbacks.py        # Training stats callback
│   │   └── utils/
│   │       ├── terrain_generator.py# Procedural terrain (BFS-verified)
│   │       └── vectorizer.py       # State snapshot → numpy arrays
│   └── tests/                      # 33 Python tests
├── debug-visualizer/               # Browser-based debug UI
│   ├── index.html                  # Multi-panel layout
│   ├── style.css                   # Dark theme + perf bars
│   └── visualizer.js               # Rendering + telemetry
└── docs/                           # Documentation
    ├── architecture.md             # System architecture
    ├── ipc-protocol.md             # ZMQ + WS message schemas
    └── study/                      # 12 engineering case studies
```

---

## Running RL Training

### Prerequisites
```bash
cd macro-brain
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Training Commands
```bash
# Start Rust simulation first (required for ZMQ)
cd micro-core && cargo run &

# Then start training
cd macro-brain
source venv/bin/activate

# Basic training (flat map, 100K steps)
python -m src.training.train --timesteps 100000

# With curriculum auto-promotion
python -m src.training.train --timesteps 100000 --curriculum

# Monitor training
tensorboard --logdir=./tb_logs/
```

### Training Outputs
| Artifact | Location | Purpose |
|----------|---------|---------|
| Checkpoints | `macro-brain/checkpoints/` | Model snapshots (every 10K steps) |
| TensorBoard | `macro-brain/tb_logs/` | Reward curves, loss, episode stats |

