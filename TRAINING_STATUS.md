# Mass-Swarm AI Simulator — Training Status

> **Last Updated:** 2026-04-08  
> **Phase:** 3.5 Complete → Ready for Training  
> **Codebase Health:** ✅ Rust 195 tests · Python 63 tests · 0 warnings

---

## Architecture Overview

```text
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
│  - MaskablePPO + 5-Stage Curriculum                      │
│  - 50×50 density heatmaps (OGM)                          │
│  - Terrain generator (BFS-verified)                      │
│  - Exploit-proof zero-sum reward function                │
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
- ✅ Phase 3 Safety Patches implemented

### Phase 3.5: Training Pipeline Readiness
- ✅ **Python BotController:** Extracted bot strategy logic into Python.
- ✅ **ZMQ Batch Protocol:** Implemented `Vec<MacroDirective>` handling for mult-agent AI directive commands.
- ✅ **GameProfile Validator CLI:** Protect constraints.
- ✅ **Run Manager:** Centralized tracking of runs (`runs/`).
- ✅ **Launch Script (`train.sh`):** Automates pipeline.
- ✅ **5-Stage Curriculum:** 50v50 increments incorporating fully random procedural logic and mixed heuristics.

---

## 5-Stage Curriculum Design

| Stage | Map | Bot Behavior | Actions Unlocked | Graduation Condition |
|-------|-----|-------------|------------------|---------------------|
| **1** | Flat 1000×1000 | **Charge** — straight rush at brain | Hold, Navigate, ActivateBuff (0-2) | WR ≥ 80%, avg survivors ≥ 10.0, 100 eps |
| **2** | Flat 1000×1000 | **Charge** — scattered 2-3 groups | +Retreat (0-3) | WR ≥ 85%, avg survivors ≥ 15.0, Retreat ≥ 5%, 100 eps |
| **3** | Simple (1-2 walls) | **HoldPosition** — defends near spawn | +ZoneModifier, +SplitFaction (0-5) | WR ≥ 75%, Split ≥ 5%, avg_flanking_score_min: 0.0, 150 eps |
| **4** | Complex (procedural) | **Adaptive** — retreats when losing, pushes when winning | +MergeFaction, +SetAggroMask (0-7) | WR ≥ 80%, timeout ≤ 5%, 250 eps |
| **5** | Complex (procedural) | **Mixed** — random strategy each episode from pool | All 8 | WR ≥ 85%, timeout ≤ 5%, 300 eps |

### Bot Behavior System
The bot uses distinct strategies based on the current curriculum stage:
- **Charge**: Always navigates toward the enemy faction.
- **HoldPosition**: Retreats to a fixed defensive waypoint.
- **Adaptive**: Charges when healthy, retreats to a designated area when health fraction falls below a configured threshold. Employs hysteresis mode-locking to prevent combat jitter/oscillation.
- **Mixed**: Selects a behavior randomly from a configuration pool per episode to encourage the agent to deduce winning strategies rather than memorizing a single counter-strategy.

---

## Training Configuration

### Hyperparameters
| Parameter | Value |
|-----------|-------|
| Algorithm | `MaskablePPO` (sb3-contrib) |
| Policy | `MultiInputPolicy` (Dict obs) |
| Observation | 5×50×50 grids + 6-dim summary |
| Actions | `Discrete(8)` |
| AI Frequency | 2 Hz (every 30 ticks) |
| Max Steps | 500 per episode (increased for dynamic exploration) |
| Entities | 50 vs 50 (100 total entities) |

---

## Reward Calculation

The reward function leverages an **exploit-proof zero-sum implementation**. All per-step combat evaluations rely cleanly on tracking entity elimination and time survival, directly incentivizing aggressive victory conditions over point farming.

### Formula
```text
reward = time_penalty + kill_trading + terminal_bonus + survival_bonus
```

### Components

Calculated per evaluating interval (`curr` - `prev_snapshot`):

| # | Component | Factor/Value | Signal Logic |
|---|-----------|--------|--------|
| 1 | **Time penalty** | `-0.01` per step | Applied every evaluation loop strictly to incentivize swift action and punish coward/idle behaviors. |
| 2 | **Kill trading** | `+0.05` per killed, `-0.03` per dead| Raw numeric advantage calculation leveraging `enemies_killed` vs `own_lost`. |
| 3 | **Terminal Condition** | `+10.0` or `-10.0` | Emitted conditionally on total enemy wipeout or total friendly loss respectively to firmly end gradients. |
| 4 | **Survival bonus** | `+5.0` multiplier | Factors remaining survivor proportion (`curr_own / starting_entities`) onto the `Terminal: Win` completion to restrict pyrrhic sacrifices. |

*(Note: Prior heuristic flanking formulas are available in `rewards.py` contextually, but active simulation profiles rely purely on zero-sum structures for reliable baseline behavior).*

---

## How to Train

Run the automated bootstrapping launch script for single-command orchestration:

```bash
./train.sh --profile profiles/default_swarm_combat.json --timesteps 500000 --curriculum
```

This sequence:
1. Validates the profile parameters.
2. Auto-builds the Rust Micro-Core binary and launches it detached on port `5555`.
3. Creates a unique, timestamped `runs/` tracking directory.
4. Triggers Python iterative RL training.

### Output Locations
| Artifact | Path | Purpose |
|----------|------|---------|
| Runs Base | `runs/run_<timestamp>_<uuid>/`| Contains all generated artifacts isolated per training launch. |
| Checkpoints | `runs/.../checkpoints/` | Periodic model weight snapshots. |
| TensorBoard | `runs/.../tb_logs/` | Real-time reward curves, loss, logic stats. |
| Artifacts | `runs/.../profile_snapshot.json`| Locked copy of initialized configurations to audit parameters. |

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
| Rust unit/integration | 195 | `cd micro-core && cargo test` |
| Python unit | 63 | `cd macro-brain && python -m pytest tests/ -v` |
| Smoke test | — | `./train.sh --timesteps 0` |
| Full dev stack | — | `./dev.sh` |
