# Task P03: Unit Builder Nodes

- **Task_ID:** `P03_unit_nodes`
- **Execution_Phase:** 1 (depends on P01)
- **Model_Tier:** `standard`
- **Live_System_Impact:** `safe`

## Target_Files
- `debug-visualizer/src/node-editor/nodes/unit.js` — NEW
- `debug-visualizer/src/node-editor/nodes/stat.js` — NEW
- `debug-visualizer/src/node-editor/nodes/death.js` — NEW

## Dependencies
- P01 complete (Drawflow setup + CSS)

## Context_Bindings
- `implementation_plan_playground_feature_2.md` — Task 03 section
- `implementation_plan_playground.md` — §Node Data Schema (unit, stat, death)
- `.agents/skills/frontend-ux-ui/SKILL.md`

## Strict_Instructions
**Read `implementation_plan_playground_feature_2.md` → Task 03 section.** Build unit node (class ID, name), stat node (HP/armor/speed with sliders), death node (threshold condition). Nodes connect: Faction→Unit→Stat, Unit→Death.

## Verification_Strategy
```
Test_Type: manual_steps
Acceptance_Criteria:
  - "Can add Unit node and connect from Faction output"
  - "Stat node shows slider for initial value"
  - "Death node configurable condition (LessThanEqual)"
  - "Data stored per schema contract"
```
