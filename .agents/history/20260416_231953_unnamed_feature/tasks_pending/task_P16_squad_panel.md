# Task P16: Squad Control Panel

- **Task_ID:** `P16_squad_panel`
- **Execution_Phase:** 4 (depends on P13, P10)
- **Model_Tier:** `standard`
- **Live_System_Impact:** `safe`

## Target_Files
- `debug-visualizer/src/panels/playground/squad-panel.js` — NEW
- `debug-visualizer/src/styles/playground-overlay.css` — MODIFY (extend with squad styling)

## Dependencies
- P13 (squad manager), P10 (overlay CSS framework)

## Context_Bindings
- `implementation_plan_playground_feature_4.md` — Task 16 section (full panel DOM + styling)
- `.agents/skills/frontend-ux-ui/SKILL.md`

## Strict_Instructions
**Read `implementation_plan_playground_feature_4.md` → Task 16 section.** Create squad-panel.js overlay card: appears when activeSquadId is set, shows squad name, unit count, HP bar, current order. Action buttons: Move, Attack, Hold, Retreat, Disband. Live update from render loop. Extend playground-overlay.css with squad-specific styles (HP bar gradient, action button grid).

## Verification_Strategy
```
Test_Type: manual_steps
Acceptance_Criteria:
  - "Panel appears when squad selected"
  - "Shows live unit count and HP bar"
  - "Action buttons send correct WS commands"
  - "Disband merges squad back"
  - "Panel hides when squad eliminated/deselected"
  - "Styling matches glassmorphic overlay-card pattern"
```
