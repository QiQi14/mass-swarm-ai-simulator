# Mass-Swarm AI Simulator — Training Status

> **Last Updated:** 2026-04-06  
> **Phase:** 3 Complete → Ready for Training  
> **Codebase Health:** ✅ Rust 180 tests · Python 33 tests · 0 warnings

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   Debug Visualizer                       │
│              (HTML/JS — ws://localhost:8080)              │
└───────────────────────┬─────────────────────────────────┘
                        │ WebSocket (10 TPS)
┌───────────────────────┴─────────────────────────────────┐
│                  Micro-Core (Rust/Bevy)                   │
│  - 60 TPS physics, 10K+ entities                         │
│  - Flow Fields, Boids, Terrain, Fog of War               │
│  - Directive Executor (8-action vocabulary)               │
│  - 3-Tier Terrain (Passable/Destructible/Permanent)      │
└───────────────────────┬─────────────────────────────────┘
                        │ ZMQ REQ/REP (2 Hz)
┌───────────────────────┴─────────────────────────────────┐
│                Macro-Brain (Python/SB3)                   │
│  - MaskablePPO + 2-Stage Curriculum                      │
│  - 50×50 density heatmaps (OGM)                          │
│  - Terrain generator (BFS-verified)                      │
│  - Reward shaping (5 components + P5 anti-exploit)       │
└─────────────────────────────────────────────────────────┘
```

---

## Completed Phases

### Phase 1: Micro-Core (Rust ECS)
- ✅ Bevy 0.18 headless 60 TPS loop
- ✅ Fibonacci spiral spawning
- ✅ Spatial hash grid + Boids separation
- ✅ Flow field pathfinding (Dijkstra)
- ✅ Terrain grid (dual hard/soft costs)
- ✅ Fog of War (bit-packed, wall-aware)
- ✅ Combat interaction system

### Phase 2: IPC & Visualization
- ✅ WebSocket server (real-time state stream)
- ✅ Debug visualizer (HTML/Canvas)
- ✅ ZMQ REQ/REP AI bridge

### Phase 3: Multi-Master Arbitration & RL
- ✅ `MacroDirective` — 8-action vocabulary (Hold, UpdateNav, Frenzy, Retreat, ZoneModifier, SplitFaction, MergeFaction, AggroMask)
- ✅ `NavigationTarget` enum (Faction chasing / Waypoint)
- ✅ `AiResponse` envelope (Directive vs ResetEnvironment)
- ✅ Directive Executor system (Vaporization Guard, Moses Effect, Ghost State Cleanup)
- ✅ Engine Override system (Tier 1 authority)
- ✅ State Vectorizer (50×50 density heatmaps per faction)
- ✅ `SwarmEnv` (Gymnasium-compatible, 13 safety tests)
- ✅ `MaskablePPO` training with `sb3-contrib`
- ✅ 2-Stage Curriculum (flat → procedural terrain)
- ✅ Terrain Generator (3-tier encoding, BFS connectivity)
- ✅ Reward Shaping (Pacifist Flank exploit blocked)
- ✅ 3-Tier Interactable Terrain (Passable/Destructible/Permanent)
- ✅ Debug Visualizer Phase 3 upgrades (zone tools, faction splitter, aggro masks, ML brain panel)

---

## Training Configuration

### Stage 1 — Tactical Sandbox
| Parameter | Value |
|-----------|-------|
| Map | Flat 1000×1000 |
| Opponent | Heuristic Bot (Faction 1, Rust-controlled) |
| Actions | 0-3 only (Hold, UpdateNav, Frenzy, Retreat) |
| Actions 4-7 | **MASKED** (MaskablePPO prevents selection) |
| Terrain | None (flat) |
| Promotion | `mean_reward > 0.3` over 50-episode window |

### Stage 2 — Domain Randomization
| Parameter | Value |
|-----------|-------|
| Map | Procedural (walls, chokepoints, swamps) |
| Opponent | Same heuristic bot |
| Actions | All 8 (full vocabulary unlocked) |
| Terrain | 60% permanent walls, 40% destructible |
| Wall types | Tier 1 (breakable by zone modifiers), Tier 2 (indestructible) |

### Hyperparameters
| Parameter | Value |
|-----------|-------|
| Algorithm | `MaskablePPO` (sb3-contrib) |
| Policy | `MultiInputPolicy` (Dict obs) |
| Observation | 4×50×50 density + 50×50 terrain + 6-dim summary |
| Actions | `Discrete(8)` |
| AI Frequency | 2 Hz (every 30 ticks) |
| Max Steps | 200 per episode |

---

## How to Train

```bash
# 1. Start Rust simulation (must be running for ZMQ)
cd micro-core && cargo run

# 2. In another terminal — start training
cd macro-brain
source venv/bin/activate

# Stage 1 only (flat map, actions 0-3)
python -m src.training.train --timesteps 100000

# With curriculum (auto-promotes to Stage 2)
python -m src.training.train --timesteps 100000 --curriculum

# Monitor with TensorBoard
tensorboard --logdir=./tb_logs/
```

### Output Locations
| Artifact | Path | Purpose |
|----------|------|---------|
| Checkpoints | `macro-brain/checkpoints/` | Model snapshots (every 10K steps) |
| TensorBoard | `macro-brain/tb_logs/` | Reward curves, loss, episode stats |

---

## Training Runs

| # | Date | Timesteps | Curriculum | Notes | Status |
|---|------|-----------|------------|-------|--------|
| — | — | — | — | *No completed training runs yet* | — |

> **Instructions:** After each training run, add a row with the run details and key metrics (mean reward, episode length, stage promotions).

---

## Safety Patches (All Active)

| # | Name | Protection |
|---|------|-----------|
| P1 | Vaporization Guard | `directive.take()` — consumed once per tick |
| P2 | Moses Effect | `u16::MAX` tiles immune to cost modifiers |
| P3 | Ghost State Cleanup | MergeFaction purges zones + buffs + aggro |
| P4 | f32 Sort Panic | `select_nth_unstable_by` with `partial_cmp` |
| P5 | Pacifist Flank Block | Distance cutoff + attenuation on flanking bonus |
| P6 | Dynamic Epicenter | SplitFaction uses density centroid, not hardcoded |
| P7 | Sub-Faction Desync | Read `active_sub_factions` from Rust snapshot |
| P8 | ZMQ Deadlock Guard | Timeout → truncate episode; tick swallowing |

---

## Test Health

| Suite | Count | Command |
|-------|-------|---------|
| Rust unit/integration | 180 | `cd micro-core && cargo test` |
| Python unit | 33 | `cd macro-brain && python -m pytest tests/ -v` |
| Smoke test | — | `cd micro-core && cargo run -- --smoke-test` |
| Full dev stack | — | `./dev.sh` |

---

## Archived Implementation

All Phase 3 task briefs, changelogs, QA reports, dispatch prompts, and implementation plans are archived in:
```
.agents/history/20260406_phase3_multi_master_arbitration_rl_training/
├── dispatch/     ← 12 executor prompt files
├── plans/        ← 6 implementation plan files
├── tasks/        ← 35 task briefs + changelogs + QA reports
└── task_state_final.json
```
