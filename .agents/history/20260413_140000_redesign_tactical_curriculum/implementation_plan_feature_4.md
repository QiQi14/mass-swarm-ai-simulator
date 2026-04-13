# Feature 5: Environment Integration & Tuning (Tasks 06–08)

## Purpose

Wire the stage-specific combat rules, unit types, ch6 activation, and reward adjustments into the SwarmEnv training loop. Update the profile for 10 stages.

---

## Task 06: SwarmEnv Integration

### Target Files

- `macro-brain/src/env/swarm_env.py`

### Dependencies

- Task 02 (`stage_combat_rules.py` must exist)
- Task 03 (updated spawn generators in `curriculum.py`)
- Task 04 (V-wall terrain generator)
- Task 05 (ch6 sub-faction density in vectorizer)

### Live System Impact: `destructive`

> [!WARNING]
> **Training MUST be paused before this task runs.** This modifies `SwarmEnv.reset()` payload construction.

### Strict Instructions

#### Step 1: Import stage combat rules

Add to imports at top of `swarm_env.py`:

```python
from src.training.stage_combat_rules import get_stage_combat_rules, get_stage_unit_types
```

#### Step 2: Add `_effective_stage` tracking

Add new instance variable in `__init__`:

```python
self._effective_stage: int = 0  # Resolved stage (handles Stage 9 delegation)
```

#### Step 3: Modify `reset()` to include stage-specific combat rules

In the `reset()` method, after building spawns (~line 218–222), resolve the effective stage and build merged combat rules:

```python
# Resolve effective stage (for Stage 9 delegation)
effective_stage = self.curriculum_stage
if self.curriculum_stage == 9:
    from src.training.curriculum import get_last_stage9_choice
    effective_stage = get_last_stage9_choice()
self._effective_stage = effective_stage

# Build merged combat rules: base melee + stage-specific
base_combat_rules = self.profile.combat_rules_payload()
stage_combat_rules = get_stage_combat_rules(
    effective_stage,
    enemy_faction=self._trap_faction,
    brain_faction=self.brain_faction,
)
all_combat_rules = base_combat_rules + stage_combat_rules
```

Replace `payload["combat_rules"]` with:
```python
"combat_rules": all_combat_rules,
```

#### Step 4: Add unit_types to reset payload

After building the payload dict:

```python
unit_types = get_stage_unit_types(effective_stage)
if unit_types is not None:
    payload["unit_types"] = unit_types
```

#### Step 5: Use `_effective_stage` for stage-specific logic

Update these references from `self.curriculum_stage` to `self._effective_stage`:

1. **Intel ping** (~line 387): `if self._effective_stage == 4:` (fires when Stage 9 picks Stage 4)
2. **Flanking score** (~line 432): Already uses `self.curriculum_stage >= 5`, keep as-is (Stage 9 always ≥ 5)
3. **Reward computation**: Pass `self._effective_stage` as the `stage` argument

#### Step 6: Update `_get_stage_action_unlock()` for 10 stages

No change needed — the existing unlock schedule covers Stages 0–6+, and Stages 7–9 inherit Stage 6's full unlock. But verify the max_substage in `CurriculumCallback` is updated to 9.

---

## Task 07: Profile & Curriculum Updates

### Target Files

- `macro-brain/profiles/tactical_curriculum.json`
- `macro-brain/src/training/callbacks.py`
- `.agents/context/training/stages.md`

### Dependencies

- Task 06 (env integration complete)

### Live System Impact: `destructive`

### Strict Instructions

#### Step 1: Update `tactical_curriculum.json`

Add 10-stage curriculum (0–9) with updated descriptions:

```json
"curriculum": [
  { "stage": 0, "description": "1v1 Navigation: learn to aim AttackCoord at a single enemy group",
    "graduation": { "win_rate": 0.85, "min_episodes": 30 } },
  { "stage": 1, "description": "Target Selection: read density, pick correct target among distractors",
    "graduation": { "win_rate": 0.80, "min_episodes": 50 } },
  { "stage": 2, "description": "Pheromone Path: use DropPheromone to redirect swarm through safe route",
    "graduation": { "win_rate": 0.80, "min_episodes": 50 } },
  { "stage": 3, "description": "Repellent Field: use DropRepellent to push swarm away from trap groups",
    "graduation": { "win_rate": 0.80, "min_episodes": 50 } },
  { "stage": 4, "description": "Fog Scouting: use Scout to find hidden enemy in fog, navigate with LKP",
    "graduation": { "win_rate": 0.80, "min_episodes": 50 } },
  { "stage": 5, "description": "Forced Flanking: enemy has AoE cone — split and pincer from two angles",
    "graduation": { "win_rate": 0.80, "min_episodes": 50, "avg_flanking_score_min": 0.3 } },
  { "stage": 6, "description": "Spread Formation: enemy has AoE circle splash — spread units to survive",
    "graduation": { "win_rate": 0.80, "min_episodes": 50 } },
  { "stage": 7, "description": "Combined Arms: learn to use heterogeneous Infantry + Tank army",
    "graduation": { "win_rate": 0.80, "min_episodes": 50 } },
  { "stage": 8, "description": "Screening: enemy has kinetic penetration — Tanks body-block for Infantry",
    "graduation": { "win_rate": 0.75, "min_episodes": 100 } },
  { "stage": 9, "description": "Randomized Graduation: random scenarios from all stages",
    "graduation": { "win_rate": 0.80, "min_episodes": 500 } }
]
```

#### Step 2: Add bot behaviors for new stages

```json
{ "stage": 5, "faction_id": 1, "strategy": { "type": "HoldPosition" }, "eval_interval_ticks": 60 },
{ "stage": 5, "faction_id": 2, "strategy": { "type": "HoldPosition" }, "eval_interval_ticks": 60 },
{ "stage": 6, "faction_id": 1, "strategy": { "type": "Charge", "target_faction": 0 }, "eval_interval_ticks": 60 },
{ "stage": 6, "faction_id": 2, "strategy": { "type": "Charge", "target_faction": 0 }, "eval_interval_ticks": 60 },
{ "stage": 7, "faction_id": 1, "strategy": { "type": "Charge", "target_faction": 0 }, "eval_interval_ticks": 60 },
{ "stage": 7, "faction_id": 2, "strategy": { "type": "Charge", "target_faction": 0 }, "eval_interval_ticks": 60 },
{ "stage": 8, "faction_id": 1, "strategy": { "type": "HoldPosition" }, "eval_interval_ticks": 60 },
{ "stage": 8, "faction_id": 2, "strategy": { "type": "HoldPosition" }, "eval_interval_ticks": 60 }
```

> [!NOTE]
> Stage 7 enemy uses Charge (rushes the brain) so the brain must engage with its mixed force. Stage 8 turrets HoldPosition (entrenched defense).

#### Step 3: Update `callbacks.py`

1. Set `max_substage = 9` in `CurriculumCallback.__init__()` default
2. Align `_get_unlocked_actions()` with `SwarmEnv._get_stage_action_unlock()`
3. Add flanking score logging for Stages 5+
4. Add Stage 8 graduation check for timeout_rate_max

#### Step 4: Update `stages.md` context doc

Replace Stages 5–8 entries with new Stages 5–9 per strategy brief.

---

## Task 08: Reward Tuning

### Target Files

- `macro-brain/src/env/rewards.py`
- `macro-brain/src/env/swarm_env.py` (spread score computation)

### Dependencies

- Task 06 (env integration)

### Live System Impact: `additive`

### Strict Instructions

#### Step 1: Disable death penalty for Stage 6

In `compute_shaped_reward()` line 289-290, extend the death penalty exemption:

```python
if stage in (4, 6):
    own_lost = 0  # Eliminate death penalty for Stages 4 and 6
```

#### Step 2: Update exploration reward eligibility

In `compute_shaped_reward()` line 307, enable exploration for all fog-enabled stages (4+):

```python
if stage >= 4 and fog_explored is not None:
    reward += exploration_reward(...)
```

#### Step 3: Add spread formation metric (SwarmEnv side)

In `SwarmEnv.step()`, compute spread score before reward calculation:

```python
# Spread score for AoE-aware formation reward (Stage 6+)
spread_score = 0.0
if self._effective_stage >= 6:
    friendly_density = obs.get("ch0")
    own_count = self._get_own_count(snapshot)
    if friendly_density is not None and own_count > 0:
        nonzero = np.sum(friendly_density > 0.01)
        spread_score = min(float(nonzero) / max(own_count, 1), 1.0)
```

Pass `spread_score` to `compute_shaped_reward()` via kwargs.

> [!NOTE]
> **Spread score intuition:** If 60 units occupy 60 different cells, `spread_score = 1.0` (perfectly spread). If all 60 units clump in 1 cell, `spread_score = 0.017` (clumped = bad). The reward function applies `flanking_bonus_scale * spread_score` as an incentive.

---

## Verification Strategy

### Task 06 (Integration)

```yaml
Acceptance_Criteria:
  - "SwarmEnv.reset() at Stage 5 sends 5 combat rules (4 base + 1 AoE cone)"
  - "SwarmEnv.reset() at Stage 6 sends 5 combat rules (4 base + 1 AoE circle)"
  - "SwarmEnv.reset() at Stage 7 sends 4 combat rules (base only) + unit_types"
  - "SwarmEnv.reset() at Stage 8 sends 5 combat rules + unit_types"
  - "Stage 9 correctly delegates to sub-stage combat rules"
  - "No regression: Stages 0-4 reset payloads unchanged"
```

### Task 07 (Profile)

```yaml
Acceptance_Criteria:
  - "Profile loads with 10 curriculum stages (0-9)"
  - "Bot behaviors for Stage 6 return Charge strategy"
  - "Bot behaviors for Stage 7 return Charge strategy"
  - "Bot behaviors for Stage 8 return HoldPosition strategy"
  - "max_substage defaults to 9 in CurriculumCallback"
```

### Task 08 (Rewards)

```yaml
Acceptance_Criteria:
  - "Stage 6 death penalty is 0"
  - "Exploration reward active for all stages >= 4"
  - "Spread score computed and passed to reward function"
  - "Reward gradient maintained: Clean Win > Bloody Win > Timeout > Loss"
```
