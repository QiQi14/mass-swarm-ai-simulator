# Decoupled Headless Mass-Swarm AI Simulation

> A tri-node system for prototyping 10,000+ entity swarm AI — Rust handles physics, Python trains the brain, and the browser lets you watch.

## What Is This?

This project implements a "headless simulation" architecture for mass-entity AI and complex swarm behaviors. Instead of building inside a game engine, we decouple the core logic into three independent processes:

| Node | Language | Responsibility |
|------|----------|---------------|
| **Micro-Core** | Rust / Bevy ECS | Deterministic physics, pathfinding, entity state (Source of Truth) |
| **Macro-Brain** | Python / PyTorch | Reinforcement learning, pattern recognition, strategic AI |
| **Debug Visualizer** | HTML5 Canvas / JS | Real-time observation dashboard + bidirectional control |

The nodes communicate via **ZeroMQ** (Rust ↔ Python) and **WebSocket** (Rust ↔ Browser). No shared memory, no tight coupling — each node is independently replaceable.

### Why Not Just Use Unity/Unreal?

Game engines are optimized for rendering, not for running 10,000 entity simulations + ML training simultaneously. By decoupling:
- **Rust** handles tick-by-tick physics at 60 TPS with no rendering overhead
- **Python** sticks to what it's good at: training neural networks
- **The browser** gives instant visual feedback with zero installation
- When done, the trained AI and Rust logic are exported (WASM/C-ABI + ONNX) and dropped into any engine

## Project Structure

```
mass-swarm-ai-simulator/
├── micro-core/              # Rust/Bevy headless simulation
├── macro-brain/             # Python ML/RL training pipeline
├── debug-visualizer/        # Browser-based canvas debug UI
├── engine-integration/      # Phase 5: Web engine integration demo
├── docs/                    # You are here
├── CASE_STUDY.md            # Original technical design document
└── implementation_plan.md   # Current phase roadmap
```

## Quick Start

### Prerequisites
- **Rust** ≥1.94 with `cargo`
- **Python** ≥3.14 with `pip`
- A modern web browser (Chrome, Firefox, Safari)

### 1. Start the Micro-Core (Rust)
```bash
cd micro-core
cargo build
cargo run
# Headless simulation starts at 60 TPS
# ZMQ server listening on tcp://localhost:5555
# WebSocket server on ws://localhost:8080
```

### 2. Start the Macro-Brain (Python)
```bash
cd macro-brain
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m src.training.train
```

### 3. Open the Debug Visualizer
Open `debug-visualizer/index.html` in your browser. It connects to `ws://localhost:8080` automatically.

> **Startup order matters:** Micro-Core first → Macro-Brain second → Visualizer last. The Micro-Core hosts all servers.

## Phase Roadmap

| Phase | Name | What It Delivers |
|-------|------|-----------------|
| **1** | Vertical Slice | Minimal Core + Bridges + Visualizer wired end-to-end |
| **2** | Core Algorithms | Hash Grid, Flow Fields, Combat — 10K+ entities at 60 TPS |
| **3** | Macro-Brain | Python RL training against the live simulation |
| **4** | Integration & Scale | Stress-test at 10K+, binary serialization, perf benchmarks |
| **5** | Web Engine Integration | Rust→WASM + ONNX Runtime Web + Three.js — proves zero-gap integration |

See [implementation_plan.md](../implementation_plan.md) for the full phase breakdown.

## Further Reading

- [Architecture Guide](architecture.md) — Deep-dive into the tri-node system, data flow, and design decisions
- [IPC Protocol](ipc-protocol.md) — Complete message schema reference for all bridges
- [CASE_STUDY.md](../CASE_STUDY.md) — Original technical design document
