# The Gymnasium Environment

Located in `src/env/`, this module translates the raw Rust physics engine into a Gymnasium-compatible format for RL training.

## Architecture

```
┌─────────────┐    ZMQ (tcp:5555)    ┌──────────────┐
│  SwarmEnv    │ ◄──────────────────► │  Micro-Core  │
│  (Python)    │  JSON snapshots      │  (Rust/Bevy) │
│              │  + directives        │              │
└─────────────┘                      └──────────────┘
```

`SwarmEnv` (`swarm_env.py`) implements the standard Gymnasium API:
```python
observation, reward, terminated, truncated, info = env.step(action)
```

### How it works:
1. **Reset**: `env.reset()` sends a "reset" payload with spawns, combat rules, and terrain to Rust. The engine clears and rebuilds the map. Returns the first observation.
2. **Step**: The AI picks an action (discrete int). `SwarmEnv` converts it to a `MacroDirective` JSON payload, batched with bot controller directives, and sends to Rust. Rust runs for `ai_eval_interval_ticks` ticks, pauses, and replies with a state snapshot.
3. **Action Masking**: Uses `MaskablePPO` from `sb3-contrib`. Invalid actions (e.g., cooldown-locked abilities) are masked so the model can't select them.

## Action Space (Stage 1)

3 discrete actions for target selection training:

| Index | Name | Directive | Description |
|-------|------|-----------|-------------|
| 0 | **Hold** | `Hold(brain_faction)` | Active brake — clears nav rules, stops movement |
| 1 | **AttackNearest** | `UpdateNav(brain → nearest_enemy)` | Navigate to closest alive enemy faction centroid |
| 2 | **AttackFurthest** | `UpdateNav(brain → furthest_enemy)` | Navigate to farthest alive enemy faction centroid |

Nearest/furthest is computed **dynamically each step** from live density grid centroids. When one enemy faction is eliminated, both attack actions converge to the remaining faction.

## Observation Space (`spaces.py`)

Multi-channel 2D density grid (CNN-compatible):

| Channel | Content |
|---------|---------|
| 0 | Own faction density |
| 1 | Enemy faction 1 density |
| 2 | Enemy faction 2 density |
| 3 | Terrain / obstacles |
| 4 | Summary stats (embedded) |

Shape: `(channels, grid_height, grid_width)` — default `(5, 50, 50)`.

## Reward Shaping (`rewards.py`)

Dense per-step rewards to guide learning:

| Component | Value | Purpose |
|-----------|-------|---------|
| Time penalty | -0.01/step | Prevents idling |
| Kill reward | +0.05/kill | Incentivizes engagement |
| Death penalty | -0.03/death | Punishes attrition |
| Win terminal | +10.0 | Victory bonus |
| Loss terminal | -10.0 | Defeat penalty |
| Survival bonus | 5.0 × (survivors/total) | Rewards clean wins |
| **Timeout = Loss** | -10.0 | Closes "hold til timeout" exploit |
| **Approach reward** | +0.02/unit closer | Closes toggle exploit (see below) |

### Approach Reward (Anti-Toggle)

Per-step reward for closing distance to the nearest enemy. Prevents the toggle exploit where the model zig-zags between targets (net-zero distance change = no approach reward) instead of committing to one target.

## Curriculum System

### 3-Sub-Stage Target Selection

Training uses a progressive curriculum to prevent entropy collapse:

| Sub-Stage | Layout | Correct Action | Graduation |
|-----------|--------|----------------|------------|
| **1** | Target at NEAR position | AttackNearest | 80% win rate, 20 consecutive episodes |
| **2** | Target at FAR position | AttackFurthest | 80% win rate, 20 consecutive episodes |
| **3** | Randomized 50/50 | Read density grid | 80% win rate, 20 consecutive episodes |

### Debuff Mechanic

When the Target (20 units) is killed while the Trap (50 units) is still ≥50% alive:
- **HP debuff**: 0.25× (Trap entities drop to 25 HP)
- **DPS debuff**: 0.25× (Trap entities deal 75% less damage via `combat_damage_stat`)

This creates a massive reward gradient: correct target order → easy win (+15), wrong order → mutual death (-10).

## Bot Controller (`bot_controller.py`)

Enemy factions are controlled by a `BotController` with configurable strategies:
- **HoldPosition**: Stay at spawn (active brake)
- **Charge**: Navigate toward brain faction
- **Adaptive**: Switch between charge/retreat based on numbers

Currently Stage 1 uses `HoldPosition` for both Trap and Target.
