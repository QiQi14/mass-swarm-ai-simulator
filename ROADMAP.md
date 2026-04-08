# Decoupled Headless Mass-Swarm AI Simulation — Phase Roadmap

> **Scope:** Strategic phase breakdown of [CASE_STUDY.md](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/CASE_STUDY.md). Each phase will be expanded into detailed DAG tasks in a subsequent planning pass.

---

## Phase Overview

```mermaid
graph LR
    P1["Phase 1 ✅\nVertical Slice\n(Core + Bridges + Visualizer)"]
    P2["Phase 2 ✅\nCore Algorithms\n(Spatial, Pathfinding, Combat)"]
    P3["Phase 3.5 ✅\nMacro-Brain\n(Python RL & Prod Pipeline)"]
    P4["Phase 4 ⬜\nIntegration\n& Scale"]
    P5["Phase 5 ⬜\nWeb Engine\nIntegration"]

    P1 --> P2
    P2 --> P3
    P3 --> P4
    P4 --> P5

    style P1 fill:#238636,stroke:#2ea043,color:#fff
    style P2 fill:#238636,stroke:#2ea043,color:#fff
    style P3 fill:#238636,stroke:#2ea043,color:#fff
```

> [!NOTE]
> **Strategy: Vertical Slice First.** Phase 1 wires the entire tri-node pipeline end-to-end with minimal logic. Once you can spawn simple entities and watch them move on the canvas, every subsequent phase gets immediate visual feedback for debugging.

---

## Phase 1 — Vertical Slice (Core + Bridges + Visualizer) ✅ COMPLETE

**TDD Reference:** Sections 2.1, 4.1, 4.2, 5

### Scope
Stand up the complete tri-node pipeline with **minimal game logic**. The goal is a working feedback loop: Rust spawns basic entities → broadcasts via WebSocket → browser renders them on canvas → user sends commands back. No advanced algorithms yet — just enough to prove the wiring works.

### Micro-Core (Rust/Bevy)
- Project scaffold (`micro-core/`) with `Cargo.toml`, Bevy 0.18 headless
- Minimal ECS components: `Position`, `Velocity`, `Team`
- One trivial system: `movement_system` (entities drift in a direction — random or fixed)
- Fixed-timestep loop via `MinimalPlugins` + `ScheduleRunnerPlugin` (60 TPS)
- Basic entity spawning at startup (e.g., 100 entities, two teams)

### IPC Bridges
- **WS Bridge** (`ws_bridge.rs`): Async tokio task, broadcasts entity positions over `ws://localhost:8080`
- **ZMQ Bridge** (`zmq_bridge.rs`): Stub socket on `tcp://localhost:5555`, sends/receives a round-trip test message (no real AI yet)
- JSON message schema with `"type"` discriminator field
- Delta-sync tracking: spawn/move/die diffing

### Debug Visualizer
- `debug-visualizer/index.html` — single static page, zero build step
- Canvas rendering loop via `requestAnimationFrame()`
- Draw circles: red (swarm) vs. blue (defenders)
- Delta-sync buffer: store incoming WS payloads, redraw at monitor refresh rate
- Basic controls: spawn button, pause/resume, entity count HUD

### Success Criteria
- All three nodes start and connect (`Micro-Core → WS → Browser`, `Micro-Core → ZMQ → stub`)
- Browser renders ~100 moving entities smoothly
- Spawn button triggers new entities visible on canvas
- `cargo build` + `cargo clippy` clean, zero warnings

### Dependencies
None — this is the project's starting point.

---

## Phase 2 — Core Algorithms (Spatial, Pathfinding, Combat)

**TDD Reference:** Sections 2.2

### Scope
Implement the **real simulation logic** inside the Micro-Core. This is where the swarm becomes intelligent at the individual level: entities detect neighbors, follow flow fields, and engage in combat. The existing Debug Visualizer provides immediate visual feedback for all of this.

### Deliverables
- `Health` component + `combat_system` (proximity-based damage)
- Spatial partitioning via **Hash Grid** for O(1) proximity/neighbor queries
- **Dijkstra Maps / Vector Flow Fields** for mass pathfinding
- `FlowFieldFollower` component — entities follow the velocity vector of their current grid cell
- `spawning_system` with configurable wave spawning
- Visualizer upgrades: draw pathfinding lines, grid weight overlays, health bars
- C-ABI preparation: structure core logic for future `#[no_mangle] pub extern "C"` export

### Success Criteria
- 10,000 entities tick at 60 TPS without frame drops
- Entities navigate via flow fields (visible in the Debug Visualizer)
- Combat system triggers entity deaths (visible as entities disappearing)
- Unit tests for spatial grid lookups, flow field generation, and combat resolution

### Dependencies
- **Phase 1** (the tri-node pipeline must be working for visual debugging)

---

## Phase 3 — Macro-Brain & RL Training (Python / PyTorch)

**TDD Reference:** Section 3

### Scope
Build the AI training pipeline. Python wraps the Rust simulation as a Gymnasium environment and trains a PPO agent to issue macro-level swarm commands. With the Visualizer already running, training episodes can be observed in real-time.

### Deliverables
- Python project scaffold (`macro-brain/`) with `requirements.txt`
- Custom `gymnasium.Env` wrapping ZMQ communication (`SwarmEnv`)
- State vectorization: JSON → flat tensor / low-res heatmap
- Observation space and action space definitions
- PPO training loop via SB3 `MaskablePPO` (sb3-contrib) with 5-stage curriculum
- Reward function design (e.g., territory captured, defenders eliminated)
- Macro-action vocabulary: `TRIGGER_FRENZY`, `FLANK_LEFT`, etc.
- Trained model checkpoint

### Success Criteria
- `SwarmEnv.reset()` and `SwarmEnv.step(action)` round-trip correctly with the Rust core
- Training loop runs for N episodes without crashes
- Agent shows measurable learning (reward curve trends upward)
- Macro-actions are visible in the Debug Visualizer (swarm behavior changes in response)

### Dependencies
- **Phase 2** (Core algorithms must be in place — the AI needs real game state to train against)

---

## Phase 4 — Integration, Tuning & Scale

**TDD Reference:** Sections 2.2 (spatial perf), 4.1 (binary serialization)

### Scope
Stress-test the full system at target scale and optimize for sustained performance. All three nodes running simultaneously over extended sessions.

### Deliverables
- Full tri-node startup orchestration (documented startup order, health checks)
- Simultaneous AI training + debug visualization against the same Micro-Core
- Serialization upgrade: JSON → Bincode/MessagePack for high entity counts
- Performance profiling and bottleneck resolution
- Configuration system for tick rate, AI eval frequency, entity cap
- End-to-end integration tests

### Success Criteria
- All three nodes stable over extended sessions (>10 min)
- 10,000+ entities with AI evaluation + debug visualization without degradation
- Documented performance benchmarks (tick time, ZMQ latency, WS throughput)

### Dependencies
- **Phase 3** (Macro-Brain must be functional to test the full loop)

---

## Phase 5 — Web Engine Integration Test (WASM + ONNX Runtime Web)

**TDD Reference:** Section 6

### Scope
Prove the **"zero-gap engine integration"** thesis by consuming the Rust core and trained AI model inside a web-based game engine. This validates the full production pipeline without requiring Unity/Unreal knowledge — pure web tech the team already knows.

### Deliverables
- **Rust → WASM:** Compile the Micro-Core simulation logic to WebAssembly (`wasm32-unknown-unknown` target via `wasm-pack`)
- **ONNX Model Export:** `torch.onnx.export` → `macro_brain.onnx`
- **ONNX Runtime Web:** Load and run the trained model in-browser via `onnxruntime-web`
- **3D Rendering:** A web game engine (Three.js or Babylon.js) renders entities at coordinates provided by the WASM module — the engine's only job is visuals, exactly as described in TDD Section 6
- **Integration Demo:** A standalone web page that loads the WASM core + ONNX model + 3D engine, runs the full simulation loop, and renders it in 3D
- **Native C-ABI reference build:** Also produce a `.dylib`/`.so`/`.dll` with `#[no_mangle] pub extern "C"` wrappers + `cbindgen` headers, documenting the path for future Unity/Unreal integration

### Success Criteria
- Web demo runs the simulation in-browser: WASM ticks entities, ONNX model issues macro-actions, Three.js/Babylon.js renders the scene
- 3D engine is purely a renderer — all game logic runs in WASM, proving the decoupled architecture
- Native `.dylib` builds successfully and is callable from a minimal C test harness
- Integration guide documents both paths (web WASM + native C-ABI)

### Dependencies
- **Phase 4** (stable, tuned system with a trained model)

---

## Resolved Decisions

| Question | Decision |
|----------|----------|
| **Scale target** | **10,000+ entities is the hard minimum.** Modern devices handle 1K trivially — there is no point in optimizing for that baseline. The entire architecture exists to solve the 10K+ problem. |
| **Phase 5 scope** | **Web-based engine integration test.** Compile Rust to WASM, run ONNX in-browser, render with Three.js/Babylon.js. This proves zero-gap integration without requiring commercial engine expertise. Native C-ABI build is also produced as a reference artifact. |

---

## Phase Status

| Phase | Status | Completed | Key Deliverables |
|-------|--------|-----------|------------------|
| **Phase 1** | ✅ Complete | 2026-04-04 | Bevy 0.18 ECS, WS/ZMQ bridges, Debug Visualizer, bidirectional commands |
| **Phase 2** | ✅ Complete | 2026-04-05 | Spatial hash grid, Chamfer flow fields, Boids steering, FoW, terrain, 111 unit tests |
| **Phase 3.5** | ✅ Complete | 2026-04-08 | Multi-Master Arbitration, SB3 MaskablePPO, 5-stage curriculum, Bot Controller, prod pipeline, 195 Rust + 63 Python tests |
| **Phase 4** | ⬜ Not Started | — | 10K scale test, serialization upgrade, full tri-node orchestration |
| **Phase 5** | ⬜ Not Started | — | WASM compilation, ONNX export, Three.js 3D rendering |

### Phase 2 Completion Notes

Phase 2 was split into two implementation cycles:

1. **Universal Core Algorithms** (Tasks 01–08): Context-agnostic refactor, spatial hash grid, flow field pathfinding, rule resources, interaction/removal systems, composite movement/spawning, IPC upgrades, integration stress test.

2. **Debug Visualizer UX Refactor** (Tasks 09–15): Terrain grid, faction visibility, terrain-aware flow fields, visibility IPC, WS commands (Fibonacci spawn, terrain editing, scenario I/O), visualizer UI (spawn tools, fog renderer, paint mode), final integration.

**Key bugs resolved during integration:** broadcast forwarder death, SimState physics freezing, `Changed<Position>` late-join, omniscient flow field, Play/Pause desync. All documented in `docs/study/001-009`.

### Phase 3 Completion Notes

Phase 3 was implemented as 12 atomic tasks across 5 features:

1. **MacroDirective Protocol** (Tasks 01–04): ZMQ protocol upgrade, Phase 3 resources, state vectorizer, Python scaffold.
2. **Directive Executor** (Tasks 05–06): Executor system, engine overrides, SwarmEnv Gymnasium environment.
3. **ZMQ Integration** (Task 07): AiResponse envelope, ResetEnvironment, terrain tier constants.
4. **PPO Training** (Tasks 08–09): SB3 MaskablePPO pipeline, 5-stage curriculum learning, dynamic spawning, reward shaping.
5. **Debug Visualizer Phase 3** (Tasks 10–12): ML Brain panel, zone modifier tools, faction splitters, aggro masks.

**Key research:** RL training methodology, 3-tier interactable terrain, multi-master arbitration. All documented in `docs/study/010-012`.

**Safety patches:** 8 patches preventing RL exploitation (Vaporization Guard, Moses Effect, Ghost State Cleanup, f32 Sort Panic, Pacifist Flank Block, Dynamic Epicenter, Sub-Faction Desync, ZMQ Deadlock Guard).

### Phase 3.5 Completion Notes

Phase 3.5 was introduced to solidify the training pipeline before large scale runs:

1. **Python BotController:** Extracted bot strategy logic entirely into Python (Context-Agnostic refactor completion).
2. **5-Stage Curriculum:** Procedural terrain logic, dynamic 50v50 entity scaling, mixed heuristic algorithms.
3. **Training Orchestration:** Run Managers for tracking experiments in `runs/`, Validator CLIs, and `train.sh` launch scripts.

> [!NOTE]
> This roadmap was approved at the start of the project. Per-phase implementation plans are created via the `/planner` workflow and archived in `.agents/history/` after completion.

