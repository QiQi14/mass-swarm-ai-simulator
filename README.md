# Mass-Swarm AI Simulator

A study project exploring two proof-of-concept ideas: **decoupled tri-node architecture** for mass-entity AI simulation, and **AI-agent-driven development workflows** for orchestrating complex software builds.

> **Status:** Phase 3.5 of 5 complete — 195 Rust + 63 Python tests, RL training pipeline operational with 5-stage curriculum, bidirectional combat resolution at 50v50. [See Roadmap →](ROADMAP.md)

---

## What Is This?

This project is simultaneously two experiments:

### Experiment 1: Tri-Node Simulation Architecture

Can we build a 10,000+ entity AI simulation by splitting it into three independent OS processes — with zero shared memory, zero coupling, and each node independently replaceable?

```
     ┌──────────────────────────────┐
     │  Micro-Core (Rust / Bevy)   │ ← Source of Truth
     │  60 TPS · 10K+ entities     │
     │  ECS · Spatial Hash · Flow  │
     │  Fields · Fog of War        │
     └──────┬──────────────┬───────┘
            │              │
      ZeroMQ (REQ/REP)    WebSocket (async)
      ~2 Hz state snap    ~10 Hz delta sync
            │              │
     ┌──────▼──────┐  ┌───▼──────────────────────┐
     │ Macro-Brain │  │  Debug Visualizer (Vite)  │
     │ (Python)    │  │  Dual-mode: Training      │
     │ PyTorch RL  │  │  + Playground UI          │
     │ PPO Agent   │  │  Tactical HUD aesthetic   │
     └─────────────┘  └──────────────────────────┘
```

**The thesis:** Game engines (Unity, Unreal) are rendering-first architectures. When you need to simulate 10,000+ AI entities for machine learning training, the rendering pipeline becomes the bottleneck — consuming 90%+ of the frame budget on shaders, draw calls, and physics visualization while the actual game logic starves for CPU time.

By stripping the simulation down to a headless ECS (Entity Component System) that does nothing but compute, we reclaim the full CPU budget for what matters: physics, pathfinding, and AI decision-making. The debug visualizer connects as a passive observer over WebSocket — it never slows down the simulation because it runs in a separate process.

The result is a simulation that runs at a **fixed 60 TPS regardless of observer count**, with the entire architecture designed to be consumed by any game engine later via FFI (C-ABI) or WASM compilation.

### Experiment 2: AI-Agent Development Workflow

Can multiple AI coding agents — with specialized roles — build a complex system faster and more reliably than a single monolithic AI session?

```
     ┌─────────────────┐
     │   Human (User)   │
     │  Approves plans  │
     │  Sets direction  │
     └───────┬─────────┘
             │
     ┌───────▼──────────┐
     │   Planner Agent   │
     │  Reads codebase   │     ┌──────────────────────┐
     │  Designs DAG      │────▶│  Implementation Plan  │
     │  Splits tasks     │     │  + Task Briefs        │
     └──────────────────┘     └──────┬───────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
             ┌──────────┐    ┌──────────┐    ┌──────────┐
             │Executor A│    │Executor B│    │Executor C│
             │ Task 09  │    │ Task 10  │    │ Task 11  │
             │ Terrain  │    │FoW Grid  │    │Flow+Move │
             └────┬─────┘    └────┬─────┘    └────┬─────┘
                  │               │               │
                  └───────────────┼───────────────┘
                                  ▼
                          ┌──────────────┐
                          │   QA Agent    │
                          │ Contract test │
                          │ Certification │
                          └──────────────┘
```

The project uses a **DAG-based planning workflow** where:

1. **The Planner** analyzes the codebase, designs architectural contracts, and creates a Directed Acyclic Graph (DAG) of tasks with dependency edges
2. **Executor Agents** receive context-isolated task briefs and implement them in parallel — each agent sees only its target files, contracts, and dependencies
3. **The QA Agent** audits implementations against the original contracts, catching scope violations and regressions

Each phase produced a full archival trail: implementation plans, task briefs, changelogs, QA certification reports, and knowledge captures. This isn't just source code — it's a reproducible record of how a complex system was designed, decided upon, and built.

---

## Why We Choose This Approach

### Why Rust for the Simulation Core?

The Micro-Core runs at a **fixed 60 TPS** and must process 10,000+ entity updates per tick — spatial indexing, flow field pathfinding, Boids separation, stat mutations, entity spawning/removal, fog of war, and IPC serialization. At this scale, every microsecond matters.

Rust's ownership model eliminates data races at compile time, which is non-negotiable for a simulation that uses parallel iteration (`par_iter_mut()`) across CPU cores. Bevy's ECS architecture provides zero-cost archetype storage and cache-friendly iteration over entity components.

**Achieved:** 195 unit tests, sub-millisecond per-tick processing, 60 TPS sustained with bidirectional combat resolution.

### Why Three Separate Processes?

**Information asymmetry by design.** Each node operates on a different timescale with different data needs:

| Node | Frequency | Data | Concern |
|:-----|:----------|:-----|:--------|
| Micro-Core | 60 Hz | Full ECS state | Physics, pathfinding, combat |
| Macro-Brain | ~2 Hz | Fog-filtered state snapshot | RL strategy under partial observability |
| Debug Visualizer | ~10 Hz | Delta entity sync | Human observation, debugging |

The ZMQ bridge sends the Macro-Brain a **fog-filtered state snapshot** — it only sees enemy entities visible to its faction. This creates a Partially Observable Markov Decision Process (POMDP), which is essential for training an AI that must learn to explore vs. exploit.

If all three concerns lived in one process, you'd couple rendering frame rate to AI inference time to simulation tick rate. With three processes, each runs independently — you can train AI at 2 Hz while the simulation ticks at 60 Hz and the visualizer renders at monitor refresh rate.

### Why Stable-Baselines3 over Ray RLlib?

The original technical design specified **Ray RLlib** as the RL framework. During Phase 3 implementation, we evaluated both and chose **Stable-Baselines3 (SB3)** with the `sb3-contrib` extension. Here's why:

| Criteria | Ray RLlib | SB3 + sb3-contrib | Winner |
|:---------|:----------|:-------------------|:-------|
| **Action Masking** | Requires custom wrapper + policy override | First-class `MaskablePPO` in `sb3-contrib` | SB3 |
| **Setup Complexity** | Ray cluster runtime, distributed scheduler | `pip install` and go — single-process | SB3 |
| **Multi-Agent** | Native — built for multi-agent RL | Single-agent only | RLlib |
| **Debugging** | Opaque; logs buried in Ray worker processes | Transparent; standard Python stack traces | SB3 |
| **Scale** | Designed for 100+ parallel envs on clusters | Best for 1–8 envs on a single machine | RLlib |

**The deciding factor was action masking.** Our 8-action vocabulary includes terrain-dependent actions (ZoneModifier, SplitFaction) that are invalid on flat maps. Without proper masking, the agent wastes exploration budget on illegal moves and learns that half its actions are useless — a phenomenon called "Learned Helplessness." SB3's `MaskablePPO` solves this natively: the policy's softmax is zeroed out for masked actions at every step, so the agent never even considers invalid moves.

**The trade-off:** RLlib's multi-agent support would enable **self-play** (training the swarm against a learning opponent instead of a static bot). This is deferred to Phase 4 — if we need self-play, we'll either migrate to RLlib or implement population-based training on top of SB3.

**Goal:** A training pipeline that converges quickly on a single machine, with clear debugging output, and progressive action space expansion via curriculum learning.

### Why a 5-Stage Curriculum?

Throwing an agent into a complex environment with 8 actions, procedural terrain, and multiple unit types simultaneously is a recipe for convergence failure. The agent has too many degrees of freedom to discover meaningful behavior through random exploration.

Instead, we use **progressive complexity expansion** — each curriculum stage adds one new challenge after the previous one is mastered:

```
Stage 1 ── Learn to fight
  3 actions (Hold, Navigate, Frenzy), flat map. Retreat is explicitly locked to force combat engagement.
  Spawns: Fixed starting scenarios.
  Graduate: >80% win rate over 100 episodes

Stage 2 ── Learn positioning
  +Retreat (4 actions), defenders scattered into 2-3 groups
  Spawns: Dynamic procedural spreading.
  Graduate: >75% win rate

Stage 3 ── Learn army management
  +ZoneModifier, +SplitFaction (6 actions), simple terrain (1-2 walls)
  Graduate: >70% win rate

Stage 4 ── Learn terrain tactics
  Full 8 actions, complex procedural terrain, uniform units
  Graduate: >65% win rate

Stage 5 ── Learn unit composition (Phase 4)
  Full actions + terrain + multiple unit types (Tanker/Ranger/Scout)
```

Each stage's graduation threshold decreases because the scenarios become inherently harder — winning 65% with complex terrain and 8 actions is more impressive than winning 80% on a flat map with 3.

**Achieved:** Stage 1 operational — episodes completing in ~10 steps, win/loss cycling at ~55% (random policy), auto-promotion triggers when thresholds are met.

### Why Agent-Driven Development?

The system has **15 interdependent tasks** spanning Rust ECS systems, WebSocket IPC, ZeroMQ bridges, HTML5 Canvas rendering, and fog-of-war bit manipulation. No single context window can hold all of this simultaneously.

The DAG planning approach solves this by:

1. **Context isolation** — each executor agent receives only its relevant files and contracts, staying well within token limits
2. **Parallel execution** — independent tasks run in separate agent sessions simultaneously
3. **Contract-driven integration** — shared interfaces are specified as architectural contracts in the implementation plan, so agents that never communicate can still produce compatible code
4. **Persistent learning** — bugs, gotchas, and conventions are captured as knowledge files that persist across sessions (21 knowledge files accumulated)

**Achieved:** 3 phases completed across 7 planning cycles, 15+ executor dispatches, 7 QA audits — with full archival trail in `.agents/history/`.

---

## How It Works

The system operates across three decoupled processes that communicate purely over IPC, with strict separation of concerns.

1. **The Micro-Core (Rust):** The absolute source of truth. Runs ECS systems, Spatial Hash Grid, Pathfinding, and Combat mapping. When run with `./dev.sh --watch`, it operates purely for debug visualization. During training, it is booted with `cargo run -- --training` which disables cosmetic systems (like initial wave spawning) and relies purely on atomic `ResetEnvironment` payloads from Python via ZMQ. 
2. **The Macro-Brain (Python):** The Reinforcement Learning agent. Connects via ZeroMQ Request/Reply. Upon reset, Python sends initial procedural terrain and spawn locations. Then, every 30 ticks (2Hz), it receives an observation (grid densities, Faction state) and returns an action via an 8-command vocabulary (e.g., `Retreat`, `ZoneModifier`, `SplitFaction`).
3. **The Debug Visualizer (JS):** Connects to Rust via WebSockets (`ws://127.0.0.1:8080`). Parses state delta-updates and translates them to an HTML5 canvas at monitor refresh rate.

Because these are fully split, they do not block each other natively. By running `dev.sh --watch` in one terminal and Python training in the other, one can watch Python RL training live through the visualizer without injecting rendering delays back into the PyTorch steps.

---

## Project Structure

```
mass-swarm-ai-simulator/
├── micro-core/                # Rust simulation (Bevy 0.18 ECS)
│   └── src/
│       ├── components.rs      # Position, Velocity, FactionId, StatBlock, etc.
│       ├── spatial/           # O(1) Hash Grid for proximity queries
│       ├── pathfinding/       # Chamfer Dijkstra Flow Fields
│       ├── terrain.rs         # Integer-cost terrain grid
│       ├── visibility.rs      # Bit-packed fog of war (632 bytes/faction)
│       ├── rules/             # Config-driven navigation, interaction, removal
│       ├── systems/           # Movement, interaction, spawning, flow field, WS sync
│       └── bridges/           # WebSocket server, ZMQ bridge
├── debug-visualizer/          # Browser-based real-time visualizer (Vite + Vanilla JS)
│   ├── index.html             # Dual-mode app shell with tab navigation
│   ├── vite.config.js         # Vite dev server config
│   └── src/
│       ├── main.js            # App entry, router, mode switching
│       ├── router.js          # Hash-based mode router (#training / #playground)
│       ├── components/        # Tabs, accordion, sparkline, toast
│       ├── panels/            # Mode-aware panel registry
│       │   ├── training/      # Dashboard, ML Brain, Perf
│       │   ├── playground/    # Game Setup wizard, spawn, terrain, zones
│       │   └── shared/        # Telemetry, Inspector, Viewport, Legend
│       ├── draw/              # Canvas rendering (entities, terrain, fog, overlays)
│       └── styles/            # "Tactical Command Center" design system
├── macro-brain/               # Python RL training (SB3 MaskablePPO)
├── docs/
│   ├── architecture.md        # Architecture deep-dive
│   ├── ipc-protocol.md        # IPC message schema reference
│   └── study/                 # 9 case studies & algorithm research notes
├── .agents/                   # AI-agent workflow infrastructure
│   ├── agents/                # Planner, Executor, QA agent definitions
│   ├── workflows/             # DAG planning, execution lifecycle, QA protocols
│   ├── knowledge/             # 21 persistent knowledge files (gotchas, conventions)
│   └── history/               # 6 archived planning cycles with full audit trails
├── CASE_STUDY.md              # Original Technical Design Document
├── ROADMAP.md                 # 5-phase roadmap with completion status
└── dev.sh                     # One-command dev environment launcher
```

## Core Algorithms Implemented

| Algorithm | Study | Complexity | Purpose |
|:----------|:------|:-----------|:--------|
| [Spatial Hash Grid](docs/study/005_spatial_hash_grid.md) | 005 | O(1) amortized | Proximity queries for 10K+ entities |
| [Chamfer Dijkstra Flow Fields](docs/study/006_chamfer_dijkstra_flow_fields.md) | 006 | O(V log V) | Mass pathfinding — one field for all entities |
| [Composite Steering](docs/study/008_composite_steering_boids.md) | 008 | O(N×K) | Flow field navigation + Boids separation |
| [Bit-Packed Fog of War](docs/study/009_bitpacked_fog_of_war.md) | 009 | O(N) | 632 bytes/faction POMDP observability |
| [Zero-Alloc Disjoint Queries](docs/study/007_disjoint_queries_zero_alloc.md) | 007 | O(N×K) | Bevy ECS safe mutual mutation |

## Quick Start

```bash
# Prerequisites: Rust toolchain, Node.js 18+
git clone https://github.com/QiQi14/mass-swarm-ai-simulator.git
cd mass-swarm-ai-simulator

# Start everything (builds Rust, starts Vite dev server, launches simulation)
./dev.sh

# Open the debug visualizer (auto-opens via Vite)
# Training mode: http://127.0.0.1:5173/#training
# Playground mode: http://127.0.0.1:5173/#playground
```

The visualizer connects automatically. Use **Playground mode** (`#playground`) for spawn tools, terrain painting, and scenario design. Use **Training mode** (`#training`) to monitor ML training metrics, win rate, and reward history.

## Tech Stack

| Node | Language | Key Technologies |
|:-----|:---------|:-----------------|
| Micro-Core | Rust 2024 | Bevy 0.18 ECS, Tokio, tungstenite, ZeroMQ |
| Macro-Brain | Python 3.14+ | PyTorch, Stable-Baselines3, sb3-contrib, Gymnasium |
| Debug Visualizer | Vanilla JS | Vite, HTML5 Canvas, WebSocket, ES Modules |
| Engine Integration | WASM + JS | wasm-pack, onnxruntime-web, Three.js *(Phase 5)* |

## Documentation

| Document | Description |
|:---------|:------------|
| [ROADMAP](ROADMAP.md) | 5-phase development roadmap with current progress |
| [Architecture](docs/architecture.md) | System architecture, data flows, design rationale |
| [IPC Protocol](docs/ipc-protocol.md) | Complete WebSocket & ZMQ message schema reference |
| [Case Studies](docs/study/) | 9 algorithm research notes & bug postmortems |
| [Original TDD](CASE_STUDY.md) | Technical Design Document that started the project |

## Which Is Our Goal

Our ultimate goal is a **production-ready "zero-gap engine integration."** 

By taking the headless Rust simulation and compiling it entirely to WebAssembly (`wasm32-unknown-unknown`), alongside exporting the trained Python brain to an ONNX file (`onnxruntime-web`), we can embed 10,000+ AI entities and high-level behavioral models directly into web-based game engines (like Three.js or Babylon.js).

The game engine’s *only* responsibility will become rendering visual assets exactly where the WASM core dictates, proving the thesis that game engines should be render-first, with simulation and intelligence decoupled.

**Phase 4: Integration & Scale** will stress-test this at scale, and **Phase 5** will execute the Web Engine Integration.

See [ROADMAP.md](ROADMAP.md) for the full 5-phase plan.

## License

TBD
