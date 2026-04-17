# Changelog: task_03_training_main_bugfix

## Task Summary
Bug fix for channel availability reset, icon wiring to icon() system, and collapsed strip redesign.

## Files Modified
- `debug-visualizer/src/training-main.js`

## Changes Made

### Rationale Comment
Added file-size rationale at top of file (>300 lines): bootstrap orchestration — all items tightly coupled.

### Icon Import + Wiring
- Added `import { icon } from './components/icons.js'`
- `renderOverlayCards()`: renamed local `icon` var → `iconHtml`, wraps panel icon in `<span class="overlay-card__header-icon">` instead of bare span
- Channel card header: `📡` → `icon('radio')`
- Overlays card header: `👁` → `icon('eye')`
- Collapse button: `◀/▶` text → `icon('chevron-left', 11)` / `icon('chevron-right', 11)` via `innerHTML`
- Minimize button initial HTML: `<span>—</span>` → `icon('minus', 16)`
- Minimize/maximize toggle: `<span>—/□</span>` → `icon('minus', 16)` / `icon('square', 16)`

### Bug Fix: _updateChannelAvailability
**Root cause:** The function called `input.checked = false` whenever `t.hasData()` returned false. At every episode reset, data sources briefly return false before the new episode's data arrives, causing all active channel toggles to flicker to unchecked.

**Fix:** Removed the `input.checked = false` block entirely from `_updateChannelAvailability`. The function now ONLY adds/removes the `channel-row--disabled` CSS class (which sets `pointer-events: none`). This prevents new activations while preserving the user's existing checked state.

The `change` event handler still guards correctly: `if (!t.hasData()) { e.target.checked = false; }` — so attempting to enable a disabled channel is still blocked.

Also added `refreshActiveStrip()` call at the end of `_updateChannelAvailability` to keep collapsed strip in sync.

### Collapsed Strip Redesign
`refreshActiveStrip()` updated:
- Now queries active channels via `document.getElementById(t.id)` directly (simpler)
- When active.length > 0: prepends `<span class="channel-strip-count">N active</span>` badge before the dots
- No other logic changed

## Human Interventions
None — implemented per spec.
