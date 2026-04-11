# Mass-Swarm AI Simulator — Training Status

> **Last Updated:** 2026-04-10 (22:00 local)
> **Phase:** Tactical Training Curriculum v3.1 — Stage 1 (Target Selection)
> **Codebase Health:** ✅ 181 Rust tests · 51+ Python tests · 0 warnings

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
│  - Fog-of-war grids in ZMQ state snapshot                │
│  - Buff system: damage + speed multipliers               │
│  - Terrain: hard_costs (pathfinding) + soft_costs (speed)│
└───────────────────────┬─────────────────────────────────┘
                        │ ZMQ REQ/REP (every 30 ticks)
┌───────────────────────┴─────────────────────────────────┐
│                Macro-Brain (Python/SB3)                   │
│  - MaskablePPO + MultiDiscrete([8, 2500])                │
│  - TacticalExtractor (CNN+MLP feature extractor)         │
│  - 8-channel 50×50 observation tensor (fixed shape)      │
│  - LKP fog-of-war memory buffer                          │
│  - 9-stage tactical curriculum (0-8)                     │
│  - Bot controller (Python-side heuristic AI for enemies) │
└─────────────────────────────────────────────────────────┘
```

---

## Current Model Configuration

| Parameter | Value |
|-----------|-------|
| **Algorithm** | `MaskablePPO` (sb3-contrib) |
| **Policy** | `MultiInputPolicy` + `TacticalExtractor` |
| **Action Space** | `MultiDiscrete([8, 2500])` — 8 action types × 50×50 flattened grid |
| **Observation** | Dict: 8 × `Box(50,50)` + `Box(12)` |
| **Feature Extractor** | CNN(8×50×50→128) + MLP(12→64) → 256-dim embedding |
| **Learning Rate** | 3e-4 |
| **Batch Size** | 64 |
| **Steps/Update** | 2048 |
| **Epochs** | 10 |
| **Profile** | `profiles/tactical_curriculum.json` |

---

## 8-Action Vocabulary

| Idx | Action | Unlock Stage | Coords? | Description |
|:---:|--------|:---:|:---:|-------------|
| 0 | Hold | 0 | ❌ | Stop, hold position |
| 1 | AttackCoord | 0 | ✅ | Move main force to grid coordinate |
| 2 | DropPheromone | 2 | ✅ | Attract zone (flow field cost -50) |
| 3 | DropRepellent | 3 | ✅ | Repel zone (flow field cost +200) |
| 4 | SplitToCoord | 5 | ✅ | Detach 30% flanking group |
| 5 | MergeBack | 5 | ❌ | Recombine split group |
| 6 | Retreat | 6 | ✅ | Tactical withdrawal to coordinate |
| 7 | Scout | 4 | ✅ | Detach 10% recon group |

> **Design Principle — "The General":** Every action is an atomic primitive.
> Complex tactics (flank, lure, retreat-and-ambush) must emerge from the model composing primitives.
> See `conventions.md` for full rules.

---

## 9-Stage Curriculum (0-8)

| Stage | Name | World | Grid | Fog? | New Actions | Key Lesson | Grad WR |
|:---:|------|:---:|:---:|:---:|:---:|---|:---:|
| 0 | 1v1 Navigation | 400² | 20² | ❌ | Hold, AttackCoord | Navigate to single target | 85% |
| 1 | Target Selection | 500² | 25² | ❌ | — | Pick weak target over strong trap | 80% |
| 2 | Pheromone Path | 600² | 30² | ❌ | DropPheromone | Route through safe path via attract | 80% |
| 3 | Repellent Field | 600² | 30² | ❌ | DropRepellent | Push swarm away from danger zones | 80% |
| 4 | Fog Scouting | 800² | 40² | ✅ | Scout | Find hidden targets with recon | 80% |
| 5 | Flanking | 1000² | 50² | ✅ | Split, Merge | Pincer attack from two angles | 80% |
| 6 | Full Tactics | 1000² | 50² | ✅ | Retreat | All 8 actions, combine primitives | 80% |
| 7 | Protected Target | 1000² | 50² | ✅ | — | Full tactics vs guarded HVT | 75% |
| 8 | Randomized | varies | varies | varies | — | Generalize across all scenarios | 80% |

### Key Technical Details

- **Fog schedule:** OFF for stages 0-3, ON from stage 4+
- **Fixed tensor shape:** Observation always 50×50. Smaller maps center-padded with zeros.
- **Flattened coordinates:** `MultiDiscrete([8, 2500])` — single spatial index preserves 2D coherence.
- **LKP Memory:** Feed-forward PPO has no temporal memory. LKP buffer decays last-known enemy density at −0.02/tick under fog.
- **Debuff mechanic (stage 1):** Killing target first → trap DPS × 0.25 + trap enrages (charges brain). Brain CANNOT brute-force the trap.
- **Terrain costs:** Default = 100. Mud = 40 (soft_cost). Danger zones = 300 (hard_cost). Walls = 65535 (impassable).

---

## Reward Components

| # | Component | Value | Stages |
|---|-----------|-------|:---:|
| 1 | Time penalty | −0.01 / step | All |
| 2 | Kill reward | +0.05 per kill | All |
| 3 | Death penalty | −0.03 per death | All |
| 4 | Win terminal | +10.0 | All |
| 5 | Loss terminal | −10.0 | All |
| 6 | Survival bonus | +5.0 × (survivors/starting) | All |
| 7 | Approach | +0.02 × dist_closed | All |
| 8 | Exploration | +0.005 × new_cells (decay@80%) | 4+ (fog stages) |
| 9 | Threat priority | +2.0 weaker group first | 1+ |
| 10 | Flanking geometry | +0.1 × angle_score | 5+ |
| 11 | Debuff bonus | +2.0 (target killed before trap) | 1+ |

**Gradient:** Tactical Win (+18..+22) ≫ Brute Force (+8..+12) > Loss (−11..−13) ≈ Timeout

---

## Training History

| Date | Event |
|------|-------|
| 2026-04-08 | Old `Discrete(3)` Stage 1 — oscillation bug discovered |
| 2026-04-10 | Tactical curriculum v3 deployed — 11 tasks complete |
| 2026-04-10 | Stage 0 graduated (85% WR in 30 episodes) |
| 2026-04-10 | Stage 1 initial run: 0% WR — spatial bug (trap/target too close) |
| 2026-04-10 | Stage 1 fix 1: separated trap/target by 340+ units |
| 2026-04-10 | Stage 1 fix 2: debuff was no-oping on HP (only damage matters) |
| 2026-04-10 | Stage 1 fix 3: trap charges brain after debuff (no retargeting needed) |
| 2026-04-10 | Stages 2-3 implemented: Pheromone Path + Repellent Field terrain generators |
| 2026-04-10 | Stage 1 training in progress (run_20260410_212655), first WIN at episode 9 |

---

## Key Files

| File | Purpose |
|------|---------|
| `profiles/tactical_curriculum.json` | Master game profile (factions, combat, rewards, stages) |
| `macro-brain/src/training/curriculum.py` | Stage configs, spawn generators, terrain generators |
| `macro-brain/src/env/swarm_env.py` | Gymnasium env, action masking, debuff logic |
| `macro-brain/src/env/bot_controller.py` | Bot AI (HoldPosition, Charge, Patrol, debuff-aware) |
| `macro-brain/src/training/train.py` | Training entrypoint (--load-checkpoint, --start-stage) |
| `train.sh` | Shell wrapper for starting training runs |

> **For deep engine mechanics:** See `.agents/context/engine-mechanics.md`
> **For curriculum design details:** See `.agents/context/training-curriculum.md`
