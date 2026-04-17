# Usage Guide — Mass-Swarm AI Simulator

> **Last Updated:** 2026-04-16 · Phase 4.0 (Action Space v3 + Node Editor + Squad Control)

## Prerequisites

| Tool | Version | Check | Notes |
|------|---------|-------|-------|
| Rust | stable 1.82+ | `rustc --version` | Micro-Core engine |
| Python | 3.12+ | `python3 --version` | RL training (macro-brain) |
| Node.js | 18+ | `node --version` | Debug Visualizer (Vite dev server) |
| npm | 9+ | `npm --version` | Visualizer dependency management |

> [!NOTE]
> The project has **three independent processes** that communicate via ZeroMQ (Rust ↔ Python, port `5555`) and WebSocket (Rust → Browser, port `8080`). They can be started independently or together via scripts.

---

## Quick Start — Three Workflows

### 1. Playground Mode (Manual Debugging)

Start the Rust simulation + Debug Visualizer. No ML training — you control everything from the browser.

```bash
# Start everything (builds Rust, starts Vite + Micro-Core)
./dev.sh

# Opens automatically at:
# http://127.0.0.1:5173#playground
```

**What you get:** A browser-based tactical command center with two interaction modes:
- **Node Editor** — Visual Drawflow-based rule editor. Design battle scenarios by connecting Faction, Unit, Combat, Navigation, and Death nodes, then press ▶ Launch to compile the graph into WS commands.
- **Squad Control** — Box-select entities on the canvas, form squads (sub-factions), and issue RTS-style orders: move, attack, hold, retreat, disband. Right-click for contextual commands.

### 2. Training Mode (ML Training)

Start all three nodes: Rust engine + Python RL training + optional browser monitoring.

```bash
# One-command training (builds Rust, starts engine, runs Python)
./train.sh

# With options:
./train.sh --timesteps 500000           # Train for 500K steps
./train.sh --slow-train                 # Max TPS (no frame sleep)
./train.sh --no-visualizer              # Headless (no browser)
./train.sh --profile profiles/custom.json  # Custom game profile
./train.sh --load-checkpoint runs/run_XXX/checkpoints/ppo_swarm_50000_steps.zip --start-stage 2
```

**What it does:**
1. Builds Rust Micro-Core in release mode
2. Opens Debug Visualizer (browser) — optional
3. Starts Micro-Core with `--training` flag (ZMQ-driven, no manual spawns)
4. Launches Python MaskablePPO training (foreground)

### 3. Watch Mode (Monitor Running Training)

If training is already running, start only the Debug Visualizer to observe:

```bash
./dev.sh --watch       # or: ./dev.sh --training
# Opens at http://127.0.0.1:5173#training
```

> [!TIP]
> Watch mode does NOT touch the Rust engine or training process. Safe to start/stop anytime.

---

## Architecture Overview

```
┌─────────────────────────────┐    ZMQ REQ/REP :5555    ┌──────────────────────────────┐
│  Rust Micro-Core            │◄───────────────────────►│  Python Macro-Brain           │
│  (Bevy 0.18 ECS)            │    JSON snapshots +      │  (MaskablePPO + Gymnasium)   │
│                             │    directives             │                              │
│  • Combat (interaction.rs)  │                          │  • SwarmEnv (swarm_env.py)    │
│  • Navigation (flow_field)  │    WS :8080 (debug)      │  • Vectorizer (8ch → CNN)     │
│  • Fog of War (visibility)  │◄──────────────────┐     │  • Rewards (5-component)      │
│  • Density Maps (50×50)     │                   │     │  • Curriculum (9 stages)      │
│  • Terrain (3-tier costs)   │                   │     │  • Profile system (JSON)      │
│  • Entity Lifecycle         │                   │     └──────────────────────────────┘
└────────────────┬────────────┘                   │
                 │ JSON delta_update              │
                 ▼                                │
┌──────────────────────────────┐                  │
│  Debug Visualizer (Browser)  │──────────────────┘
│  (Vite + Vanilla JS)         │   WS commands
│                              │
│  Modes:                      │
│  • #training  (monitoring)   │
│  • #playground (manual ctrl) │
│                              │
│  8-channel overlay toggles   │
│  Entity inspector            │
│  Training dashboard          │
└──────────────────────────────┘
```

### Ports

| Port | Protocol | Direction | Purpose |
|------|----------|-----------|---------|
| `5555` | ZeroMQ REQ/REP | Rust ↔ Python | AI state snapshots + macro directives |
| `8080` | WebSocket | Rust → Browser | Debug visualization sync |
| `5173` | HTTP (Vite) | Browser | Debug Visualizer dev server |

---

## Running Individual Components

### Micro-Core Only (Playground)

```bash
cd micro-core
cargo run                     # Playground mode (paused until browser connects)
cargo run -- --smoke-test     # 300-tick smoke test, then exit
cargo run -- --training       # Training mode (ZMQ-driven, waits for Python)
cargo run -- --training --throttle  # Training at 60 TPS (human-observable)
```

**CLI Flags:**

| Flag | Effect |
|------|--------|
| `--training` | ZMQ-driven mode: no initial spawns, unpaused, long ZMQ timeout |
| `--throttle` | Cap at 60 TPS even in training (for browser observation) |
| `--smoke-test` | Auto-exit after 300 ticks |
| `--entity-count N` | Override initial entity count (playground only) |

### Python Training Only

Requires a running Micro-Core with `--training`.

```bash
cd macro-brain
source .venv/bin/activate     # or: .venv/bin/python directly

# Fresh training run
python -m src.training.train --profile profiles/tactical_curriculum.json --timesteps 100000

# Resume from checkpoint
python -m src.training.train \
    --load-checkpoint runs/run_YYYYMMDD_HHMMSS/checkpoints/ppo_swarm_50000_steps.zip \
    --start-stage 2 \
    --timesteps 500000
```

**Train CLI Arguments:**

| Argument | Default | Description |
|----------|---------|-------------|
| `--profile` | `profiles/tactical_curriculum.json` | Game profile JSON |
| `--timesteps` | `100000` | Total training timesteps |
| `--runs-dir` | `./runs` | Output directory for training runs |
| `--load-checkpoint` | — | Path to `.zip` checkpoint to resume from |
| `--start-stage` | `0` | Curriculum stage to start from |

### Visualizer Only (Vite Dev Server)

```bash
cd debug-visualizer
npm install          # First time only
npx vite --port 5173 --host 0.0.0.0
```

---

## Debug Visualizer

### Dual-Mode Interface

The visualizer operates in two modes, selected via URL hash:

| Mode | URL | Purpose |
|------|-----|---------|
| **Training** | `#training` | Read-only monitoring: reward curves, episode stats, channel overlays |
| **Playground** | `#playground` | Node-based scenario editor + tactical squad control |

### Canvas Controls

| Action | Control |
|--------|---------|
| **Pan** | Click + drag (on empty canvas) |
| **Zoom** | Scroll wheel (toward pointer) |
| **Reset view** | Double-click |
| **Inspect entity** | Click near an entity |
| **Box-select** | Left-click + drag (over entities) |
| **Move order** | Right-click on empty map (with squad selected) |
| **Attack order** | Right-click near enemy (with squad selected) |
| **Hold** | `H` key (with squad selected) |
| **Retreat** | `R` key + click target (with squad selected) |
| **Deselect** | `Escape` |
| **Disband squad** | `Delete` key |

### Observation Channel Overlays (v4.0)

Toggle these in the **Viewport Layers** panel to see what the CNN sees:

| Toggle | Channel | Visualization |
|--------|---------|---------------|
| Ch0 — Friendly Count | 🟦 Force | Green heatmap — where brain units are |
| Ch1 — Enemy Count | 🟦 Force | Red heatmap — where enemies are |
| Ch2 — Friendly ECP | 🟦 Force | Cyan glow — brain's combat power |
| Ch3 — Enemy ECP | 🟦 Force | Magenta glow — enemy threat density |
| Ch4 — Terrain Cost | 🟩 Environment | Amber/red overlay — walls and mud |
| Ch5 — Fog Awareness | 🟩 Environment | Dark overlay — unknown/explored/visible |
| Ch6 — Class 0 Density | 🟨 Tactical | Per-class density (frontline) |
| Ch7 — Class 1 Density | 🟨 Tactical | Per-class density (midline) |

### Playground UI Components

| Component | Description |
|-----------|-------------|
| **Top Bar** | Version badge, Preset dropdown, ▶ Launch button, Focus Mode toggle, Minimize |
| **Node Editor** | Drawflow canvas — glassmorphic node-based scenario builder (semi-transparent over sim) |
| **Bottom Toolbar** | Add node buttons (+Faction, +Unit, +Combat, +Nav, +Death), terrain paint, sim controls |
| **Preset Gallery** | Fullscreen splash on first load — select a pre-built scenario or start blank |
| **Squad Panel** | Right-side overlay card — squad name, unit count, HP bar, action buttons |
| **Tactical Overlay** | Canvas layer — selection box, squad banners, pulsing order arrows, rally points |
| **Focus Mode** | Toggle 30% → 90% opacity on node editor (backdrop frost effect) |

---

## Tests

### Rust (Micro-Core)

```bash
cd micro-core
cargo test                        # All tests (257 tests)
cargo test snapshot               # Snapshot builder tests
cargo test density                # Density/ECP map tests
cargo test interaction            # Combat system tests
cargo test tactical               # Tactical overrides + class filter tests
cargo test --no-default-features  # Without debug telemetry
```

### Python (Macro-Brain)

```bash
cd macro-brain
.venv/bin/python -m pytest tests/ -v              # All tests (219 tests)
.venv/bin/python -m pytest tests/test_vectorizer.py      # Channel construction
.venv/bin/python -m pytest tests/test_channel_integrity.py  # Channel invariants
.venv/bin/python -m pytest tests/test_rewards.py         # Reward components
.venv/bin/python -m pytest tests/test_actions.py         # Action space v3 (3D)
.venv/bin/python -m pytest tests/test_tactical_integration.py  # Full pipeline
```

---

## Training Outputs

Each training run creates a timestamped directory:

```
runs/run_YYYYMMDD_HHMMSS/
├── config.json                  # Snapshot of the game profile used
├── checkpoints/                 # Model snapshots (every 10K steps)
│   ├── ppo_swarm_10000_steps.zip
│   └── ...
├── tb_logs/                     # TensorBoard logs
│   └── MaskablePPO_1/
│       └── events.out.tfevents...
├── episode_log_stage0.csv       # Per-episode metrics (reward, kills, duration)
└── episode_log_stage1.csv       # (created when promoted to stage 1)
```

### Monitoring Training

```bash
# TensorBoard (from macro-brain/)
.venv/bin/tensorboard --logdir runs/run_LATEST/tb_logs/

# Episode CSV (quick check)
tail -f runs/run_LATEST/episode_log_stage0.csv
```

### Curriculum Promotion

The agent auto-promotes through stages when it achieves an **80% win rate** over a rolling window. Key stages:

| Stage | Map | Goal | Key Mechanic |
|-------|-----|------|-------------|
| 0 | 400×400 | Navigate to 1 enemy | AttackCoord aiming |
| 1 | 500×500 | Choose correct target (2 enemies) | ECP-based target selection |
| 2 | 600×600 | Find path around walls | ZoneModifier (attract/repel) |
| 3 | 600×600 | Avoid trap groups | ZoneModifier (repel) |
| 4 | 800×800 | Scout fog, sequential targets | Intel Ping, retargeting |
| 5 | 1000×1000 | Class-aware splitting + tactics | SplitToCoord, MergeBack, SetPlaystyle |
| 6 | 1000×1000 | Tactical withdrawal | Retreat |
| 7+ | 1000×1000 | Flanking, kite, buff usage | ActivateSkill, Kite playstyle |

---

## Game Profile System

Training is configured through JSON game profiles. The default profile is `profiles/tactical_curriculum.json`.

```bash
# Validate a profile
cd macro-brain
.venv/bin/python -c "from src.config.validator import validate_profile; from src.config.game_profile import load_profile; print(validate_profile(load_profile('profiles/tactical_curriculum.json')))"
```

Key profile sections:
- **`factions`** — unit types with stat blocks (HP, damage, speed, etc.)
- **`combat_rules`** — interaction rules between factions
- **`training.curriculum`** — stage definitions with map size, fog, action unlocks
- **`bot_behaviors`** — per-stage AI behavior for enemy factions (patrol, hold, chase)

---

## `dev.sh` Reference

```bash
./dev.sh                # Playground dev mode (Rust + Vite)
./dev.sh --watch        # Visualizer only (monitor training)
./dev.sh --training     # Alias for --watch
./dev.sh --smoke        # 300-tick smoke test, then exit
./dev.sh --release      # Build with release optimizations
./dev.sh --prod         # Production build (no debug telemetry)
./dev.sh --clean        # Kill leftover processes and free ports
```

| Mode | Telemetry | Performance | Use Case |
|------|-----------|-------------|----------|
| Default | ON | Debug | Development, UI debugging |
| `--release` | ON | Optimized | Performance testing |
| `--prod` | **OFF** | Optimized | Benchmarks (zero overhead) |
| `--watch` | N/A | N/A | Monitor a running training session |

---

## Troubleshooting

### Port Already in Use

```bash
./dev.sh --clean              # Kills processes on :5173 and :8080

# Manual alternative
lsof -ti:8080 | xargs kill   # Kill WS port user
lsof -ti:5173 | xargs kill   # Kill Vite port user
lsof -ti:5555 | xargs kill   # Kill ZMQ port user
```

### Training Crashes on Reset

- Ensure Micro-Core is running with `--training` flag
- Check that the game profile is valid (`validate_profile`)
- Look for ZMQ timeout errors in the Rust terminal

### Channel Verification Errors (❌ CRITICAL)

If you see `ch2 (friendly ECP) is ALL ZEROS!` during training startup:
1. Check the Rust terminal for entity spawn counts
2. Verify the game profile has valid `stats` entries for all factions
3. Check `density_maps` and `ecp_density_maps` keys in the diagnostic log

### WebSocket Won't Connect

1. Ensure Micro-Core is running (check for `[WS] Listening on 0.0.0.0:8080`)
2. The visualizer auto-reconnects every 2 seconds
3. In watch mode, the training Rust process must be running

### No Entities in Playground

1. Entities only spawn when you use the Spawn panel or Game Setup wizard
2. In training mode, entities are spawned by Python via `ResetEnvironment`
3. Check terminal for `[Reset] Despawned X, spawned Y` messages

---

## File Structure

```
mass-swarm-ai-simulator/
├── dev.sh                          # Dev mode launcher (Playground)
├── train.sh                        # Training launcher (all 3 nodes)
├── USAGE.md                        # ← You are here
├── TRAINING_STATUS.md              # Training metrics & channel layout
├── ROADMAP.md                      # Phase roadmap (1-5)
├── CASE_STUDY.md                   # Original technical design document
│
├── micro-core/                     # 🦀 Rust simulation engine (Bevy 0.18)
│   ├── Cargo.toml                  # Features: debug-telemetry
│   └── src/
│       ├── main.rs                 # App entry, CLI flags, custom runner
│       ├── lib.rs                  # Module barrel
│       ├── terrain.rs              # 3-tier terrain (Pass/Destruct/Perm)
│       ├── visibility.rs           # Bit-packed Fog of War per faction
│       ├── components/             # ECS: Position, Velocity, FactionId, StatBlock, UnitClassId
│       ├── config/                 # Resources: DensityConfig, BuffConfig, FactionTacticalOverrides
│       │   └── tactical_overrides.rs  # Runtime tactical behavior overrides per faction
│       ├── rules/                  # InteractionRule, NavigationRule, RemovalRule
│       ├── systems/                # Bevy systems
│       │   ├── movement.rs         # Composite 3-vector steering (flow + boids + tactical)
│       │   ├── flow_field_update.rs# Dijkstra flow fields + zone modifiers
│       │   ├── directive_executor/ # 8-action vocabulary executor
│       │   │   └── executor.rs     # SplitFaction (class_filter), SetTacticalOverride, etc.
│       │   ├── tactical_sensor.rs  # 10 Hz tactical behavior (Kite, PeelForAlly) + override lookup
│       │   ├── interaction.rs      # Combat: range, mitigation, cooldowns
│       │   ├── state_vectorizer.rs # 50×50 density + ECP + per-class density maps
│       │   ├── ws_command.rs       # WS command handler (spawn_wave, set_interaction)
│       │   └── ws_sync.rs          # Debug broadcast to browser
│       ├── bridges/
│       │   ├── ws_server.rs        # Tokio WebSocket server (:8080)
│       │   ├── zmq_bridge/         # ZeroMQ REQ/REP bridge (:5555)
│       │   │   ├── io_loop.rs      # Background async ZMQ thread
│       │   │   ├── systems.rs      # ai_trigger + ai_poll systems
│       │   │   ├── snapshot.rs     # State snapshot builder
│       │   │   └── reset.rs        # ResetEnvironment handler
│       │   └── zmq_protocol/       # DTOs: StateSnapshot, MacroDirective
│       │       └── directives.rs   # SplitFaction{class_filter}, SetTacticalOverride
│       ├── spatial/                # Spatial hash grid (collision)
│       └── pathfinding/            # Flow field navigation
│
├── macro-brain/                    # 🧠 Python RL training
│   ├── requirements.txt            # sb3-contrib, gymnasium, torch, zmq
│   ├── profiles/                   # Game profile JSON configs
│   │   └── tactical_curriculum.json
│   ├── src/
│   │   ├── config/                 # Profile parser, validator, definitions
│   │   ├── env/
│   │   │   ├── swarm_env.py        # Gymnasium env (ZMQ REP, 3D action masking)
│   │   │   ├── rewards.py          # 5-component reward + anti-exploit
│   │   │   ├── actions.py          # MultiDiscrete([8,2500,4]) → MacroDirective
│   │   │   ├── spaces.py           # Action space v3 (8 actions × 2500 coords × 4 modifiers)
│   │   │   ├── bot_controller.py   # Heuristic enemy AI (patrol, hold, chase)
│   │   │   └── wrappers.py         # FrameSkipWrapper
│   │   ├── training/
│   │   │   ├── train.py            # MaskablePPO entry point
│   │   │   ├── curriculum.py       # 9-stage curriculum (spawns, terrain, fog)
│   │   │   ├── callbacks.py        # Curriculum auto-promotion, logging
│   │   │   └── run_manager.py      # Timestamped run directory creation
│   │   ├── models/
│   │   │   └── feature_extractor.py# CNN(8×50×50→128) + MLP(12→64) → 256
│   │   └── utils/
│   │       ├── vectorizer.py       # Snapshot → 8-channel numpy (incl. per-class density)
│   │       ├── terrain_generator.py# Procedural terrain (BFS-verified)
│   │       └── lkp_buffer.py       # Last Known Position (fog decay)
│   ├── tests/                      # 219 Python tests
│   └── runs/                       # Training run outputs
│
├── debug-visualizer/               # 🌐 Browser-based debug UI
│   ├── package.json                # Vite + Drawflow
│   ├── vite.config.js              # Multi-entry (main + playground)
│   ├── index.html                  # Entry point
│   └── src/
│       ├── main.js                 # App init, mode router
│       ├── playground-main.js      # Playground entry point (floating overlay layout)
│       ├── state.js                # Shared state (entities, squads, selection)
│       ├── config.js               # Grid, colors, faction config
│       ├── router.js               # Hash-based #training/#playground routing
│       ├── websocket.js            # WS client (auto-reconnect)
│       ├── draw/                   # Canvas rendering
│       │   ├── entities.js         # Entity dots + effects
│       │   └── tactical-overlay.js # Selection box, squad banners, order arrows
│       ├── node-editor/            # Drawflow-based scenario builder
│       │   ├── drawflow-setup.js   # Drawflow init + glassmorphic theme
│       │   ├── compiler.js         # Graph → WS commands compiler
│       │   ├── preset-gallery.js   # Preset splash modal
│       │   ├── brain-runner.js     # ONNX.js inference loop for General node
│       │   └── nodes/              # Node type renderers
│       │       ├── faction.js, unit.js, stat.js, death.js
│       │       ├── combat.js, relationship.js
│       │       ├── navigation.js, waypoint.js, movement.js
│       │       └── general.js      # ML brain node
│       ├── squads/                 # Squad (sub-faction) control
│       │   ├── squad-manager.js    # Create/disband squads via SplitFaction/MergeFaction
│       │   └── order-system.js     # Move/attack/hold/retreat orders
│       ├── controls/               # Event handlers
│       │   ├── selection.js        # Box-select + faction-click selection
│       │   └── init.js             # Right-click order dispatch
│       ├── panels/                 # UI panels (viewport, training, playground)
│       │   └── playground/
│       │       ├── squad-panel.js   # Squad info overlay card
│       │       ├── terrain-overlay.js
│       │       └── sim-controls-overlay.js
│       └── styles/                 # Tactical Command Center CSS
│           ├── node-editor.css     # Drawflow glassmorphic overrides
│           ├── tactical.css        # Selection, banners, arrows
│           └── playground-overlay.css  # Overlay card styling
│
├── docs/                           # Architecture docs (partially outdated)
│   ├── architecture.md             # System architecture overview
│   ├── ipc-protocol.md             # LEGACY — see .agents/context/
│   └── study/                      # Engineering case studies
│
└── .agents/                        # AI agent context (internal)
    ├── context/                    # Current-truth docs (engine, curriculum, IPC)
    └── history/                    # Change logs from DAG/direct implementations
```

---

## Rust Logging

```bash
RUST_LOG=info cargo run                    # Info-level logs
RUST_LOG=debug cargo run                   # Debug-level logs
RUST_LOG=micro_core=trace cargo run        # Trace-level for micro-core only
```

> [!TIP]
> Entity telemetry goes to the Browser via WebSocket. Text logs go to the Terminal. This separation prevents GC stutter in the browser at high TPS.

---

## First-Time Setup

```bash
# 1. Clone
git clone <repo-url>
cd mass-swarm-ai-simulator

# 2. Rust toolchain
rustc --version   # Ensure ≥ 1.82

# 3. Python environment
cd macro-brain
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..

# 4. Visualizer dependencies
cd debug-visualizer
npm install
cd ..

# 5. Verify everything works
cd micro-core && cargo test && cd ..                  # 257 Rust tests
cd macro-brain && .venv/bin/python -m pytest tests/ && cd ..  # 219 Python tests

# 6. Start playground
./dev.sh

# 7. Or start training
./train.sh --timesteps 100000
```
