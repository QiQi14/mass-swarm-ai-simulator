# Changelog: task_01_overlay_css_height_chips

## Task Summary
CSS changes to overlay.css for height unification, action-chip styles, status dots, and modal improvements.

## Files Modified
- `debug-visualizer/src/styles/overlay.css`

## Changes Made

### A — Linked Row Height Unification
- Changed `.overlay-linked-row` `align-items` from `flex-end` → `stretch`
- Added `#overlay-card-ml-brain, #overlay-card-stage-info { min-height: 148px }` — ensures the two side-by-side cards share identical height regardless of content

### B — SVG Icon Alignment
- Added `.overlay-card__header-icon` class: flex, accent-primary color, 0.75 opacity — proper sizing for inline SVGs in card headers
- Added `.overlay-card__header-icon svg { display: block }` — prevents baseline alignment issues

### C — Inline Status Dots
- Added `.status-dot-inline` + `.status-dot-inline--ok/err/warn/wait` variants — replaces emoji status indicators in panels with clean CSS circle dots with glow effects

### D — Channel Strip
- Increased `.channel-active-strip` `min-height` from 28px → 36px
- Added `.channel-strip-count` class — count badge shown in collapsed state ("N active")

### E — Action Chip (NEW)
- Added `.action-chip` class: left 3px accent-border, semi-transparent bg, uppercase, 700 weight — visually distinct from toggle pills
- Added `.action-chip__icon` sub-class for the icon prefix
- `.stage-modal__badge` kept as deprecated alias with reduced emphasis styling

### F — Stage Modal Section Title
- Added `.stage-modal__section-title` — 11px, tertiary color, uppercase, letters-spaced, bottom border divider
- Added `.stage-details-btn` — ghost button for "Curriculum Details" in stage card

### G — Graduation Box Restructure
- `.grad-metrics` changed from flex-row to 2-column grid
- `.stage-modal__grad-box h3` reduced from 14px/primary to 11px/tertiary/uppercase (section label style)
- Added `.grad-metric__icon`, `.grad-metric__label`, `.grad-metric__value` sub-elements for stacked metric layout

## Human Interventions
None — implemented per spec.
