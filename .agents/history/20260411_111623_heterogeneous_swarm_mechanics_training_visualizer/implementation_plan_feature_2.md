# Feature 2: Training Visualizer Metrics Overlay

> Detail file for Task T06.

---

## Task 06: Training Visualizer Metrics Overlay

**Task_ID:** `task_06_training_visualizer`
**Execution_Phase:** 1 (Parallel — no Rust dependencies)
**Model_Tier:** `standard`
**Target_Files:**
- `debug-visualizer/js/training-overlay.js` [NEW]
- `debug-visualizer/css/training-overlay.css` [NEW]
- `debug-visualizer/index.html` [MODIFY]

**Context_Bindings:**
- `context/conventions`

**Dependencies:** None (uses existing HTTP server + CSV files)

### Background

The Rust Micro-Core already serves static files from `debug-visualizer/` via its HTTP server. The Python training pipeline writes `episode_log.csv` to a `run_latest/` symlink directory. The visualizer can poll this CSV via HTTP to display training metrics without any Rust or Python changes.

**Data source:** `run_latest/episode_log.csv` with columns:
```
episode,stage,steps,win,reward,brain_survivors,enemy_survivors,win_rate_rolling
```

### Strict Instructions

1. **Create `debug-visualizer/js/training-overlay.js`:**

   This module provides a floating overlay panel that:
   - Polls `run_latest/episode_log.csv` every 5 seconds via `fetch()`
   - Parses the CSV into an array of episode records
   - Renders these real-time metrics:
     - **Episode counter** (total episodes completed)
     - **Current stage** (from last CSV row)
     - **Rolling win rate** (from `win_rate_rolling` column, displayed as percentage bar)
     - **Last 20 episode rewards** (simple sparkline using canvas mini-chart)
     - **Stage history** (compact list of stage transitions with timestamps)
   - Gracefully handles network errors (CSV not found = training not running)
   - Toggle-able via a keyboard shortcut (`T` key) or button

   **Architecture (with tail-read optimization for high-TPS training):**

   > [!IMPORTANT]
   > At >3000 TPS, the CSV grows to thousands of lines per minute. The overlay
   > MUST use a tail-read strategy: fetch only the **last 4KB** via HTTP `Range`
   > header, cache the total episode count, and only parse new lines.

   ```javascript
   // training-overlay.js
   
   const POLL_INTERVAL_MS = 5000;
   const CSV_URL = '/run_latest/episode_log.csv';
   const TAIL_BYTES = 4096;  // Only fetch last 4KB (~80 episodes)
   
   let overlayVisible = false;
   let pollTimer = null;
   let cachedEpisodeCount = 0;  // Track total without re-parsing full file
   
   export function initTrainingOverlay() {
       createOverlayDOM();
       startPolling();
       document.addEventListener('keydown', (e) => {
           if (e.key === 't' || e.key === 'T') toggleOverlay();
       });
   }
   
   function createOverlayDOM() {
       // Create floating panel with id="training-overlay"
       // Position: bottom-right corner, semi-transparent dark background
       // Contains: #training-episodes, #training-stage, #training-winrate,
       //           #training-sparkline (canvas), #training-status
   }
   
   async function fetchAndUpdate() {
       try {
           // Tail-read: only fetch last 4KB to avoid downloading entire CSV
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
           updateMetrics(records);
       } catch (e) {
           showStatus('Training data unavailable');
       }
   }
   
   function parseCSVTail(text, isPartial) {
       // If partial (206), the first line is likely truncated — skip it
       // Parse remaining lines into episode records
       // Use Content-Range header to estimate total episode count
       // Return array of { episode, stage, steps, win, reward, winRate }
   }
   
   function updateMetrics(records) {
       // Update DOM elements with latest data
       // Draw sparkline on #training-sparkline canvas (last 20 records)
   }
   ```

2. **Create `debug-visualizer/css/training-overlay.css`:**
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
   
   /* Win rate bar, sparkline styles, etc. */
   ```

3. **Modify `debug-visualizer/index.html`:**
   - Add CSS link: `<link rel="stylesheet" href="css/training-overlay.css">`
   - Add script import at bottom: `<script type="module" src="js/training-overlay.js"></script>`
   - OR if not using modules, add `<script>` tag and call `initTrainingOverlay()` after page load

   **IMPORTANT:** Check the existing index.html structure first. It may or may not use ES modules. Match the existing pattern.

### Anti-Patterns

- ❌ Do NOT add WebSocket channels to Rust for training data — use HTTP polling
- ❌ Do NOT parse the CSV line-by-line on every poll — cache and only parse new lines
- ❌ Do NOT block the main render loop — all fetch operations are async
- ❌ Do NOT use external charting libraries — keep the visualizer dependency-free (vanilla JS)

### Verification_Strategy

```yaml
Test_Type: manual_steps
Test_Stack: browser (vanilla JS)
Acceptance_Criteria:
  - "Overlay panel appears when pressing 'T' key"
  - "Panel shows 'No active training run' when no CSV is available"
  - "When run_latest/episode_log.csv exists, panel shows episode count, stage, and win rate"
  - "Sparkline canvas renders last 20 episode rewards"
  - "Panel auto-updates every 5 seconds without page refresh"
  - "Overlay does not interfere with existing canvas rendering or controls"
Manual_Steps:
  - "Start the micro-core: cd micro-core && cargo run"
  - "Open http://localhost:8080 in browser"
  - "Press 'T' to toggle overlay"
  - "Verify 'No active training run' message"
  - "Start training: cd macro-brain && ./train.sh tactical_curriculum"
  - "Wait 10 seconds, verify overlay shows live episode data"
```
