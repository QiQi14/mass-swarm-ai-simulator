# Task 05: Integration Smoke Test

Task_ID: task_05_integration_smoke_test
Execution_Phase: C
Model_Tier: standard

## Target_Files
- None (verification-only task)

## Dependencies
- Task 01 (HTML + CSS layout)
- Task 03 (Rust WS bidirectional)
- Task 04 (JS visualizer)

## Context_Bindings
- context/infrastructure

## Strict_Instructions

This is a **verification-only task**. Do NOT create or modify any source files.

### Test Procedure

#### Gate 1: Rust Build Verification
```bash
cd micro-core && cargo check
cd micro-core && cargo clippy
cd micro-core && cargo test
```
All must pass with zero errors and zero warnings.

#### Gate 2: Static File Verification
Verify these files exist and are non-empty:
- `debug-visualizer/index.html`
- `debug-visualizer/style.css`
- `debug-visualizer/visualizer.js`

Verify all mandatory DOM IDs exist in `index.html`:
```
sim-canvas, stat-tps, stat-ping, stat-ai-latency, stat-entities,
stat-swarm, stat-defender, stat-tick, play-pause-btn, step-btn,
step-count-input, toggle-grid, toggle-velocity, toggle-fog,
status-dot, status-text
```

#### Gate 3: Visual Rendering Test
1. Start Micro-Core: `cd micro-core && cargo run`
2. Open `debug-visualizer/index.html` in a browser
3. Verify:
   - Connection status shows "Connected"
   - Canvas renders colored dots (two distinct colors for swarm vs defender)
   - Dots move each tick
   - Telemetry panel shows: TPS updating, entity count = 100, swarm/defender breakdown

#### Gate 4: Pan/Zoom Test
1. Scroll wheel on canvas → verify zoom in/out
2. Click+drag on canvas → verify pan
3. Double-click → verify view resets

#### Gate 5: Layer Toggle Test
1. Toggle grid checkbox → verify grid overlay appears/disappears on canvas
2. Enable velocity vectors → verify direction lines appear on entities
3. Fog toggle → verify some visual change (even if minimal placeholder)

#### Gate 6: Command Round-Trip Test
1. Click Play/Pause → verify:
   - Rust logs: `[WS Command] Simulation paused/resumed`
   - Entities stop/resume movement
2. Set step count to 5, click Step → verify:
   - Rust logs: `[WS Command] Stepping 5 tick(s)`
   - Exactly 5 ticks advance, then auto-pause
3. Click on canvas → verify:
   - New entities spawn at the clicked position
   - Rust logs: `[WS Command] Spawned ... entities`
   - Entity count increases in telemetry

#### Gate 7: Reconnection Test
1. Stop Micro-Core (Ctrl+C)
2. Verify: connection status changes to disconnected
3. Restart Micro-Core
4. Verify: auto-reconnect, entity buffer cleared, rendering resumes

#### Gate 8: Error-Free Operation
- Open browser DevTools Console
- Verify: zero JavaScript errors during all tests
- Verify: no Rust panics

### Acceptance Criteria
- ALL 8 gates pass
- Zero console errors (JS and Rust)
- Bidirectional commands work: toggle_sim, step, spawn (click), kill_all
- Velocity vectors render correctly when enabled
- Step mode auto-pauses after N ticks

## Verification_Strategy
  Test_Type: manual_steps + integration
  Acceptance_Criteria:
    - "All 8 verification gates pass"
    - "Zero JavaScript console errors"
    - "Zero Rust panics"
    - "Bidirectional WS commands work end-to-end"
  Manual_Steps:
    - "Follow gates 1-8 in sequence"
    - "Document results for each gate"
