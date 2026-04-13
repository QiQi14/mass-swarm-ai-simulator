# Tech Stack

> **Last updated:** 2026-04-03 — all versions pinned to latest stable releases.

## Node 1: Micro-Core (Simulation Engine)
- **Language:** Rust (Edition 2024, compiler ≥1.94)
- **Framework:** Bevy Engine 0.18 (headless mode — `MinimalPlugins`, no renderer)
- **ECS:** Bevy ECS (Entity Component System)
- **Async Runtime:** Tokio 1.50 (`full`, `rt-multi-thread`)
- **Serialization:** `serde` 1.0.228 + `serde_json` 1.0.149
- **Build Target:** `cdylib` (C-ABI dynamic library for future engine integration)

### Key Dependencies (Cargo.toml)
| Crate | Version | Purpose |
|-------|---------|---------|
| `bevy` | 0.18 | Headless ECS + `ScheduleRunnerPlugin` (fixed 60 TPS) |
| `serde` | 1.0 | State serialization for IPC (with `derive` feature) |
| `serde_json` | 1.0 | JSON encoding/decoding for IPC messages |
| `tokio` | 1.50 | Async networking (WS bridge, ZMQ bridge) |
| `tokio-tungstenite` | 0.29 | WebSocket server for Debug Visualizer |
| `zeromq` | 0.5 | Native async ZeroMQ IPC for Python AI Bridge |

> [!NOTE]
> **Bevy 0.18 headless pattern:** Use `MinimalPlugins.set(ScheduleRunnerPlugin::run_loop(Duration::from_secs_f64(1.0 / 60.0)))` for the fixed-timestep simulation loop. Do NOT use `DefaultPlugins`. Bevy 0.18 also introduces high-level feature collections (`2d`, `3d`, `ui`) — disable all via `default-features = false`.

> [!NOTE]
> **ZeroMQ crate choice:** The `zeromq` 0.5 crate is a native async Rust implementation built on Tokio — no C `libzmq` dependency. Alternative: `rzmq` 0.5 (native Rust, supports `io_uring` on Linux).

## Node 2: Macro-Brain (AI / ML)
- **Language:** Python 3.14+
- **ML Framework:** PyTorch 2.11
- **RL Library:** Ray RLlib (via Ray 2.54)
- **Environment Standard:** Gymnasium 1.2 (Farama Foundation)
- **IPC:** PyZMQ (ZeroMQ Python bindings)
- **Model Export:** ONNX (for production deployment)

### Key Dependencies (requirements.txt)
| Package | Version | Purpose |
|---------|---------|---------|
| `torch` | 2.11 | Neural network training and inference |
| `ray[rllib]` | 2.54 | Distributed RL training (PPO, etc.) |
| `gymnasium` | 1.2 | Standard RL environment interface (`reset()`, `step()`) |
| `pyzmq` | latest | ZeroMQ client for Rust bridge |
| `onnx` | latest | Model export for production integration |

## Node 3: Debug Visualizer (Observation Dashboard)
- **Language:** Vanilla JavaScript (ES2024+)
- **Rendering:** HTML5 `<canvas>` with `requestAnimationFrame()` loop
- **Networking:** Native WebSocket API (`ws://localhost:8080`)
- **Framework:** None — static `index.html`, zero build step
- **Hosting:** Local static file served from Rust or standalone

> [!NOTE]
> No build tooling, no npm, no bundler. The visualizer is a single static HTML page that connects to the Micro-Core's WebSocket server.

## Inter-Process Communication
| Bridge | Protocol | Library |
|--------|----------|---------|
| Rust ↔ Python | ZeroMQ (REQ/REP over TCP) | `zeromq` 0.5 (Rust) / `pyzmq` (Python) |
| Rust ↔ Web UI | WebSocket | `tokio-tungstenite` 0.29 (Rust) / native `WebSocket` (JS) |
| Serialization | JSON (prototype) → Bincode/MessagePack/Protobuf (scale) | `serde_json` |

## Phase 5: Web Engine Integration
- **WASM Tooling:** `wasm-pack` + `wasm-bindgen` (compile Rust → `wasm32-unknown-unknown`)
- **AI Inference:** `onnxruntime-web` (run ONNX model in browser via WebAssembly backend)
- **3D Renderer:** Three.js or Babylon.js (TBD at Phase 5 planning — both are viable)
- **Native C-ABI (reference):** `cbindgen` for C header generation from Rust `cdylib`

> [!NOTE]
> Phase 5 tooling is listed for completeness. These dependencies are NOT required during Phases 1–4. The Micro-Core should remain WASM-compatible by avoiding platform-specific APIs (raw threads, file I/O), but `wasm-pack` compilation is not tested until Phase 5.
