# Tactical Training Refactor — Speed Chase & ECP Formula

## Summary
Completed the implementation phase for the V-05 tactical training refactor. The previously approved architecture for `ActivateSkill`, Multi-Stat `ECP`, and the `Stage 6` redesign is now live.

## Changes Completed

### 1. Multi-Skill System
- Added `SkillDef` model to `definitions.py`.
- Updated `parser.py` to parse `skills` from profile into `AbilitiesDef`.
- Replaced `Retreat` with `ActivateSkill` in `spaces.py` and `actions.py`.
- Mapped coordinate argument to `skill_idx % len(skills)`.
- Updated `brain_directive` construction to correctly trigger `ActivateBuff` based on the targeted skill.

### 2. ECP Calculation
- Added `ecp_formula` support to Rust `DensityConfig` in `buff.rs`.
- Updated `snapshot.rs` to compute `primary_stat` as the product of all `stat_indices` provided in the `ecp_formula`.
- Wired `get_stage_ecp_formula()` in Python's `stage_combat_rules.py` to return the multi-stat formula for Stages 5+.
- Plumbed `ecp_formula` deep into the Python `swarm_env.py` reset payload.

### 3. Stage 6 Speed Chase (Redesign)
- Modified `curriculum.py` for Stage 6 to use a horizontal layout (x=100 Brain vs x=350 Enemy vs x=800 Ally).
- Brain speed is set to 55 (slower than pursuing enemy at 60). Brain must use the new `SpeedBoost` skill to survive.
- Updated `tactical_curriculum.json` bot behaviors for Stage 6: Enemy charges, Ally holds position.
- Refined Stage 6 description to match scenario.
- Restored the death penalty for Stage 6 in `rewards.py` (making the chase penalize the brain heavily if it is caught).

## System Impact
The Rust core tests pass, confirming `DensityConfig` serialization works. The new skill index math prevents out-of-bound errors, and the pipeline cleanly passes configuration to the `EcpFormulaPayload` analog logic. Training scripts are ready to resume execution.
