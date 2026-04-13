# Randomized Faction Roles — Heatmap-Only Tactical Learning

## Problem

The current profile has 3 factions: Brain(0), Trap(1), Target(2). The faction roles are **fixed**: faction 1 is always the tank, faction 2 is always the squishy target. Although the observation merges enemy channels (`ch1`/`ch7`), the model could still exploit a static pattern (e.g., "the smaller blob is always the target").

We cannot collapse to 2 factions because the **debuff mechanic is essential**: after the brain kills the squishy group, the tank group gets debuffed (HP halved), making the fight winnable. Without it, the model learns cowardice.

## Design

**Keep 3 factions, but randomize roles each episode.**

On every `reset()`, flip a coin:
- **Heads**: faction 1 = tank (high HP, many units), faction 2 = squishy (low HP, few units)
- **Tails**: faction 1 = squishy, faction 2 = tank

The observation already merges all enemies into unified `ch1` (raw density) and `ch7` (ECP density). The model **cannot** distinguish faction IDs — it must read the ECP heatmap to find the correct target.

The debuff tracks `_trap_faction` and `_target_faction` dynamically, so it fires correctly regardless of which faction ID got which role.

## Proposed Changes

---

### Profile

#### [MODIFY] [tactical_curriculum.json](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/macro-brain/profiles/tactical_curriculum.json)
- Give factions neutral names: rename "Trap" → "EnemyA", "Target" → "EnemyB"
- Both get identical base stats (`hp: 100.0`) — actual stats are overridden per-episode by the curriculum spawner

---

### Curriculum Spawns

#### [MODIFY] [curriculum.py](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/macro-brain/src/training/curriculum.py)
- For **single-enemy stages** (0, 2, 3, 4, 5): spawn only faction 1 or faction 2 (randomly chosen each episode). No behavioral change.
- For **multi-group stages** (1, 6, 7, 8): randomly assign which faction ID gets tank stats vs squishy stats. Return spawn entries with appropriate per-group stat overrides.
- Add a return value or metadata that tells `SwarmEnv` which faction ID was assigned the "target" (squishy) role this episode.

---

### Environment

#### [MODIFY] [swarm_env.py](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/macro-brain/src/env/swarm_env.py)
- In `reset()`, after calling `get_spawns_for_stage()`, read the role assignment metadata to set `_trap_faction` and `_target_faction` dynamically (instead of hardcoding `1` and `2`).
- Remove hardcoded `_trap_faction = 1` / `_target_faction = 2` from `__init__`.
- All existing debuff/reward logic works unchanged — it already references `self._trap_faction` / `self._target_faction`.

---

### No Changes Needed

- **rewards.py**: `threat_priority_bonus` and `compute_shaped_reward` use faction IDs passed from the env — they don't hardcode anything.
- **callbacks.py**: CSV columns (`trap_alive`, `target_alive`) still work since they read from env info dict.
- **Rust side**: No changes. Combat rules `0↔1` and `0↔2` are symmetric. The ECP density map is per-entity, so mixed stat blocks produce correct gradients regardless of which faction has which stats.
- **vectorizer.py**: Already merges all enemy factions into `ch1`/`ch7`.

## Why This Works

1. **Observation is faction-blind**: `ch1` = all enemy density merged. `ch7` = all enemy ECP merged. No per-faction channels.
2. **Summary vector is faction-blind**: Reports normalized totals, not per-faction counts.
3. **Role randomization breaks pattern**: The model can't learn "faction 2 is always correct." Each episode, either faction could be the squishy.
4. **Debuff is preserved**: `_target_faction` is set correctly each episode. When the squishy group is eliminated → tank group gets HP halved → brain can win.
5. **ECP gradient drives learning**: Squishies appear dimmer on `ch1` (fewer units) but brighter on `ch7` (higher effective DPS per unit). The model learns: "attack the blob where ch7 > ch1."

## Verification Plan

### Automated
1. Run training for 10k timesteps. Verify logs show alternating faction assignments.
2. Verify Stage 1 episode logs: `trap_alive` and `target_alive` columns show correct tracking regardless of which faction ID was assigned.
3. Verify debuff fires correctly when target is killed first (check `debuff_applied` in logs).
