# Task P09: Nav + Waypoint + Movement Nodes

- **Task_ID:** `P09_nav_waypoint`
- **Execution_Phase:** 2 (depends on P07, R01)
- **Model_Tier:** `standard`
- **Live_System_Impact:** `safe`

## Target_Files
- `debug-visualizer/src/node-editor/nodes/navigation.js` — NEW
- `debug-visualizer/src/node-editor/nodes/waypoint.js` — NEW
- `debug-visualizer/src/node-editor/nodes/movement.js` — NEW
- `debug-visualizer/src/node-editor/compiler.js` — MODIFY (extend with nav compilation)

## Dependencies
- P07 (integration), R01 (WS spawn_wave movement config)

## Context_Bindings
- `implementation_plan_playground_feature_3.md` — Task 09 section
- `implementation_plan_playground.md` — §Node Data Schema (navigation, waypoint, movement)

## Strict_Instructions
**Read `implementation_plan_playground_feature_3.md` → Task 09 section.** Build navigation node (follower/target ports), waypoint node (map-click coordinate picker), movement node (speed presets, engagement range). Extend compiler to produce navigation rules and movement configs.

## Verification_Strategy
```
Test_Type: manual_steps
Acceptance_Criteria:
  - "Navigation node connects follower faction to target faction/waypoint"
  - "Waypoint node allows coordinate input"
  - "Movement node speed presets (slow/normal/fast) set correct values"
  - "Compiled output has navigation rules"
```
