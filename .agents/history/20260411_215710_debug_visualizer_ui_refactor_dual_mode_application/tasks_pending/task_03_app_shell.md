# Task 03: App Shell & Mode Router

## Task_ID
task_03_app_shell

## Execution_Phase
Phase 2 (Depends on T01, T02)

## Model_Tier
`advanced`

## Target_Files
- `debug-visualizer/index.html` — **REWRITE**
- `debug-visualizer/src/main.js` — **REWRITE**
- `debug-visualizer/src/router.js` — **NEW**
- `debug-visualizer/src/components/tabs.js` — **NEW**
- `debug-visualizer/src/components/accordion.js` — **NEW**
- `debug-visualizer/src/components/sparkline.js` — **NEW**
- `debug-visualizer/src/components/toast.js` — **NEW**

## Dependencies
T01 (file structure exists), T02 (CSS classes exist)

## Context_Bindings
- `context/conventions` (JS naming, DOM IDs)
- `context/architecture` (data flow: WS → state → draw)
- `skills/frontend-ux-ui` (design aesthetic — MUST READ)

## Strict_Instructions
See `implementation_plan_feature_2.md` → Task 03 for exhaustive instructions.

Key components:
1. Rewrite `index.html` — minimal shell, all content injected via JS. Use DM Sans + IBM Plex Mono as HTML font fallback.
2. Create `router.js` — Hash-based mode switching (#training / #playground).
3. Create `tabs.js` — Tab bar with animated indicator (spring easing).
4. Create `accordion.js` — Collapsible panels with mode filtering.
5. Create `sparkline.js` — Canvas-based reusable chart (electric cyan default).
6. Create `toast.js` — Notification system extracted from websocket.js.
7. Rewrite `main.js` — Import CSS, init router, render tabs, wire mode changes.

## Verification_Strategy
```yaml
Test_Type: manual_steps
Test_Stack: Browser + Vite dev server
Acceptance_Criteria:
  - "Tab bar renders with Training and Playground tabs"
  - "Clicking tabs switches URL hash and fires modechange event"
  - "Panel scroll area is empty but renders (panels come in T04/T05)"
  - "Canvas renders entities correctly"
  - "WS connects and status badge updates"
  - "Toast notifications still work"
Manual_Steps:
  - "npm run dev → verify tab bar appears below SwarmControl header"
  - "Click Training tab → hash changes to #training"
  - "Click Playground tab → hash changes to #playground"
  - "Verify canvas still renders, WS connects"
```

## Live_System_Impact
`safe`
