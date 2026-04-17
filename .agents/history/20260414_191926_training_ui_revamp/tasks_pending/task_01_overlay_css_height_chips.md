---
Task_ID: task_01
Title: "CSS: Fix Height Mismatch + Action Chip + Strip Styles"
Execution_Phase: 1
Model_Tier: standard
Status: PENDING
Live_System_Impact: safe
---

## Target_Files
- `debug-visualizer/src/styles/overlay.css`

## Dependencies
- None (Phase 1)

## Context_Bindings
- context/project/conventions.md
- skills/frontend-ux-ui/SKILL.md

## Strict_Instructions

### A — Linked Row Height Unification
Change `.overlay-linked-row` `align-items` from `flex-end` to `stretch`.
Add `min-height: 148px` to `#overlay-card-ml-brain` and `#overlay-card-stage-info`.

### B — New `.action-chip` class
Left cyan border (3px), bg rgba(255,255,255,0.04), border rgba(255,255,255,0.08).
Has `.action-chip__icon` child class (color: accent-primary).
Text: 11px, 700 weight, uppercase, letter-spacing 0.04em.

### C — Collapsed channel strip
`.channel-active-strip` min-height → 36px.
New `.channel-strip-count` class: mono 10px, accent-primary color, green tinted bg badge.

### D — Stage modal section title
New `.stage-modal__section-title` class: 11px, tertiary color, uppercase, letter-spacing 0.1em, bottom border.
New `.grad-metric__icon`, `.grad-metric__label`, `.grad-metric__value` sub-classes.
Grad metrics use 2-column grid layout.

### E — SVG icon alignment in headers
New `.overlay-card__header-icon` class: display flex, align-items center, accent-primary color at 0.8 opacity.

## Verification_Strategy
  Test_Type: manual_steps
  Manual_Steps:
    - ML Brain Status and Stage Info cards must share identical card height
    - Collapsed channel strip shows minimum 36px height
    - Action chips show left cyan border (visually distinct from toggle pills)
