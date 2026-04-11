# Task 06: Training Visualizer Metrics Overlay

**Task_ID:** `task_06_training_visualizer`
**Feature:** Training Visualizer Upgrade
**Execution_Phase:** 1 (Parallel — no Rust dependencies)
**Model_Tier:** `standard`

## Target_Files
- `debug-visualizer/js/training-overlay.js` [NEW]
- `debug-visualizer/css/training-overlay.css` [NEW]
- `debug-visualizer/index.html` [MODIFY]

## Dependencies
None (uses existing HTTP server + CSV files)

## Context_Bindings
- `context/conventions`

## Background

The Rust Micro-Core already serves static files from `debug-visualizer/` via its HTTP server. The Python training pipeline writes `episode_log.csv` to a `run_latest/` symlink directory. The visualizer can poll this CSV via HTTP to display training metrics without any Rust or Python changes.

**Data source:** `run_latest/episode_log.csv` with columns:
```
episode,stage,steps,win,reward,brain_survivors,enemy_survivors,win_rate_rolling
```

**CRITICAL PERFORMANCE NOTE:** At >3000 TPS, the CSV grows to thousands of lines per minute. The overlay MUST use a **tail-read strategy**: fetch only the last 4KB via HTTP `Range` header, cache previously parsed data, and skip truncated first lines.

## Strict_Instructions

### 1. Create `debug-visualizer/js/training-overlay.js`

This module provides a floating overlay panel that:
- Polls `run_latest/episode_log.csv` every 5 seconds
- Uses HTTP `Range: bytes=-4096` to only fetch the last 4KB (~80 episodes)
- Handles partial responses (HTTP 206) by skipping the truncated first line
- Parses the CSV tail into an array of episode records
- Renders these real-time metrics:
  - **Episode counter** (total episodes from `episode` column of last row)
  - **Current stage** (from `stage` column of last row)
  - **Rolling win rate** (from `win_rate_rolling` column, displayed as percentage bar with color gradient)
  - **Last 20 episode rewards** (simple sparkline using a `<canvas>` mini-chart)
  - **Stage history** (compact list showing when stage transitions occurred)
- Gracefully handles network errors (CSV not found = "No active training run")
- Toggle-able via keyboard shortcut (`T` key) or a small toggle button

**IMPORTANT:** Use `<script type="module">` and ES module `export` syntax. This is required for future Vite migration. Do NOT use global scripts or IIFEs.

**Architecture:**

```javascript
// training-overlay.js

const POLL_INTERVAL_MS = 5000;
const CSV_URL = '/run_latest/episode_log.csv';
const TAIL_BYTES = 4096;

let overlayVisible = false;
let pollTimer = null;
let cachedEpisodeCount = 0;

export function initTrainingOverlay() {
    createOverlayDOM();
    startPolling();
    document.addEventListener('keydown', (e) => {
        if (e.key === 't' || e.key === 'T') toggleOverlay();
    });
}

function createOverlayDOM() {
    // Create floating panel with id="training-overlay"
    // Position: bottom-right corner, semi-transparent dark glass background
    // Contains: #training-episodes, #training-stage, #training-winrate-bar,
    //           #training-sparkline (canvas 280x60), #training-status
    // Include a small "Training" header with a close/minimize button
}

async function fetchAndUpdate() {
    try {
        const resp = await fetch(CSV_URL, {
            headers: { 'Range': `bytes=-${TAIL_BYTES}` }
        });
        if (!resp.ok && resp.status !== 206) {
            showStatus('No active training run');
            return;
        }
        const text = await resp.text();
        const isPartial = resp.status === 206;
        const records = parseCSVTail(text, isPartial);
        if (records.length > 0) updateMetrics(records);
    } catch (e) {
        showStatus('Training data unavailable');
    }
}

function parseCSVTail(text, isPartial) {
    const lines = text.trim().split('\n');
    // If partial (206), first line is likely truncated — skip it
    const startIdx = isPartial ? 1 : 1; // Skip header or truncated line
    // Parse remaining lines: episode,stage,steps,win,reward,...,win_rate_rolling
    // Return array of { episode, stage, steps, win, reward, winRate }
}

function updateMetrics(records) {
    const latest = records[records.length - 1];
    // Update #training-episodes with latest.episode
    // Update #training-stage with latest.stage
    // Update win rate bar width + color (green >70%, yellow 40-70%, red <40%)
    // Draw sparkline of last 20 rewards on canvas
}

function drawSparkline(canvas, values) {
    // Simple line chart: normalize values to canvas height
    // Use gradient stroke (red = negative, green = positive)
    // No axes, no labels — just the line
}
```

### 2. Create `debug-visualizer/css/training-overlay.css`

```css
#training-overlay {
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 320px;
    background: rgba(15, 15, 25, 0.92);
    border: 1px solid rgba(100, 180, 255, 0.3);
    border-radius: 12px;
    padding: 16px;
    color: #e0e8f0;
    font-family: 'JetBrains Mono', 'Menlo', monospace;
    font-size: 13px;
    z-index: 1000;
    backdrop-filter: blur(8px);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    transition: opacity 0.3s ease, transform 0.3s ease;
}

#training-overlay.hidden {
    opacity: 0;
    transform: translateY(20px);
    pointer-events: none;
}

/* Header */
.training-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    border-bottom: 1px solid rgba(100, 180, 255, 0.15);
    padding-bottom: 8px;
}

.training-header h3 {
    margin: 0;
    font-size: 14px;
    color: rgba(100, 180, 255, 0.9);
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* Metric rows */
.training-metric {
    display: flex;
    justify-content: space-between;
    margin-bottom: 6px;
}

.training-metric .label {
    color: rgba(200, 210, 220, 0.6);
}

.training-metric .value {
    font-weight: bold;
    color: #e0e8f0;
}

/* Win rate bar */
.winrate-bar {
    height: 6px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 3px;
    margin: 8px 0;
    overflow: hidden;
}

.winrate-bar-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.5s ease, background-color 0.5s ease;
}

/* Sparkline canvas */
#training-sparkline {
    width: 100%;
    height: 60px;
    border-radius: 6px;
    background: rgba(0, 0, 0, 0.2);
    margin-top: 8px;
}

/* Status message */
.training-status {
    text-align: center;
    color: rgba(200, 210, 220, 0.4);
    font-style: italic;
    padding: 20px 0;
}
```

### 3. Modify `debug-visualizer/index.html`

First, **check the existing structure** of index.html. Then:

- Add CSS link in `<head>`:
  ```html
  <link rel="stylesheet" href="css/training-overlay.css">
  ```

- Add module script at the bottom of `<body>`:
  ```html
  <script type="module">
      import { initTrainingOverlay } from './js/training-overlay.js';
      initTrainingOverlay();
  </script>
  ```

**IMPORTANT:** If index.html currently uses non-module scripts, the `type="module"` script won't conflict — modules are deferred by default and have their own scope. This is safe to add alongside existing `<script>` tags.

## Anti-Patterns
- ❌ Do NOT add WebSocket channels to Rust for training data — use HTTP polling only
- ❌ Do NOT fetch the full CSV every poll — use Range header for tail-read
- ❌ Do NOT block the main render loop — all fetch operations are async
- ❌ Do NOT use external charting libraries — vanilla JS only (no npm deps)
- ❌ Do NOT use global `<script>` — use `type="module"` for future Vite compat

## Verification_Strategy

```yaml
Test_Type: manual_steps
Test_Stack: browser (vanilla JS)
Acceptance_Criteria:
  - "Overlay panel appears when pressing 'T' key"
  - "Panel shows 'No active training run' when CSV not available"
  - "When run_latest/episode_log.csv exists, panel shows episode count, stage, and win rate"
  - "Sparkline canvas renders last 20 episode rewards"
  - "Panel auto-updates every 5 seconds without page refresh"
  - "Overlay does not interfere with existing canvas rendering or controls"
  - "Uses type='module' for Vite-ready ES modules"
Manual_Steps:
  - "Start the micro-core: cd micro-core && cargo run"
  - "Open http://localhost:8080 in browser"
  - "Press 'T' to toggle overlay"
  - "Verify 'No active training run' message"
  - "Start training: cd macro-brain && ./train.sh tactical_curriculum"
  - "Wait 10 seconds, verify overlay shows live episode data"
```
