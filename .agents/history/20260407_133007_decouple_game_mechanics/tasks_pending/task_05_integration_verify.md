# Task 05: Integration Verification

- **Task_ID:** task_05_integration_verify
- **Execution_Phase:** 4 (sequential — after Task 04)
- **Model_Tier:** standard
- **Feature:** Decoupling Game Mechanics

## Target_Files
- All files modified by Tasks 01-04 (read-only audit)
- Any test files that need final fixups

## Dependencies
- Task 01, Task 02, Task 03, Task 04 (all completed)

## Context_Bindings
- `context/architecture`
- `context/ipc-protocol`
- `skills/rust-code-standards`

## Strict_Instructions

### Goal
Verify the complete refactor compiles, all tests pass, and no hardcoded game logic remains.

### Step 1: Rust Build + Test

```bash
cd micro-core && cargo build --release
cd micro-core && cargo test
cd micro-core && cargo clippy
```

**All must pass. If any fail, fix the issue.**

### Step 2: Python Test

```bash
cd macro-brain && source venv/bin/activate
python -m pytest tests/ -v --ignore=tests/test_terrain_generator.py --ignore=tests/test_swarm_env.py
```

**All must pass.**

### Step 3: Audit for Remaining Violations

ALL of these greps must return ZERO results:

```bash
# Game-specific type names
grep -r "FrenzyConfig" micro-core/src/
grep -r "FactionSpeedBuffs" micro-core/src/
grep -r "TriggerFrenzy" micro-core/src/
grep -r "TriggerFrenzy" macro-brain/src/
grep -r "TriggerFrenzy" macro-brain/tests/

# Hardcoded constants
grep -r "DEFAULT_MAX_DENSITY" micro-core/src/
grep -r "TERRAIN_DESTRUCTIBLE" micro-core/src/
grep -r "TERRAIN_PERMANENT" micro-core/src/

# Wave spawn system (removed)
grep -rn "wave_spawn" micro-core/src/ --include="*.rs" | grep -v "^.*:.*//.*wave"

# Hardcoded stat names in buff data structures
grep -rn "speed_multiplier\|damage_multiplier" micro-core/src/config.rs
grep -rn "damage_multiplier_enabled" micro-core/src/

# Game-specific naming in Python
grep -r "Frenzy" macro-brain/profiles/
grep -r "ACTION_FRENZY" macro-brain/src/
```

### Step 4: Verify Profile Completeness

`default_swarm_combat.json` must include:
- `world` ✓
- `factions` ✓
- `combat` ✓
- `movement` (max_speed, steering_factor, etc.) ✓
- `terrain_thresholds` (impassable_threshold, destructible_min) ✓
- `removal_rules` (stat_index + condition) ✓
- `abilities` with `buff_cooldown_ticks`, stat mappings, and `activate_buff` with `modifiers` ✓
- `training` with `max_density` ✓
- `actions` with `ActivateBuff` ✓

### Step 5: Verify Contracts Match

Ensure Rust ZMQ `ResetEnvironment` fields and Python `SwarmEnv.reset()` payload keys are identical:
- `terrain`, `spawns`, `combat_rules`, `ability_config`, `movement_config`, `max_density`, `terrain_thresholds`, `removal_rules`

### Step 6: Document Results

Write a brief summary of:
- Total test counts (Rust + Python)
- Any fixes made during verification
- Confirmation that all 10 violations are resolved

## Verification_Strategy
  Test_Type: integration
  Test_Stack: Rust (cargo test) + Python (pytest)
  Acceptance_Criteria:
    - "`cargo build --release` succeeds"
    - "`cargo test` all pass"
    - "`cargo clippy` no new warnings"
    - "`python -m pytest` all pass"
    - "Zero grep hits for ANY hardcoded game logic"
    - "Profile JSON includes ALL injectable sections"
    - "Buff system is fully stat-index-based (no speed/damage names in data)"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test"
    - "cd micro-core && cargo clippy"
    - "cd macro-brain && source venv/bin/activate && python -m pytest tests/ -v --ignore=tests/test_terrain_generator.py --ignore=tests/test_swarm_env.py"
