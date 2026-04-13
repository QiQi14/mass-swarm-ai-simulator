# Study Notes: RL Training Methodology

> [!NOTE]
> **Historical document (Phase 3, 2026-04-06).** The 2-stage curriculum, `Frenzy` action, `Territory` reward,
> and action masking code shown here are all superseded. Current system uses a 9-stage tactical curriculum
> with 8 atomic primitives, `MultiDiscrete([8, 2500])` action space, and progressive stage-based action unlocking.
> See `.agents/context/training-curriculum.md` and `.agents/context/engine-mechanics.md` for current design.

> **Problem:** How to train a macro-strategy AI that controls 10,000+ swarm entities using Deep Reinforcement Learning, without the agent exploiting mathematical loopholes.

---

## The General vs. Soldiers Paradigm

The key architectural insight: the RL agent is a **General**, not a soldier. It doesn't control individual entities — it issues 8 high-level directives that modify the simulation's rule systems.

| Layer | Who | Frequency | Scope |
|-------|-----|-----------|-------|
| **General (Python)** | MaskablePPO neural network | ~2 Hz (every 30 ticks) | 8 macro-directives |
| **Soldiers (Rust)** | Bevy ECS systems | 60 TPS | Per-entity physics, steering, combat |

The General observes a 50×50 density heatmap (Occupancy Grid Map), not individual entity positions. This reduces the observation space from O(N) to O(2500), making training tractable.

---

## 2-Stage Curriculum

### Why Curriculum?
If you expose all 8 actions + procedural terrain from the start, the agent develops **Learned Helplessness** — it discovers that random terrain makes zone modifiers unreliable, so it stops using them entirely.

### Stage 1: Tactical Sandbox
| Parameter | Value |
|-----------|-------|
| Map | Flat 1000×1000 (no terrain) |
| Opponent | Heuristic Bot (Faction 1, Rust-controlled) |
| Actions | 0-3 only: Hold, UpdateNav, Frenzy, Retreat |
| Actions 4-7 | **MASKED** (MaskablePPO prevents selection) |
| Promotion condition | `mean_reward > 0.3` over 50-episode window |

The agent first learns basic combat dynamics: when to push, when to retreat, how Frenzy affects outcomes.

### Stage 2: Domain Randomization
| Parameter | Value |
|-----------|-------|
| Map | Procedural (randomized walls, chokepoints, swamps) |
| Actions | All 8 unlocked |
| Terrain | BFS-verified connectivity between spawn zones |
| Goal | Generalized strategy that transfers to unseen maps |

### Implementation
- `MaskablePPO` from `sb3-contrib` — uses `action_masks()` method to mathematically lock invalid actions
- `CurriculumCallback` — SB3 callback that monitors rolling reward and promotes when threshold reached

---

## 50×50 Grid: The OGM Decision

### The RL Curse of Dimensionality
A 50×50 grid with 5 channels = 12,500 float inputs → standard CNN converges in hours.
A 500×500 grid = 1.25M floats → CNN parameters explode, leads to **Spatial Overfitting** (memorizes pixel noise instead of learning strategy).

### The Real-World Robotics Pipeline
In autonomous systems (Drone Swarms, Tesla FSD), raw sensor data is never fed directly to decision networks:
1. **Raw sensors** → Occupancy Grid Map (OGM)
2. **OGM** → Decision network

Our 50×50 grid IS the OGM. The Rust Micro-Core maintains high-res continuous physics (1000×1000 world), while Python sees a compressed strategic view.

### Future Upgrades (Out of Scope)
- **Foveated Attention**: High-res 20×20 patch following the action epicenter + low-res 50×50 background
- **Graph Neural Networks**: Replace grid with entity-relationship graphs for better generalization

---

## Reward Shaping

### 5-Component Reward
| Component | Weight | Signal |
|-----------|--------|--------|
| Survival | +0.01/tick | Stay alive |
| Kill | +0.1/kill | Eliminate enemy entities |
| Territory | +0.05 | % of density grid cells owned |
| Health Delta | -0.1 | Penalize own health loss |
| Flanking Bonus | +0.2 | Sub-faction close to enemy flank |

### P5: Pacifist Flank Exploit
**The Flaw:** Flanking bonus relies on projecting sub-faction position onto the enemy axis. An RL agent can send a sub-faction to the map corner — geometrically aligned but out of combat range — and collect free reward.

**The Fix:**
1. **Distance cutoff:** `max_engage_radius = 15` grid cells. Sub-factions beyond this get 0.0 bonus.
2. **Distance attenuation:** Bonus scaled by `1.0 - (dist / max_engage_radius)`. Monotonically decreasing.
3. **Density check:** If sub-faction density is 0 at its centroid, bonus = 0.

---

## ZMQ Atomic Reset

### The Problem
If Python sends terrain via WebSocket (async), the RL episode might start before Rust finishes rebuilding the collision mesh. This violates the Markov Decision Process — the agent's first observation wouldn't match the terrain it's supposed to navigate.

### The Solution
Python sends terrain + spawn config inside a `ResetEnvironment` ZMQ message. Rust halts, applies the terrain, respawns entities, and returns the fresh snapshot in the same ZMQ reply. The observation is guaranteed consistent.

```
Python: send(ResetEnvironment { terrain, spawns })
Rust:   recv → apply terrain → respawn → snap = build_snapshot()
Rust:   send(snap) → back to Running
Python: recv(snap) → first observation ready
```

This requires **two ZMQ recv→send cycles** per reset (one for the reset command, one for the first state snapshot). Strict REQ/REP discipline prevents deadlocks.

---

## Action Masking (MaskablePPO)

Standard PPO allows the agent to select any action. Masked PPO adds an `action_masks()` method that returns a boolean array:

```python
def action_masks(self):
    mask = np.ones(8, dtype=bool)  # All actions enabled
    
    if self.curriculum_stage == 1:
        mask[4:8] = False  # Lock terrain-dependent actions
    
    if self.curriculum_stage == 2:
        if not self.has_sub_factions:
            mask[6] = False  # Can't merge without sub-factions
            mask[7] = False  # Can't set aggro without sub-factions
    
    return mask
```

The neural network's logits for masked actions are set to -∞ before softmax, making selection probability exactly 0.0. This is mathematically stronger than reward penalties.

---

## Self-Play (Deferred to Phase 4)

True self-play requires maintaining a history of opponent checkpoints and sampling from them during training. This introduces:
- Checkpoint management infrastructure
- Elo rating system
- Training instability from non-stationary opponents

Currently we use a heuristic bot (Faction 1 follows default Rust rules). Self-play is the natural next step once Stage 2 training converges.
