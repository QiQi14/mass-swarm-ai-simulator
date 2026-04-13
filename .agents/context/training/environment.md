# RL Environment

## 4. Observation Space

**Files:** `macro-brain/src/utils/vectorizer.py`, `macro-brain/src/env/spaces.py`

The CNN observes the battlefield as **8 spatial channels** (50×50 grids) + **12-dim summary vector**.

### Channel Layout

| Ch | Content | Block | Active From | Initial Value |
|----|---------|-------|------------|---------------|
| ch0 | All friendly count density | 🟦 Force | Stage 0 | Live |
| ch1 | All enemy count density | 🟦 Force | Stage 0 | Live |
| ch2 | All friendly ECP density | 🟦 Force | Stage 0 | Live |
| ch3 | All enemy ECP density | 🟦 Force | Stage 0 | Live |
| ch4 | Terrain cost (base + pheromone/repellent) | 🟩 Environment | Stage 0 | Live |
| ch5 | Fog awareness (merged 3-level) | 🟩 Environment | Stage 4+ | 1.0 |
| ch6 | Interactable terrain overlay | 🟨 Tactical | Future | 0.0 |
| ch7 | System objective signal | 🟨 Tactical | Future | 0.0 |

**Block organization:**
- 🟦 **Force** (ch0-3): Symmetric own-vs-enemy force picture. Count = WHERE, ECP = HOW STRONG.
- 🟩 **Environment** (ch4-5): Terrain traversability and intelligence state.
- 🟨 **Tactical** (ch6-7): Plumbed as zeros, activated when game mechanics exist.

**Key semantics:**
- ch0 includes brain + active sub-factions (merged "all friendly")
- ch5 fog: 0.0 = unknown, 0.5 = explored but hidden (LKP zone), 1.0 = visible
- ch2 vs ch3 enables engage/retreat decisions: `ch2[cell] > ch3[cell]` = stronger here
- ch4 already reflects pheromone/repellent effects (zone modifiers write to cost map)

### Summary Vector (12-dim)

| Index | Content | Normalization |
|-------|---------|---------------|
| 0 | Own alive count | / max_entities |
| 1 | Enemy alive count | / max_entities |
| 2 | Own avg HP | / max_hp |
| 3 | Enemy avg HP | / max_hp |
| 4 | Sub-faction count | / max_sub_factions |
| 5 | Own total HP | / (max_entities × max_hp) |
| 6 | Enemy total HP | / (max_entities × max_hp) |
| 7 | Time elapsed | / max_steps |
| 8 | Fog explored % | [0, 1] |
| 9 | Has sub-factions | 0 or 1 |
| 10 | Intervention active | 0 or 1 |
| 11 | Force ratio | own/(own+enemy) |

> [!IMPORTANT]
> **`max_hp` is auto-computed** from spawn stats each episode. This replaces hardcoded constants (100.0, 200.0) that broke normalization for heterogeneous unit types (200 HP traps, 24 HP targets).

---

## 7. Reward Structure

**File:** `macro-brain/src/env/rewards.py`

| Component | Value | Purpose |
|-----------|-------|---------|
| `time_penalty_per_step` | -0.01 | Encourage speed |
| `kill_reward` | +0.05 per kill | Reward damage |
| `death_penalty` | -0.03 per death | Penalize losses |
| `win_terminal` | +10.0 | Victory bonus |
| `loss_terminal` | -10.0 | Defeat penalty |
| `survival_bonus_multiplier` | 5.0 | Bonus × surviving own units |
| `approach_scale` | 0.02 | Reward for closing distance to target |
| `exploration_reward` | 0.005 | Reward for exploring new fog cells |
| `threat_priority_bonus` | 2.0 | Bonus for engaging the correct target |
| `flanking_bonus_scale` | 0.1 | Bonus for angular separation in attacks |
| `debuff_bonus` | 2.0 | Bonus when debuff fires (target killed first) |

---