# Task P15: Tactical Canvas Overlay

- **Task_ID:** `P15_tactical_overlay`
- **Execution_Phase:** 4 (depends on P13)
- **Model_Tier:** `standard`
- **Live_System_Impact:** `safe`

## Target_Files
- `debug-visualizer/src/draw/tactical-overlay.js` — NEW
- `debug-visualizer/src/draw/entities.js` — MODIFY (integrate overlay call)
- `debug-visualizer/src/styles/tactical.css` — NEW

## Dependencies
- P13 (squad manager provides squad data)

## Context_Bindings
- `implementation_plan_playground_feature_4.md` — Task 15 section (full drawing algorithms)
- `.agents/skills/frontend-ux-ui/SKILL.md`

## Strict_Instructions
**Read `implementation_plan_playground_feature_4.md` → Task 15 section.** Create tactical-overlay.js with `drawTacticalOverlay()` called from render loop after entity drawing. Implements: selection box rubber-band, selected entity highlight rings, squad banners at centroid, pulsing order arrows, rally point animations. Integrate call in entities.js. Performance: batched paths, culling, convex hull fallback at >500 selected.

## Verification_Strategy
```
Test_Type: manual_steps
Acceptance_Criteria:
  - "Green selection box during drag"
  - "Highlight rings on selected entities"
  - "Squad banners float above centroids"
  - "Pulsing order arrows from squad to target"
  - "No FPS drop with 5 squads and 10K entities"
```
