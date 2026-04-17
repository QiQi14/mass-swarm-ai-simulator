# Task P08: Combat + Relationship Nodes

- **Task_ID:** `P08_combat_relationship`
- **Execution_Phase:** 2 (depends on P07, R01)
- **Model_Tier:** `standard`
- **Live_System_Impact:** `safe`

## Target_Files
- `debug-visualizer/src/node-editor/nodes/combat.js` — NEW
- `debug-visualizer/src/node-editor/nodes/relationship.js` — MODIFY (extend with combat presets)
- `debug-visualizer/src/node-editor/compiler.js` — MODIFY (extend with combat compilation)

## Dependencies
- P07 (integration), R01 (WS set_interaction enhancement)

## Context_Bindings
- `implementation_plan_playground_feature_3.md` — Task 08 section
- `implementation_plan_playground.md` — §Node Data Schema (combat)

## Strict_Instructions
**Read `implementation_plan_playground_feature_3.md` → Task 08 section.** Build combat node (attack type presets, damage, range, cooldown), extend relationship node with visual indicators, extend compiler to produce interaction rules from combat chains.

## Verification_Strategy
```
Test_Type: manual_steps
Acceptance_Criteria:
  - "Combat node shows attack type dropdown (melee/ranged/siege)"
  - "Connecting attacker→combat→target produces interaction rule"
  - "Compiled output has correct interaction rule JSON"
```
