# Task P10: Terrain + Sim Controls Overlay

- **Task_ID:** `P10_terrain_sim_controls`
- **Execution_Phase:** 2 (depends on P07)
- **Model_Tier:** `standard`
- **Live_System_Impact:** `safe`

## Target_Files
- `debug-visualizer/src/panels/playground/terrain-overlay.js` — NEW
- `debug-visualizer/src/panels/playground/sim-controls-overlay.js` — NEW
- `debug-visualizer/src/styles/playground-overlay.css` — NEW

## Dependencies
- P07 (integration — overlay mount points available)

## Context_Bindings
- `implementation_plan_playground_feature_3.md` — Task 10 section
- `.agents/skills/frontend-ux-ui/SKILL.md`

## Strict_Instructions
**Read `implementation_plan_playground_feature_3.md` → Task 10 section.** Create terrain paint overlay card (brush size, cost selector, paint mode toggle). Create sim controls overlay card (play/pause/step, speed slider, tick display). Both cards use glassmorphic `overlay-card` pattern. Create shared `playground-overlay.css` with card styling.

## Verification_Strategy
```
Test_Type: manual_steps
Acceptance_Criteria:
  - "Terrain overlay card with brush size and cost controls"
  - "Sim controls with play/pause/step buttons"
  - "Speed slider adjusts TPS"
  - "Cards match overlay-card glassmorphic pattern"
```
