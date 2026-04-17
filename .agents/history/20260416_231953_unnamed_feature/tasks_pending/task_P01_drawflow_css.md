# Task P01: Drawflow + CSS Foundation

- **Task_ID:** `P01_drawflow_css`
- **Execution_Phase:** 1 (Playground Foundation)
- **Model_Tier:** `standard`
- **Live_System_Impact:** `safe` — new files only

## Target_Files
- `debug-visualizer/package.json` — MODIFY (add drawflow dep)
- `debug-visualizer/src/styles/node-editor.css` — NEW
- `debug-visualizer/src/node-editor/drawflow-setup.js` — NEW

## Dependencies
- None

## Context_Bindings
- `implementation_plan_playground_feature_1.md` — Task 01 section (full strict instructions)
- `implementation_plan_playground.md` — §Shared Contracts (Node Data Schema)
- `.agents/skills/frontend-ux-ui/SKILL.md`

## Strict_Instructions

**Read `implementation_plan_playground_feature_1.md` → Task 01 section for complete details.** Summary:

1. Install `drawflow` via npm
2. Create `drawflow-setup.js`: Init Drawflow instance, configure pan/zoom, register node types, override default DOM templates with glassmorphic styling
3. Create `node-editor.css`: Override Drawflow's default styles with dark-mode glassmorphic theme matching the project design system (glass cards, accent colors, node ports)
4. Export `initDrawflow(container)` function

## Verification_Strategy
```
Test_Type: manual_steps
Acceptance_Criteria:
  - "Drawflow initializes without errors"
  - "Node editor canvas renders with dark theme"
  - "Can add/remove nodes programmatically"
  - "Pan/zoom works on the canvas"
Manual_Steps:
  - "npm run dev → open localhost → verify Drawflow canvas renders"
```
