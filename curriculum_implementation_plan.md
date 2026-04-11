# Curriculum Change Plan — Stage 1 Fixes + Stages 2-4 Redesign

> **Status:** DRAFT — Pending planner review and approval
> **Created:** 2026-04-10
> **Previous plan archived to:** `.agents/history/20260410_222800_randomized_faction_roles/`

---

## Background & Current State

The 9-stage tactical curriculum is in active training. Stage 0 has graduated. Stage 1 is training with the following fixes applied in this session:

### Fixes Already Applied (This Session)

1. **Trap count reverted to 50** — brute-force is impossible (brain can't kill 50×200HP head-on)
2. **Debuff-aware charging** — when brain kills target first → `ActivateBuff` debuffs trap DPS to 25% AND trap bot switches from `HoldPosition` to `Charge` (enrages toward brain). This eliminates the retargeting problem — the fight comes to the brain.
3. **HP buff no-op discovered** — `get_multiplier()` for stat_index 0 (HP) is never read by any Rust system. The buff only affects combat damage (stat_index 2) and movement speed (stat_index 1). The `Multiplier × 0.25` on stat 0 is dead code.

### Key Insight from This Session

> No stage in the current curriculum teaches the brain to **retarget** — to kill objective A, then reassess and pursue objective B.
> The charging trap in Stage 1 works around this. But for later stages (especially scouting), the brain must learn sequential objective pursuit.

---

## Changes to Implement

### Stage 1: Target Selection ✅ DONE

No further changes needed. Current design:
- 50 brain (100HP) vs 50 trap (200HP, HoldPosition) + 50 target (24HP, HoldPosition)
- Debuff fires when target killed → trap DPS × 0.25 + trap charges brain
- Faction roles randomized each episode (50% chance trap=faction 1 or 2)
- First WIN observed at episode 9 of current training run

---

### Stage 2: Pheromone Path (600×600, 30×30 grid)

**Terrain:** Two-path map with permanent wall divider.
- Top path: fast (cost 100) but blocked by 40-unit trap fleet
- Bottom path: safe but goes through mud (soft_cost=40, 60% speed penalty)
- Wall: permanent (65535) horizontal band with gap

**Spawns:**
- Brain (50, 100HP): left side
- Trap (40, 200HP, HoldPosition): on fast top path
- Target (20, 100HP, HoldPosition): bottom-right

**Goal:** Model uses DropPheromone on bottom path to attract swarm through safe route.

**New action unlocked:** DropPheromone (index 2)

> [!NOTE]
> Implementation exists in `curriculum.py` (`_spawns_stage2` + `_terrain_two_path`).
> Needs validation after Stage 1 graduates.

---

### Stage 3: Repellent Field (600×600, 30×30 grid)

**Terrain:** Open field with 2-3 high-cost danger zones (hard_cost=300) around trap positions.

**Spawns:**
- Brain (50, 100HP): top-left
- 2-3 trap groups (15-20 units each, 200HP, HoldPosition): scattered on direct path
- Target (20, 100HP, HoldPosition): right side
- Trap count randomized (2 or 3) to prevent memorization

**Goal:** Model uses DropRepellent on danger zones to push swarm around trap engagements.

**New action unlocked:** DropRepellent (index 3)

> [!NOTE]
> Implementation exists in `curriculum.py` (`_spawns_stage3` + `_terrain_scattered_traps`).
> Needs validation after Stage 2 graduates.

---

### Stage 4: Fog Scouting + Retargeting (800×800, 40×40 grid) — NEEDS REDESIGN

**This is the key stage that needs new planning.**

Current design: single hidden target at random edge, Scout unlocked. Too simple — brain just scouts and attacks.

**Proposed redesign: Two-phase sequential objective pursuit.**

```
Fog ON. 800×800 map.
Brain (50, 100HP) at center.
Target A (15 units, 60HP) at one random edge.
Target B (15 units, 60HP) at a DIFFERENT random edge.
No traps — pure information + retargeting challenge.
```

**Win condition:** Kill BOTH targets.

**Required skill sequence:**
1. Scout → discover Target A
2. AttackCoord → kill A
3. Scout → discover Target B (different direction)
4. AttackCoord → kill B

**Why this works:**
- Neither target is dangerous (15 × 60HP = trivially killable)
- The challenge is purely informational: fog hides both, brain must actively seek
- Retargeting is REQUIRED — after killing A, brain must switch direction entirely
- Scout action gets its first real workout (recon is essential, not just decorative)

**New action unlocked:** Scout (index 7)

**Alternative considered:** Single patrol target that moves between edges. Rejected because:
- Patrol behavior is bot-controller dependent, adds complexity
- Two static targets teach a cleaner "kill → reassess → retarget" loop
- Simpler to validate win condition

---

## Stages 5-7: Complex Tactical Scenarios

> [!WARNING]
> Implementing the complete vision for Stages 5 and 6 requires significant architectural changes. We must upgrade the **Rust Micro-Core** (to handle advanced multi-faction sub-group state, complex hazard interactions, and new bot controller bait rules) and the **Debug Visualizer** (to properly render and track sub-faction splits, lure states, and Retreat vectors).
> Because of this massive scope, development will be split into multiple phased implementations.

### Stage 5: Forced Flanking / Pincer (Action: `SplitToCoord`, `MergeBack`)
**Terrain:** A strong "V" shaped forward-facing wall or extreme hazard swamp blocking a direct head-on charge. 
**Spawns:**
- **Enemy** (40 units, `HoldPosition`): Entrenched inside the V-shape, defending a strong chokepoint.
- **Brain** (60 units): Spawns out in the open.
**Mechanics:** If the Brain charges head-on via `AttackCoord`, it funnels through the chokepoint single-file and is slaughtered by the Enemy's concave formation. The AI MUST learn `SplitToCoord` to send half its forces left and half right, enveloping the enemy from multiple open angles simultaneously to win.

### Stage 6: The "Lure & Ambush" (Action: `Retreat`)
**Goal:** Organically teach Retreat as a kiting/survival mechanic to outplay aggressive (human) players.
**Terrain:** Flat open map.
**Spawns:**
- **Brain Bait Group:** 10 units spawned in the middle of the map.
- **Brain Main Army:** 80 units spawned hidden in the bottom-left corner.
- **Enemy Army:** 100 tanky units (set to `Charge` behavior) spawned right next to the Bait Group.
**Mechanics:** The Enemy will immediately aggro the Bait Group. Since it's a 10v100 fight, `Hold` or `AttackCoord` leads to instant death. The AI MUST learn to output `Retreat` on the Bait Group, kiting the enemy across the map and pulling them straight into the hidden Main Army. Once united (`MergeBack`), the massive combined force (90v100) will crush the charging enemy.

### Stage 7: Protected Target (Action: All / `Scout`)
> [!NOTE]
> Stage 7 (Protected Target): Patrol + guard + HVT design needs detailed planning. Retains placeholder config for now until underlying architecture supports advanced Stage 5/6 objectives.

---

## Documentation Updates ✅ DONE

All context documents have been updated in this session:

| File | Status |
|------|--------|
| `.agents/context/engine-mechanics.md` | **NEW** — Full Rust engine reference (combat, buffs, terrain, movement) |
| `.agents/context/training-curriculum.md` | **NEW** — Curriculum reference (all stages, rewards, bot behavior) |
| `.agents/context/ipc-protocol.md` | **REWRITTEN** — Current directive/snapshot formats |
| `.agents/context.md` | **UPDATED** — Added workflow priority rule, new file index |
| `.agents/context/conventions.md` | **UPDATED** — Fixed outdated IPC section |
| `TRAINING_STATUS.md` | **REWRITTEN** — Current actions, stages, training history |
| `docs/ipc-protocol.md` | Added LEGACY deprecation banner |
| `docs/architecture.md` | Added outdated content warning |
| `docs/study/010_*`, `013_*` | Added historical disclaimers |

---

## Files to Modify (Stage 4 Only)

### [MODIFY] `macro-brain/src/training/curriculum.py`
- Replace `_spawns_stage4()` with two-target fog scouting layout
- Add terrain generator for 800×800 flat fog map (no terrain obstacles — pure fog)
- Update `STAGE_MAP_CONFIGS[4]` if world/grid size differs from current

### [MODIFY] `macro-brain/profiles/tactical_curriculum.json`
- Update Stage 4 curriculum description
- Verify bot_stage_behaviors entry for Stage 4 has two HoldPosition groups

### [MODIFY] `macro-brain/src/env/swarm_env.py`
- Win condition check must work with 2 enemy factions both being targets (no trap/target distinction in Stage 4)
- Debuff mechanic should be INACTIVE for Stage 4 (no trap group)

### [MODIFY] Tests
- `test_tactical_integration.py` — Update Stage 4 spawn expectations
- `test_curriculum.py` — Verify new Stage 4 spawn generator

---

## Verification Plan

### Automated
1. `pytest tests/test_curriculum.py tests/test_tactical_integration.py -v` — all pass
2. Training run from Stage 1 checkpoint → verify Stage 2-4 transitions

### Manual
1. Observe Stage 1 win rate reaching 80% graduation threshold
2. Observe Stage 2 behavior — does brain use pheromone to avoid trap?
3. Observe Stage 3 behavior — does brain use repellent around danger zones?
4. Observe Stage 4 behavior — does brain scout, kill A, then retarget to B?

---

## Open Questions for Planner

> [!IMPORTANT]
> 1. **Stage 4 — Should targets be equal or different?** Both 15×60HP, or Target A slightly easier (10×40HP) to build confidence before the harder retarget to B?
> 2. **Stage 4 — Fixed edges or fully random?** Two targets always at N/S edges, or random from all 4 edges?
> 3. **When to plan Stages 5-7?** After Stage 4 graduates, or start planning now in parallel?
