---
Task_ID: task_02
Title: "JS: SVG Icon System + Panel Icon Updates"
Execution_Phase: 1
Model_Tier: standard
Status: PENDING
Live_System_Impact: safe
---

## Target_Files
- `debug-visualizer/src/components/icons.js` [NEW]
- `debug-visualizer/src/panels/training/ml-brain.js`
- `debug-visualizer/src/panels/training/stage-info.js`
- `debug-visualizer/src/panels/training/dashboard.js`

## Dependencies
- None (Phase 1, but icons.js must be created before other panel modifications)

## Context_Bindings
- context/project/conventions.md
- skills/frontend-ux-ui/SKILL.md

## Strict_Instructions

### icons.js [NEW]
Export `icon(name, size=14)` → string (raw SVG HTML).
Required icon names: brain, target, chart-line, eye, radio, zap, chevron-right, chevron-left, minimize, maximize, trophy, layers.
Use Lucide SVG path data. No DOM manipulation — pure string function.

### ml-brain.js
- Replace `icon: '🧠'` with `icon: icon('brain')`
- Replace emoji status indicators with plain text + CSS class for color
- Remove emoji from directive summaries

### stage-info.js
- Replace `icon: '🎯'` with `icon: icon('target')`
- Action badges in _updateCardContent() → `.action-chip` with icon('zap',12) prefix
- Modal graduation box → structured sub-elements (icon, label, value)
- Modal actions section → also use `.action-chip`
- Stage toast → remove ⬆ emoji, use plain "STAGE X" text

### dashboard.js
- Replace `icon: '📈'` with `icon: icon('chart-line')`

## Verification_Strategy
  Test_Type: manual_steps
  Manual_Steps:
    - All card headers show SVG icons (no emoji) — verify in DevTools Elements
    - Action chips show zap icon + left cyan border
    - Modal graduation box shows structured trophy/layers icons
