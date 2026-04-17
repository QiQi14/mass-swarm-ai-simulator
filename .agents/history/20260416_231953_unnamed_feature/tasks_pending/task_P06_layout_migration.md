# Task P06: Layout Migration

- **Task_ID:** `P06_layout_migration`
- **Execution_Phase:** 1 (depends on P01)
- **Model_Tier:** `advanced`
- **Live_System_Impact:** `safe` — playground only

## Target_Files
- `debug-visualizer/index.html` — MODIFY
- `debug-visualizer/src/playground-main.js` — NEW

## Dependencies
- P01 complete (Drawflow setup)

## Context_Bindings
- `implementation_plan_playground_feature_1.md` — Task 06 section (full layout instructions)
- `implementation_plan_playground.md` — §Architecture Overview (ASCII layout diagram)
- `.agents/knowledge/workflow/gotcha_dom_deletion_crashing_modules.md`
- `.agents/skills/frontend-ux-ui/SKILL.md`

## Strict_Instructions
**Read `implementation_plan_playground_feature_1.md` → Task 06 section.** Remove sidebar, replace with floating overlay layout (top bar, drawflow container, bottom toolbar, side cards). Leave DOM stubs for legacy module queries. Create `playground-main.js` as the new entry point. Implement Focus Mode toggle (30%/90% opacity with frost effect).

## Verification_Strategy
```
Test_Type: manual_steps
Acceptance_Criteria:
  - "Sidebar removed, floating overlay layout renders"
  - "Top bar shows version, preset dropdown, launch button"
  - "Bottom toolbar shows node type buttons"
  - "Focus Mode toggle works (30% ↔ 90% transparency)"
  - "Canvas still renders underneath overlays"
  - "No JS errors from legacy modules (DOM stubs present)"
```
