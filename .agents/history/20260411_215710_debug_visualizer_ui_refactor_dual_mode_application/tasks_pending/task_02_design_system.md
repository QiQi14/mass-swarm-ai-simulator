# Task 02: Design System & CSS Rewrite

## Task_ID
task_02_design_system

## Execution_Phase
Phase 1 (Parallel — no dependencies)

## Model_Tier
`advanced`

## Target_Files
- `debug-visualizer/src/styles/variables.css` — **REWRITE**
- `debug-visualizer/src/styles/reset.css` — **NEW**
- `debug-visualizer/src/styles/layout.css` — **REWRITE**
- `debug-visualizer/src/styles/panels.css` — **REWRITE**
- `debug-visualizer/src/styles/controls.css` — MOVE + restyle
- `debug-visualizer/src/styles/canvas.css` — MOVE
- `debug-visualizer/src/styles/animations.css` — **REWRITE**
- `debug-visualizer/src/styles/training.css` — **NEW**

## Dependencies
None (parallel with T01, but targets the same file structure).

## Context_Bindings
- `context/conventions` (CSS variables naming)
- `skills/frontend-ux-ui` (design aesthetic guidelines — **MUST READ BEFORE STARTING**)

## Strict_Instructions
See `implementation_plan_feature_1.md` → Task 02 for exhaustive step-by-step instructions.

**CRITICAL: Read `skills/frontend-ux-ui` SKILL.md FIRST.**

**Aesthetic Direction: Tactical Command Center**
- Typography: Geist + Geist Mono (fallback: DM Sans + IBM Plex Mono). NEVER Inter/Roboto.
- Palette: Deep void black (#050608) + electric cyan (#06d6a0) dominant accent.
- Surfaces: Noise texture overlay, scanline effects, grid-line patterns.
- Motion: Staggered panel cascade, radar-pulse status, data-flash on update.
- Borders: Accent-colored glow, NOT plain solid lines.

## Verification_Strategy
```yaml
Test_Type: manual_steps
Test_Stack: Browser visual inspection
Acceptance_Criteria:
  - "All CSS files load without console errors"
  - "Typography is clearly NOT Inter/Roboto — Geist or fallback renders"
  - "Electric cyan accent (#06d6a0) visible on borders, active states, data values"
  - "Sidebar has atmospheric depth (noise texture, not flat solid)"
  - "Panel accordion transitions are smooth, staggered"
  - "The design feels like a tactical command center, NOT a generic SaaS dashboard"
Manual_Steps:
  - "Load page after T01 + T02 merged"
  - "Verify font rendering (Geist or DM Sans, NOT Inter)"
  - "Verify accent color (#06d6a0) on active elements"
  - "Verify noise texture overlay is visible but subtle"
  - "Check stat values use mono font in accent color"
```

## Live_System_Impact
`safe`
