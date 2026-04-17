# Task P02: Faction Builder Nodes

- **Task_ID:** `P02_faction_nodes`
- **Execution_Phase:** 1 (depends on P01)
- **Model_Tier:** `standard`
- **Live_System_Impact:** `safe`

## Target_Files
- `debug-visualizer/src/node-editor/nodes/faction.js` — NEW
- `debug-visualizer/src/node-editor/nodes/relationship.js` — NEW

## Dependencies
- P01 complete (Drawflow setup + CSS)

## Context_Bindings
- `implementation_plan_playground_feature_2.md` — Task 02 section
- `implementation_plan_playground.md` — §Node Data Schema (faction, relationship)
- `.agents/skills/frontend-ux-ui/SKILL.md`

## Strict_Instructions
**Read `implementation_plan_playground_feature_2.md` → Task 02 section.** Build faction node (spawn config, color picker, name) and relationship node (hostile/neutral/allied). Nodes store data per the schema contract.

## Verification_Strategy
```
Test_Type: manual_steps
Acceptance_Criteria:
  - "Can add Faction node to canvas with color picker and spawn config"
  - "Can add Relationship node and connect two faction outputs to it"
  - "Faction data is stored in Drawflow data object per schema"
```
