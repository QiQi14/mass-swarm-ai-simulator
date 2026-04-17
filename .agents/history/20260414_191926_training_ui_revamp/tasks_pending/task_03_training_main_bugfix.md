---
Task_ID: task_03
Title: "JS: Channel Bug Fix + Icon Wiring + Collapsed Strip Redesign"
Execution_Phase: 1
Model_Tier: standard
Status: PENDING
Live_System_Impact: safe
---

## Target_Files
- `debug-visualizer/src/training-main.js`

## Dependencies
- icons.js must exist (Task 02 creates it — run after or concurrently)

## Context_Bindings
- context/project/conventions.md

## Strict_Instructions

### Bug Fix — _updateChannelAvailability
Current code unchecks toggles when hasData() briefly returns false on episode reset.
Fix: Remove the `input.checked = false` block from _updateChannelAvailability.
Only add/remove `channel-row--disabled` CSS class. The `change` event handler already
guards against enabling disabled channels.
Always call refreshActiveStrip() at end.

### Icon Wiring
Import `icon` from `./components/icons.js`.
Replace all emoji icon strings:
- Channel card header: `📡` → icon('radio')
- Overlays card header: `👁` → icon('eye')
- Collapse button: `◀/▶` → icon('chevron-left') / icon('chevron-right', 12)
- Minimize button: `—` → icon('minimize')
- Expand button: `□` → icon('maximize')
- Mobile sheet headers: replace emoji

renderOverlayCards(): header.innerHTML uses panel.icon field as raw HTML (already works).

### Collapsed Strip Redesign
refreshActiveStrip(): when active.length > 0, prepend a count badge:
`<span class="channel-strip-count">${active.length} active</span>`
followed by dot spans. When 0 active, show "No active channels".

### File Size Note
// NOTE: This file exceeds 300 lines but is not split because it is a
// bootstrap orchestration file — all items are tightly coupled init sequences and DOM wiring.
Add this comment at line 1.

## Verification_Strategy
  Test_Type: manual_steps
  Manual_Steps:
    - Episode reset: active channel toggles remain checked after reset
    - Collapsed strip shows count badge "N active" + colored dots
    - All headers use SVG icons (no emoji)
