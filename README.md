# Mass-Swarm AI Simulator

**Decoupled Headless Mass-Swarm AI Simulation** — A tri-node architecture for prototyping 10,000+ entity swarm AI with Deep Reinforcement Learning.

## Architecture

```
    Micro-Core (Rust/Bevy)           ← Source of Truth
    60 TPS · 10K+ entities · ECS
         │              │
    ZeroMQ (REQ/REP)    WebSocket (async)
         │              │
         ▼              ▼
    Macro-Brain        Debug Visualizer
    (Python/PyTorch)   (Browser/Canvas)
    RL training ≈2Hz   Real-time observation
```

Three independent OS processes. No shared memory. Each node is independently replaceable.

## Status

> 🚧 **Pre-implementation** — Phase roadmap finalized, project scaffolding not yet started.

See [implementation_plan.md](implementation_plan.md) for the current phase roadmap.

## Documentation

| Document | Audience | Description |
|----------|----------|-------------|
| [docs/README.md](docs/README.md) | Developers | Project overview, quick start guide |
| [docs/architecture.md](docs/architecture.md) | Developers | Architecture deep-dive, data flows, design rationale |
| [docs/ipc-protocol.md](docs/ipc-protocol.md) | Developers | Complete IPC message schema reference |
| [CASE_STUDY.md](CASE_STUDY.md) | All | Original Technical Design Document |
| [implementation_plan.md](implementation_plan.md) | All | Phase roadmap & resolved decisions |

## Tech Stack

| Node | Language | Key Tech |
|------|----------|----------|
| Micro-Core | Rust 2024 | Bevy 0.18 ECS, Tokio, ZeroMQ |
| Macro-Brain | Python 3.14+ | PyTorch 2.11, Ray RLlib, Gymnasium |
| Debug Visualizer | Vanilla JS | HTML5 Canvas, native WebSocket |
| Engine Integration | WASM + JS | wasm-pack, onnxruntime-web, Three.js |

## License

TBD
