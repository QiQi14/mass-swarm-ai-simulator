# Task P12: Selection System

- **Task_ID:** `P12_selection_system`
- **Execution_Phase:** 4 (depends on P07)
- **Model_Tier:** `standard`
- **Live_System_Impact:** `safe`

## Target_Files
- `debug-visualizer/src/controls/selection.js` — NEW
- `debug-visualizer/src/state.js` — MODIFY (add selection state)

## Dependencies
- P07 (integration — canvas event handlers available)

## Context_Bindings
- `implementation_plan_playground_feature_4.md` — Task 12 section (full box-select + faction-click algorithms)

## Strict_Instructions
**Read `implementation_plan_playground_feature_4.md` → Task 12 section.** Add selection state to state.js (selectedEntities, selectionBox, activeSquadId). Create selection.js with `boxSelect()`, `factionClickSelect()`, `getSelectionCentroid()`, `getSelectionStats()`. Integrate with canvas mouse events for left-click-drag box-select and left-click faction-select.

## Verification_Strategy
```
Test_Type: manual_steps
Acceptance_Criteria:
  - "Left-click-drag draws selection box on canvas"
  - "Releasing box highlights selected entities (glow ring)"
  - "Left-click on cluster selects nearby same-faction entities"
  - "Escape clears selection"
  - "Performance: <5ms for 10K entities box-select"
```
