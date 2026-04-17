# Task P07: Integration & Wiring

- **Task_ID:** `P07_integration_wiring`
- **Execution_Phase:** 2 (depends on P04, P05, P06)
- **Model_Tier:** `advanced`
- **Live_System_Impact:** `safe`

## Target_Files
- `debug-visualizer/src/playground-main.js` — MODIFY
- `debug-visualizer/index.html` — MODIFY
- `debug-visualizer/vite.config.js` — MODIFY

## Dependencies
- P04 (compiler), P05 (presets), P06 (layout) all complete

## Context_Bindings
- `implementation_plan_playground_feature_3.md` — Task 07 section (full wiring instructions)
- `implementation_plan_playground.md` — §Architecture Overview
- `.agents/knowledge/workflow/gotcha_dom_deletion_crashing_modules.md`

## Strict_Instructions
**Read `implementation_plan_playground_feature_3.md` → Task 07 section.** Wire all Phase 1 modules together: import Drawflow setup, mount preset gallery, connect ▶ Launch button to compiler→WS dispatch, configure Vite entry points, handle sidebar cleanup stubs, integrate minimize/expand toggle.

## Verification_Strategy
```
Test_Type: manual_steps
Acceptance_Criteria:
  - "npm run dev loads playground with node editor"
  - "Preset gallery appears on first load"
  - "Selecting preset populates node graph"
  - "▶ Launch compiles graph and sends WS commands"
  - "Entities spawn and interact correctly"
  - "Training page (/training.html) unaffected"
```
