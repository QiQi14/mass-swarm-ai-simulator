# RL Overview

## 1. Design Principle: "The General"

> The model is a General, not a state machine picker.

- Every action is an **atomic primitive** (see `conventions.md`)
- Complex tactics (flank, lure, retreat-and-ambush) must **emerge** from the model composing primitives
- Stages teach ONE new skill each, then the model combines them in later stages
- If a stage can be brute-forced (won without using the intended skill), the stage is poorly designed

---

## 2. Stage Summary

| Stage | Name | New Action | Fog | Key Mechanic |
|-------|------|-----------|-----|-------------|
| 0 | 1v1 Navigation | Hold, AttackCoord | OFF | Find and kill single target |
| 1 | Target Selection | — | OFF | Pick weak target over strong trap |
| 2 | Pheromone Path | DropPheromone | OFF | Route through safe path via pheromone |
| 3 | Repellent Field | DropRepellent | OFF | Push swarm away from danger zones |
| 4 | Fog Scouting | Scout | **ON** | Find hidden targets with recon |
| 5 | Flanking | SplitToCoord, MergeBack | ON | Pincer attack from two angles |
| 6 | Full Tactics | Retreat | ON | All 8 actions, combine primitives |
| 7 | Protected Target | — | ON | Full tactics vs guarded HVT |
| 8 | Randomized | — | ON | Random scenario from pool |

### Graduation Requirements

Each stage requires sustained win rate (rolling window) + minimum episodes:

| Stage | Win Rate | Min Episodes | Extra |
|-------|----------|-------------|-------|
| 0 | 85% | 30 | — |
| 1 | 80% | 50 | — |
| 2 | 80% | 50 | — |
| 3 | 80% | 50 | — |
| 4 | 80% | 50 | — |
| 5 | 80% | 50 | avg_flanking_score ≥ 0.3 |
| 6 | 80% | 50 | — |
| 7 | 75% | 100 | — |
| 8 | 80% | 500 | — |

---

## 5. Key Files

| File | Responsibility |
|------|---------------|
| `macro-brain/src/training/curriculum.py` | Stage configs, spawn generators, terrain generators |
| `macro-brain/src/env/swarm_env.py` | Action unlock schedule, debuff logic, win/loss detection |
| `macro-brain/src/env/bot_controller.py` | Bot AI (HoldPosition, Charge, Patrol, debuff-aware charging) |
| `macro-brain/src/training/callbacks.py` | Graduation logic, episode logging |
| `macro-brain/profiles/tactical_curriculum.json` | Master profile (factions, combat rules, rewards, stage descriptions) |

---

## 9. Common Pitfalls & Gotchas

> [!CAUTION]
> **HP buff is inert.** Buff modifiers on stat_index 0 (HP) are stored but never read.
> To reduce enemy HP, use combat damage (interaction rules), not buff multipliers.
> See `engine-mechanics.md` Section 3.

> [!WARNING]
> **Terrain default cost is 100, not 0.** Sending all-zero terrain makes every cell "free" 
> for pathfinding, which breaks cost comparisons. Always use 100 as baseline.

> [!WARNING]
> **get_spawns_for_stage() returns a TUPLE**, not a list.
> Format: `(spawns_list, role_meta_dict)` where role_meta has `trap_faction` and `target_faction`.

> [!NOTE]
> **Episode length:** `max_steps=500` in profile, but `FrameSkipWrapper(skip=5)` means
> `500/5 = 100` outer steps. Each outer step = 5 × 30 = 150 simulation ticks.
> Total episode = 15,000 ticks = 250 sim-seconds at 60 TPS.