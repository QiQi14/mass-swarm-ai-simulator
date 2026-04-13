# Mass-Swarm AI Simulator

A study project exploring two proof-of-concept ideas: **decoupled tri-node architecture** for mass-entity AI simulation, and **AI-agent-driven development workflows** for orchestrating complex software builds.

> **Status:** Phase 3.5 of 5 complete — 249 Rust + 214 Python tests, RL training pipeline operational with 9-stage curriculum, Boids 2.0 tactical steering with heterogeneous unit classes. [See Roadmap →](ROADMAP.md)

---

## What Is This?

This project is simultaneously two experiments:

### Experiment 1: Tri-Node Simulation Architecture

Can we build a 10,000+ entity AI simulation by splitting it into three independent OS processes — with zero shared memory, zero coupling, and each node independently replaceable?

```
     ┌────────────────────────────────────────────────────┐
     │            Micro-Core (Rust / Bevy 0.18)           │
     │  60 TPS · 10K+ entities · ECS + Spatial Hash Grid  │
     │                                                    │
     │  ┌────────────┐ ┌────────────┐ ┌────────────────┐  │
     │  │ Flow Fields │ │  Boids 2.0 │ │   Tactical     │  │
     │  │ (Dijkstra)  │ │ 3-Vector   │ │  Sensor (10Hz) │  │
     │  │  Pathfind   │ │  Blending  │ │  Kite · Peel   │  │
     │  └────────────┘ └────────────┘ └────────────────┘  │
     │  ┌────────────┐ ┌────────────┐ ┌────────────────┐  │
     │  │  Fog of War │ │3-Mode Dmg  │ │ Unit Type Reg  │  │
     │  │ Bit-Packed  │ │1v1·AoE·Pen │ │ Class Behav.   │  │
     │  └────────────┘ └────────────┘ └────────────────┘  │
     └────────┬──────────────────────────────┬────────────┘
              │                              │
        ZeroMQ (REQ/REP)              WebSocket (async)
        ~2 Hz state snapshot          ~10 Hz delta sync
              │                              │
     ┌────────▼────────┐  ┌──────────────────▼─────────────┐
     │   Macro-Brain   │  │   Debug Visualizer (Vite + JS) │
     │   (Python 3.14) │  │   Dual-mode: Training          │
     │   MaskablePPO   │  │   + Playground UI               │
     │   9-stage curric │  │   "Tactical Command Center"    │
     └─────────────────┘  └────────────────────────────────┘
```

**The thesis:** Game engines (Unity, Unreal) are rendering-first architectures. When you need to simulate 10,000+ AI entities for machine learning training, the rendering pipeline becomes the bottleneck — consuming 90%+ of the frame budget on shaders, draw calls, and physics visualization while the actual game logic starves for CPU time.

By stripping the simulation down to a headless ECS (Entity Component System) that does nothing but compute, we reclaim the full CPU budget for what matters: physics, pathfinding, and AI decision-making. The debug visualizer connects as a passive observer over WebSocket — it never slows down the simulation because it runs in a separate process.

The result is a simulation that runs at a **fixed 60 TPS regardless of observer count**, with the entire architecture designed to be consumed by any game engine later via FFI (C-ABI) or WASM compilation.

### Experiment 2: AI-Agent Development Workflow

Can multiple AI coding agents — with specialized roles — build a complex system faster and more reliably than a single monolithic AI session?

```
     ┌──────────────────┐
     │   Human (User)    │ Sets direction, approves plans, resolves ambiguity
     └────────┬─────────┘
              │
     ┌────────▼──────────┐
     │  Strategist Agent  │ Research · Diagnosis · Tactical Design
     │  Reads engine math │     ┌─────────────────────┐
     │  Reads training    │────▶│   Strategy Brief     │
     │  Produces brief    │     │  (Root-level .md)    │
     └──────────────────┘      └──────────┬──────────┘
                                          │
     ┌────────────────────────────────────▼───────────────┐
     │                   Planner Agent                     │
     │  Reads strategy brief + codebase                    │
     │  Designs DAG of parallel tasks                      │
     │  Writes implementation_plan.md                      │
     │  Generates task briefs in tasks_pending/            │
     └──────────────────────┬──────────────────────────────┘
                            │
           ┌────────────────┼────────────────┐
           ▼                ▼                ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │Executor A│    │Executor B│    │Executor C│
    │ Task 01  │    │ Task 02  │    │ Task 03  │
    │ (basic)  │    │(standard)│    │(advanced)│
    └────┬─────┘    └────┬─────┘    └────┬─────┘
         │               │               │
         └───────────────┼───────────────┘
                         ▼
                 ┌──────────────┐
                 │   QA Agent    │
                 │ Contract test │
                 │ Certification │
                 │ Knowledge cap │
                 └──────────────┘
```

The project uses a **4-role DAG-based planning workflow** where:

1. **The Strategist** researches the problem domain — analyzes combat math, RL training dynamics, and engine mechanics — then produces a `strategy_brief.md` that frames the problem, identifies constraints, and proposes architectural direction
2. **The Planner** consumes the strategy brief, analyzes the codebase, designs architectural contracts, and creates a Directed Acyclic Graph (DAG) of tasks with dependency edges and model-tier annotations
3. **Executor Agents** receive context-isolated task briefs and implement them in parallel — each agent sees only its target files, contracts, and dependencies. Model tier is matched to task complexity (basic / standard / advanced)
4. **The QA Agent** audits implementations against the original contracts, catching scope violations and regressions, then captures lessons learned as persistent knowledge files

Each phase produced a full archival trail: strategy briefs, implementation plans, task briefs, changelogs, QA certification reports, and knowledge captures. This isn't just source code — it's a reproducible record of how a complex system was designed, decided upon, and built.

**Accumulated:** 22 archived planning cycles, 34 knowledge files, 13 algorithm case studies.

---

## Why We Choose This Approach

### Why Rust for the Simulation Core?

The Micro-Core runs at a **fixed 60 TPS** and must process 10,000+ entity updates per tick — spatial indexing, flow field pathfinding, 3-vector Boids steering, stat mutations, tactical sensor evaluation, entity spawning/removal, fog of war, and IPC serialization. At this scale, every microsecond matters.

Rust's ownership model eliminates data races at compile time, which is non-negotiable for a simulation that uses parallel iteration (`par_iter_mut()`) across CPU cores. Bevy's ECS architecture provides zero-cost archetype storage and cache-friendly iteration over entity components.

**Achieved:** 249 unit tests, sub-millisecond per-tick processing, 60 TPS sustained with heterogeneous unit classes and 3-mode damage delivery (1v1, AoE, Penetration).

### Why Three Separate Processes?

**Information asymmetry by design.** Each node operates on a different timescale with different data needs:

| Node | Frequency | Data | Concern |
|:-----|:----------|:-----|:--------|
| Micro-Core | 60 Hz | Full ECS state | Physics, pathfinding, combat, tactical steering |
| Macro-Brain | ~2 Hz | Fog-filtered state snapshot | RL strategy under partial observability |
| Debug Visualizer | ~10 Hz | Delta entity sync | Human observation, debugging |

The ZMQ bridge sends the Macro-Brain a **fog-filtered state snapshot** — it only sees enemy entities visible to its faction. This creates a Partially Observable Markov Decision Process (POMDP), which is essential for training an AI that must learn to explore vs. exploit.

If all three concerns lived in one process, you'd couple rendering frame rate to AI inference time to simulation tick rate. With three processes, each runs independently — you can train AI at 2 Hz while the simulation ticks at 60 Hz and the visualizer renders at monitor refresh rate.

### Why a 4-Role Agent Workflow?

The system has **22+ completed planning cycles** spanning Rust ECS systems, WebSocket IPC, ZeroMQ bridges, HTML5 Canvas rendering, Python RL environments, and combat mathematics. No single context window can hold all of this simultaneously.

The original 3-role system (Planner → Executor → QA) worked for well-defined coding tasks but broke down when the problem itself needed deep analysis — for example, debugging why the RL agent plateaus at 50% win rate, or designing the combat math for penetration damage. The **Strategist** role was added to handle this research-first phase:

| Role | Product | Context Needs |
|:-----|:--------|:-------------|
| **Strategist** | Strategy Brief | Deep: engine math, RL dynamics, training logs |
| **Planner** | Implementation Plan + DAG | Wide: full codebase scan, dependency analysis |
| **Executor** | Code changes | Narrow: target files + contracts only |
| **QA** | Certification Report + Knowledge | Medium: contracts + implementation diffs |

**Context isolation** is the key insight — each executor agent receives only its relevant files and contracts, staying well within token limits. **Model tiering** assigns cheap local models to boilerplate tasks and reserves expensive frontier models for architectural work.

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

### Why a 9-Stage Curriculum?

Throwing an agent into a complex environment with 8 actions, procedural terrain, and multiple unit types simultaneously is a recipe for convergence failure. The agent has too many degrees of freedom to discover meaningful behavior through random exploration.

Instead, we use **progressive complexity expansion** — each curriculum stage adds one new challenge after the previous one is mastered:

```
Stage 0 — Learn to move          (2 actions, flat map, 1 target)
Stage 1 — Learn target priority  (2 actions, trap vs target)
Stage 2 — Learn pathfinding      (+Pheromone, walled map)
Stage 3 — Learn zone control     (+Repellent, danger zones)
Stage 4 — Learn scouting         (+Scout, fog of war, 2 sequential targets)
Stage 5 — Learn flanking         (+Split/Merge, V-chokepoint forcing pincer)
Stage 6 — Learn retreat          (+Retreat, full 8-action lure & ambush)
Stage 7 — Learn defense          (all actions, protected HVT scenario)
Stage 8 — Generalization         (randomized params across all mechanics)
```

Graduate: >80% win rate over 200 episodes × 50 consecutive wins.

---

## How It Works

The system operates across three decoupled processes that communicate purely over IPC, with strict separation of concerns.

1. **The Micro-Core (Rust):** The absolute source of truth. Runs ECS systems: Spatial Hash Grid, Flow Field Pathfinding, 3-vector Boids 2.0 movement (flow + separation + tactical), 10 Hz entity-sharded tactical sensor (Kite/PeelForAlly via subsumption), 3-mode damage delivery (1v1/AoE/Penetration), fog of war, and terrain. When run with `./dev.sh --watch`, it operates for debug visualization. During training, it is booted with `cargo run -- --training` which relies on atomic `ResetEnvironment` payloads from Python via ZMQ.
2. **The Macro-Brain (Python):** The RL strategic director. Connects via ZeroMQ REQ/REP. Upon reset, Python sends procedural terrain, spawn locations, interaction rules, and unit type definitions. Every 30 ticks (~2 Hz), it receives an 8-channel 50×50 observation tensor + 12-dim summary and returns an action via an 8-command vocabulary.
3. **The Debug Visualizer (JS):** Dual-mode web app (Training / Playground). Connects via WebSocket. Parses delta-updates and renders to HTML5 Canvas. Training mode shows RL metrics; Playground mode provides spawn tools, terrain painting, and scenario design.

Because these are fully split, they do not block each other. By running `dev.sh --watch` in one terminal and Python training in another, you can watch RL training live through the visualizer without injecting rendering delays into PyTorch steps.

---

## Project Structure

```
mass-swarm-ai-simulator/
├── micro-core/                    # Rust simulation (Bevy 0.18 ECS, 249 tests)
│   └── src/
│       ├── components/            # Position, Velocity, FactionId, StatBlock,
│       │                          # UnitClassId, TacticalState, CombatState
│       ├── config/                # SimulationConfig, UnitTypeRegistry, BuffConfig
│       ├── spatial/               # O(1) Hash Grid (faction-embedded payload)
│       ├── pathfinding/           # Chamfer Dijkstra Flow Fields
│       ├── terrain.rs             # Integer-cost terrain grid
│       ├── visibility.rs          # Bit-packed fog of war (632 bytes/faction)
│       ├── rules/                 # Config-driven interaction, navigation, removal
│       ├── systems/
│       │   ├── movement.rs        # Boids 2.0: 3-vector blend + engagement hold
│       │   ├── tactical_sensor.rs # 10 Hz sharded subsumption (Kite, PeelForAlly)
│       │   ├── interaction.rs     # 1v1 pairwise + CombatState stamping
│       │   ├── aoe_interaction.rs # AoE splash (Circle, Ellipse, ConvexPolygon)
│       │   ├── penetration.rs     # Ray penetration (Kinetic/Beam energy model)
│       │   └── ...                # flow_field, spawning, removal, visibility
│       └── bridges/               # WebSocket server, ZMQ bridge + protocol
├── debug-visualizer/              # Browser-based real-time visualizer (Vite + ES Modules)
│   └── src/
│       ├── main.js                # App entry, mode router (#training / #playground)
│       ├── panels/                # Training (Dashboard, Obs, Rewards) + Playground
│       ├── draw/                  # Canvas rendering (entities, terrain, fog, overlays)
│       └── styles/                # "Tactical Command Center" design system
├── macro-brain/                   # Python RL training (SB3 MaskablePPO, 214 tests)
│   └── src/
│       ├── env/                   # SwarmEnv (Gymnasium), actions, rewards, bot AI
│       ├── models/                # TacticalExtractor (CNN+MLP feature extractor)
│       ├── training/              # 9-stage curriculum, callbacks, train.py
│       └── utils/                 # State vectorizer, LKP fog buffer
├── docs/
│   ├── architecture.md            # Architecture deep-dive
│   └── study/                     # 13 algorithm case studies & research notes
├── .agents/                       # AI-agent workflow (4-role DAG framework)
│   ├── workflows/                 # Strategist, Planner, Executor, QA lifecycles
│   ├── context/                   # Structured project context (engine/, project/, training/)
│   │   ├── engine/                # Architecture, combat, navigation, terrain, protocol
│   │   ├── project/               # Features ledger, conventions, tech stack
│   │   └── training/              # Stages, bots, environment, overview
│   ├── knowledge/                 # 34 persistent knowledge files (gotchas, conventions)
│   ├── history/                   # 22 archived planning cycles with full audit trails
│   ├── rules/                     # Execution boundaries, QA protocol, shared state
│   └── skills/                    # Domain-specific capabilities (Rust code standards)
├── mathematics_reference.md       # Full mathematical specification (all formulas)
├── TRAINING_STATUS.md             # Current training run status & curriculum details
├── ROADMAP.md                     # 5-phase roadmap with completion status
├── CASE_STUDY.md                  # Original Technical Design Document
└── dev.sh                         # One-command dev environment launcher
```

## Core Algorithms Implemented

| Algorithm | Study | Complexity | Purpose |
|:----------|:------|:-----------|:--------|
| [Spatial Hash Grid](docs/study/005_spatial_hash_grid.md) | 005 | O(1) amortized | Proximity queries for 10K+ entities |
| [Chamfer Dijkstra Flow Fields](docs/study/006_chamfer_dijkstra_flow_fields.md) | 006 | O(V log V) | Mass pathfinding — one field for all entities |
| [Boids 2.0 Tactical Steering](docs/study/008_composite_steering_boids.md) | 008 | O(N×K) | 3-vector blend: flow + separation + tactical |
| [Bit-Packed Fog of War](docs/study/009_bitpacked_fog_of_war.md) | 009 | O(N) | 632 bytes/faction POMDP observability |
| [Zero-Alloc Disjoint Queries](docs/study/007_disjoint_queries_zero_alloc.md) | 007 | O(N×K) | Bevy ECS safe mutual mutation |
| [3-Tier Interactable Terrain](docs/study/011_3tier_interactable_terrain.md) | 011 | O(1) | Hard/soft cost + zone modifier overlay |
| [AoE Convex Polygon Hit-Test](docs/study/008_composite_steering_boids.md) | — | O(V) | Half-plane gradient math for splash shapes |

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
| [Mathematics Reference](mathematics_reference.md) | Complete mathematical specification (all engine formulas) |
| [Training Status](TRAINING_STATUS.md) | Current RL training run status & 9-stage curriculum |
| [Case Studies](docs/study/) | 13 algorithm research notes & bug postmortems |
| [Agent Workflow](docs/agent-workflow.md) | Multi-agent DAG framework documentation |
| [Original TDD](CASE_STUDY.md) | Technical Design Document that started the project |

## Which Is Our Goal

Our ultimate goal is a **production-ready "zero-gap engine integration."**

By taking the headless Rust simulation and compiling it entirely to WebAssembly (`wasm32-unknown-unknown`), alongside exporting the trained Python brain to an ONNX file (`onnxruntime-web`), we can embed 10,000+ AI entities and high-level behavioral models directly into web-based game engines (like Three.js or Babylon.js).

The game engine's *only* responsibility will become rendering visual assets exactly where the WASM core dictates, proving the thesis that game engines should be render-first, with simulation and intelligence decoupled.

**Phase 4: Integration & Scale** will stress-test this at scale, and **Phase 5** will execute the Web Engine Integration.

See [ROADMAP.md](ROADMAP.md) for the full 5-phase plan.

## License

TBD
