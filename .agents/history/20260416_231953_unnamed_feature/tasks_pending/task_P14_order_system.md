# Task P14: Order System

- **Task_ID:** `P14_order_system`
- **Execution_Phase:** 4 (depends on P13)
- **Model_Tier:** `standard`
- **Live_System_Impact:** `safe`

## Target_Files
- `debug-visualizer/src/squads/order-system.js` — NEW
- `debug-visualizer/src/controls/init.js` — MODIFY (add right-click handler)

## Dependencies
- P13 (squad manager provides squad lifecycle)

## Context_Bindings
- `implementation_plan_playground_feature_4.md` — Task 14 section (order functions + right-click handler)

## Strict_Instructions
**Read `implementation_plan_playground_feature_4.md` → Task 14 section.** Create order-system.js with `orderMove()`, `orderAttack()`, `orderHold()`, `orderRetreat()`. Extend init.js with right-click handler: right-click on empty map = move waypoint, right-click near enemy = attack-move. Keyboard shortcuts: H=Hold, R+click=Retreat, Delete=Disband, Escape=Deselect.

## Verification_Strategy
```
Test_Type: manual_steps
Acceptance_Criteria:
  - "Right-click on map sends UpdateNavigation (Waypoint)"
  - "Right-click on enemy sends UpdateNavigation (Faction) + SetAggroMask"
  - "H sends Hold directive"
  - "Entities actually move to waypoint in simulation"
```
