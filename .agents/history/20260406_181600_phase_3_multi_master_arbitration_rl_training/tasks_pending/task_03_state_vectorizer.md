# Task 03: State Vectorizer (Density Heatmaps)

**Task_ID:** `task_03_state_vectorizer`
**Execution_Phase:** 1 (parallel)
**Model_Tier:** `advanced`
**Target_Files:**
  - `micro-core/src/systems/state_vectorizer.rs` (NEW)
  - `micro-core/src/systems/mod.rs` (MODIFY)
**Dependencies:** None
**Context_Bindings:**
  - `implementation_plan_feature_2.md` → Task 03 section
  - `skills/rust-code-standards`

## Strict Instructions

See `implementation_plan_feature_2.md` → **Task 03: State Vectorizer** for full instructions.

**Summary:** Create a Bevy system that computes per-faction density heatmaps (50×50 grid) from entity positions. Output: `HashMap<u32, Vec<f32>>` stored in a `DensityMaps` resource. Cell values are entity counts normalized to [0, 1]. Recomputed every 30 ticks (2 Hz).

**Key:** This is Rust-side raw data export. NO neural network channel packing (Python's job per Data Isolation principle).

## Verification_Strategy
```
Test_Type: unit
Test_Stack: cargo test (Rust)
Acceptance_Criteria:
  - Density map has correct dimensions (50 × 50 = 2500 floats)
  - Entity at known position maps to correct cell
  - Multiple entities in same cell sum correctly
  - Values normalized to [0, 1]
  - Empty faction returns empty density map
  - Separate factions get separate density maps
Suggested_Test_Commands:
  - "cd micro-core && cargo test state_vectorizer"
```
