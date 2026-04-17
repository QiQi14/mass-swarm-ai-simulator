# Task P13: Squad Manager

- **Task_ID:** `P13_squad_manager`
- **Execution_Phase:** 4 (depends on P12)
- **Model_Tier:** `advanced`
- **Live_System_Impact:** `safe`

## Target_Files
- `debug-visualizer/src/squads/squad-manager.js` — NEW
- `debug-visualizer/src/state.js` — MODIFY (add squad registry)

## Dependencies
- P12 (selection system provides selected entities)

## Context_Bindings
- `implementation_plan_playground_feature_4.md` — Task 13 section (full squad lifecycle algorithms)

## Strict_Instructions
**Read `implementation_plan_playground_feature_4.md` → Task 13 section.** Add squad registry to state.js. Create squad-manager.js with `createSquadFromSelection()` (SplitFaction WS), `disbandSquad()` (MergeFaction WS), `getSquadStats()`, `pruneDeadSquads()`. Auto-naming (Alpha, Bravo...), faction color offsetting.

## Verification_Strategy
```
Test_Type: manual_steps
Acceptance_Criteria:
  - "Box-select → Create Squad button → SplitFaction sent"
  - "Squad appears in registry with auto-name"
  - "Disband → MergeFaction sent → entities return to parent"
  - "Dead squads auto-pruned when all entities eliminated"
```
