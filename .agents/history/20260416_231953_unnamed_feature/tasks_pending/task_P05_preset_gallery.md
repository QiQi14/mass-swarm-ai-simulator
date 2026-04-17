# Task P05: Preset Gallery Splash

- **Task_ID:** `P05_preset_gallery`
- **Execution_Phase:** 1 (no dependencies)
- **Model_Tier:** `standard`
- **Live_System_Impact:** `safe`

## Target_Files
- `debug-visualizer/src/node-editor/preset-gallery.js` — NEW
- `debug-visualizer/src/styles/preset-gallery.css` — NEW

## Dependencies
- None (standalone component)

## Context_Bindings
- `implementation_plan_playground_feature_1.md` — Task 05 section
- `.agents/skills/frontend-ux-ui/SKILL.md`

## Strict_Instructions
**Read `implementation_plan_playground_feature_1.md` → Task 05 section.** Build fullscreen glassmorphic preset gallery that appears on first load. Scenario cards with titles, descriptions, icons. Selecting a preset loads its Drawflow node graph JSON. Must include "Blank Canvas" option. Export `showPresetGallery(onSelect)`.

## Verification_Strategy
```
Test_Type: manual_steps
Acceptance_Criteria:
  - "Gallery appears as fullscreen overlay on playground load"
  - "Cards show scenario titles and descriptions"
  - "Selecting a card fires onSelect callback with preset data"
  - "Gallery dismisses on selection or close"
  - "Glassmorphic styling matches design system"
```
