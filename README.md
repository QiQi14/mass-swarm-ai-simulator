# Mass-Swarm AI Simulator

A study project exploring two proof-of-concept ideas: **decoupled tri-node architecture** for mass-entity AI simulation, and **AI-agent-driven development workflows** for orchestrating complex software builds.

> **Status:** Phase 3 of 5 complete — 111 unit tests, simulation running with 10K+ entities, fog of war, terrain pathfinding, and a real-time debug visualizer. [See Roadmap →](ROADMAP.md)

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
     ┌──────▼──────┐  ┌───▼──────────────────┐
     │ Macro-Brain │  │  Debug Visualizer     │
     │ (Python)    │  │  (Browser / Canvas)   │
     │ PyTorch RL  │  │  Real-time inspection │
     │ PPO Agent   │  │  Spawn / Edit tools   │
     └─────────────┘  └──────────────────────┘
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

## Why This Approach?

### Why Rust for the Simulation Core?

The Micro-Core runs at a **fixed 60 TPS** and must process 10,000+ entity updates per tick — spatial indexing, flow field pathfinding, Boids separation, stat mutations, entity spawning/removal, fog of war, and IPC serialization. At this scale, every microsecond matters.

Rust's ownership model eliminates data races at compile time, which is non-negotiable for a simulation that uses parallel iteration (`par_iter_mut()`) across CPU cores. Bevy's ECS architecture provides zero-cost archetype storage and cache-friendly iteration over entity components.

**Achieved:** 111 unit tests, sub-millisecond per-tick processing, 60 TPS sustained.

### Why Three Separate Processes?

**Information asymmetry by design.** Each node operates on a different timescale with different data needs:

| Node | Frequency | Data | Concern |
|:-----|:----------|:-----|:--------|
| Micro-Core | 60 Hz | Full ECS state | Physics, pathfinding, combat |
| Macro-Brain | ~2 Hz | Fog-filtered state snapshot | RL strategy under partial observability |
| Debug Visualizer | ~10 Hz | Delta entity sync | Human observation, debugging |

The ZMQ bridge sends the Macro-Brain a **fog-filtered state snapshot** — it only sees enemy entities visible to its faction. This creates a Partially Observable Markov Decision Process (POMDP), which is essential for training an AI that must learn to explore vs. exploit.

If all three concerns lived in one process, you'd couple rendering frame rate to AI inference time to simulation tick rate. With three processes, each runs independently — you can train AI at 2 Hz while the simulation ticks at 60 Hz and the visualizer renders at monitor refresh rate.

### Why Agent-Driven Development?

The system has **15 interdependent tasks** spanning Rust ECS systems, WebSocket IPC, ZeroMQ bridges, HTML5 Canvas rendering, and fog-of-war bit manipulation. No single context window can hold all of this simultaneously.

The DAG planning approach solves this by:

1. **Context isolation** — each executor agent receives only its relevant files and contracts, staying well within token limits
2. **Parallel execution** — independent tasks run in separate agent sessions simultaneously
3. **Contract-driven integration** — shared interfaces are specified as architectural contracts in the implementation plan, so agents that never communicate can still produce compatible code
4. **Persistent learning** — bugs, gotchas, and conventions are captured as knowledge files that persist across sessions (21 knowledge files accumulated)

**Achieved:** 2 phases completed across 6 planning cycles, 15 executor dispatches, 7 QA audits — with full archival trail in `.agents/history/`.

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
├── debug-visualizer/          # Browser-based real-time visualizer
│   ├── index.html             # Dual-canvas rendering, spawn tools, fog toggle
│   ├── visualizer.js          # WebSocket client, entity renderer, terrain painter
│   └── style.css              # Dark theme, glassmorphism, animations
├── macro-brain/               # Python RL (Phase 3 — not yet implemented)
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
# Prerequisites: Rust toolchain, Python 3 (for dev server)
git clone https://github.com/QiQi14/mass-swarm-ai-simulator.git
cd mass-swarm-ai-simulator

# Start everything (builds Rust, starts HTTP server, launches simulation)
./dev.sh

# Open the debug visualizer
open http://127.0.0.1:3000
```

The visualizer connects automatically. Click `🎯 Spawn Mode` to add entities, toggle `Fog` to see per-faction visibility, use `🖌 Paint Mode` to draw terrain walls.

## Tech Stack

| Node | Language | Key Technologies |
|:-----|:---------|:-----------------|
| Micro-Core | Rust 2024 | Bevy 0.18 ECS, Tokio, tungstenite, ZeroMQ |
| Macro-Brain | Python 3.14+ | PyTorch, Ray RLlib, Gymnasium *(Phase 3)* |
| Debug Visualizer | Vanilla JS | HTML5 Canvas, native WebSocket, zero build step |
| Engine Integration | WASM + JS | wasm-pack, onnxruntime-web, Three.js *(Phase 5)* |

## Documentation

| Document | Description |
|:---------|:------------|
| [ROADMAP](ROADMAP.md) | 5-phase development roadmap with current progress |
| [Architecture](docs/architecture.md) | System architecture, data flows, design rationale |
| [IPC Protocol](docs/ipc-protocol.md) | Complete WebSocket & ZMQ message schema reference |
| [Case Studies](docs/study/) | 9 algorithm research notes & bug postmortems |
| [Original TDD](CASE_STUDY.md) | Technical Design Document that started the project |

## What's Next

**Phase 3: Macro-Brain & RL Training** — Build the Python side: a custom `gymnasium.Env` wrapping ZMQ communication, PPO training via Ray RLlib, and a macro-action vocabulary. The fog-of-war system means the AI must learn to explore and make decisions under partial observability.

See [ROADMAP.md](ROADMAP.md) for the full 5-phase plan.

## License

TBD
