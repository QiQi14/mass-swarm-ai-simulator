# Feature 2: App Shell, Panels & Integration (Tasks 03–06)

## Task 03: App Shell & Mode Router

### Overview
Build the core application shell: rewrite `index.html` with the new layout structure (tab bar + scrollable panel area), implement the hash-based mode router, and create reusable UI components (tabs, accordion, sparkline, toast).

### Model Tier: `advanced`

### Target Files
- `debug-visualizer/index.html` — **REWRITE**
- `debug-visualizer/src/main.js` — **REWRITE**
- `debug-visualizer/src/router.js` — **NEW**
- `debug-visualizer/src/components/tabs.js` — **NEW**
- `debug-visualizer/src/components/accordion.js` — **NEW**
- `debug-visualizer/src/components/sparkline.js` — **NEW**
- `debug-visualizer/src/components/toast.js` — **NEW**

### Dependencies
T01 (file structure exists), T02 (CSS classes exist)

### Context_Bindings
- `context/conventions` (JS naming, DOM IDs)
- `context/architecture` (data flow: WS → state → draw)
- `skills/frontend-ux-ui` (design aesthetic — MUST READ)

### Strict Instructions

1. **Rewrite `index.html`:**

   The new shell is minimal. All panel content is injected via JS. Structure:

   ```html
   <!DOCTYPE html>
   <html lang="en">
   <head>
       <meta charset="UTF-8">
       <meta name="viewport" content="width=device-width, initial-scale=1.0">
       <title>SwarmControl — Debug Visualizer</title>
       <meta name="description" content="Real-time debug visualizer for the Mass-Swarm AI Simulator">
       <link rel="preconnect" href="https://fonts.googleapis.com">
       <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
       <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
       <!-- Geist preferred via @fontsource in CSS; DM Sans + IBM Plex Mono as HTML fallback -->
   </head>
   <body>
       <div class="app-container" id="app">
           <!-- Canvas Area -->
           <main class="canvas-area" id="canvas-area">
               <canvas id="canvas-bg"></canvas>
               <canvas id="canvas-entities"></canvas>
               <div class="connection-badge" id="connection-badge">
                   <div class="status-dot" id="status-dot"></div>
                   <span id="status-text">Connecting…</span>
               </div>
               <div class="canvas-hint" id="canvas-hint">
                   Pan: drag · Zoom: scroll · Double-click: reset view
               </div>
           </main>

           <!-- Sidebar -->
           <aside class="sidebar" id="sidebar">
               <header class="sidebar-header">
                   <div>
                       <h1>Swarm<span class="accent">Control</span></h1>
                       <span class="version-badge">v0.2.0</span>
                   </div>
               </header>
               <nav class="tab-bar" id="tab-bar">
                   <!-- Tabs injected by tabs.js -->
               </nav>
               <div class="panel-scroll" id="panel-scroll">
                   <!-- Panels injected by panel registry -->
               </div>
           </aside>
       </div>

       <script type="module" src="/src/main.js"></script>
   </body>
   </html>
   ```

   **Key changes from current:**
   - All CSS is imported via JS (`import './styles/variables.css'` etc.) — Vite handles injection.
   - No inline panel HTML — all panels are JS-rendered.
   - No modal HTML — modals created dynamically in JS.
   - Tab bar added between sidebar header and panel area.
   - Canvas IDs preserved (`canvas-bg`, `canvas-entities`).

2. **Create `src/router.js`:**

   ```javascript
   // ─── Hash-Based Mode Router ─────────────────────────────────
   
   export const MODES = Object.freeze({
     TRAINING: 'training',
     PLAYGROUND: 'playground',
   });
   
   const DEFAULT_MODE = MODES.PLAYGROUND;
   let currentMode = null;
   const listeners = [];
   
   export function getCurrentMode() {
     return currentMode;
   }
   
   export function setMode(mode) {
     if (!Object.values(MODES).includes(mode)) return;
     if (mode === currentMode) return;
     const oldMode = currentMode;
     currentMode = mode;
     window.location.hash = mode;
     listeners.forEach(cb => cb(mode, oldMode));
   }
   
   export function onModeChange(callback) {
     listeners.push(callback);
   }
   
   export function initRouter() {
     const hash = window.location.hash.slice(1);
     currentMode = Object.values(MODES).includes(hash) ? hash : DEFAULT_MODE;
     window.addEventListener('hashchange', () => {
       const newHash = window.location.hash.slice(1);
       if (Object.values(MODES).includes(newHash) && newHash !== currentMode) {
         setMode(newHash);
       }
     });
   }
   ```

3. **Create `src/components/tabs.js`:**

   ```javascript
   // ─── Tab Bar Component ───────────────────────────────────────
   import { MODES, getCurrentMode, setMode } from '../router.js';
   
   const TAB_CONFIG = [
     { mode: MODES.TRAINING, label: '📊 Training', icon: '📊' },
     { mode: MODES.PLAYGROUND, label: '🎮 Playground', icon: '🎮' },
   ];
   
   export function renderTabs(container) {
     container.innerHTML = '';
     TAB_CONFIG.forEach(tab => {
       const btn = document.createElement('button');
       btn.className = 'tab-btn';
       btn.dataset.mode = tab.mode;
       btn.textContent = tab.label;
       btn.id = `tab-${tab.mode}`;
       if (getCurrentMode() === tab.mode) btn.classList.add('active');
       btn.onclick = () => setMode(tab.mode);
       container.appendChild(btn);
     });
     // Animated underline indicator
     const indicator = document.createElement('div');
     indicator.className = 'tab-indicator';
     indicator.id = 'tab-indicator';
     container.appendChild(indicator);
     updateIndicator();
   }
   
   export function updateTabs() {
     const mode = getCurrentMode();
     document.querySelectorAll('.tab-btn').forEach(btn => {
       btn.classList.toggle('active', btn.dataset.mode === mode);
     });
     updateIndicator();
   }
   
   function updateIndicator() {
     const active = document.querySelector('.tab-btn.active');
     const indicator = document.getElementById('tab-indicator');
     if (active && indicator) {
       indicator.style.left = `${active.offsetLeft}px`;
       indicator.style.width = `${active.offsetWidth}px`;
     }
   }
   ```

4. **Create `src/components/accordion.js`:**

   ```javascript
   // ─── Accordion Panel Component ────────────────────────────────
   
   /**
    * @param {Object} opts
    * @param {string} opts.id
    * @param {string} opts.title
    * @param {string} [opts.icon='']
    * @param {boolean} [opts.expanded=false]
    * @returns {{ element: HTMLElement, body: HTMLElement, setExpanded: (v: boolean) => void }}
    */
   export function createAccordion(opts) {
     const group = document.createElement('section');
     group.className = 'panel-group';
     group.id = `panel-${opts.id}`;
     group.dataset.panelId = opts.id;
   
     const header = document.createElement('div');
     header.className = 'panel-header';
     header.innerHTML = `
       <span class="panel-title">${opts.icon ? opts.icon + ' ' : ''}${opts.title}</span>
       <span class="panel-chevron">▸</span>
     `;
   
     const body = document.createElement('div');
     body.className = 'panel-body';
   
     const setExpanded = (expanded) => {
       if (expanded) {
         body.classList.add('expanded');
         body.classList.remove('collapsed');
         header.querySelector('.panel-chevron').textContent = '▾';
       } else {
         body.classList.remove('expanded');
         body.classList.add('collapsed');
         header.querySelector('.panel-chevron').textContent = '▸';
       }
     };
   
     header.onclick = () => {
       const isExpanded = body.classList.contains('expanded');
       setExpanded(!isExpanded);
     };
   
     setExpanded(opts.expanded ?? false);
   
     group.appendChild(header);
     group.appendChild(body);
   
     return { element: group, body, setExpanded };
   }
   
   /**
    * Show/hide panel groups based on mode.
    * @param {HTMLElement} container - The panel scroll container 
    * @param {string} mode - Current mode ('training' | 'playground')
    */
   export function applyModeFilter(container, mode) {
     container.querySelectorAll('.panel-group').forEach(panel => {
       const modes = (panel.dataset.modes || '').split(',');
       const visible = modes.includes(mode) || modes.includes('both');
       panel.style.display = visible ? '' : 'none';
       // Add entrance animation
       if (visible) {
         panel.classList.add('mode-enter');
         requestAnimationFrame(() => {
           requestAnimationFrame(() => panel.classList.remove('mode-enter'));
         });
       }
     });
   }
   ```

5. **Create `src/components/sparkline.js`:**

   ```javascript
   // ─── Reusable Sparkline Chart ──────────────────────────────────
   
   /**
    * Draw a sparkline on a canvas element.
    * @param {HTMLCanvasElement} canvas
    * @param {number[]} values
    * @param {Object} [opts]
    * @param {string} [opts.strokeColor='#60a5fa']
    * @param {string} [opts.fillColor='rgba(96, 165, 250, 0.15)']
    * @param {number} [opts.lineWidth=2]
    * @param {boolean} [opts.showZeroLine=true]
    */
   export function drawSparkline(canvas, values, opts = {}) {
     if (!values || values.length === 0) return;
     const ctx = canvas.getContext('2d');
     const { width, height } = canvas;
    const strokeColor = opts.strokeColor || '#06d6a0';
     const fillColor = opts.fillColor || 'rgba(6, 214, 160, 0.15)';
     const lineWidth = opts.lineWidth || 2;
     const showZeroLine = opts.showZeroLine ?? true;
     
     ctx.clearRect(0, 0, width, height);
     
     const padding = 2;
     const drawW = width - padding * 2;
     const drawH = height - padding * 2;
     
     const maxVal = Math.max(...values, 0.001);
     const minVal = Math.min(...values, 0);
     const range = maxVal - minVal || 1;
     const step = drawW / Math.max(values.length - 1, 1);
     
     // Line
     ctx.beginPath();
     values.forEach((v, i) => {
       const x = padding + i * step;
       const y = padding + drawH - ((v - minVal) / range) * drawH;
       i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
     });
     ctx.strokeStyle = strokeColor;
     ctx.lineWidth = lineWidth;
     ctx.lineJoin = 'round';
     ctx.stroke();
     
     // Fill
     ctx.lineTo(padding + (values.length - 1) * step, padding + drawH);
     ctx.lineTo(padding, padding + drawH);
     ctx.closePath();
     ctx.fillStyle = fillColor;
     ctx.fill();
     
     // Zero line
     if (showZeroLine && minVal < 0 && maxVal > 0) {
       const zeroY = padding + drawH - ((0 - minVal) / range) * drawH;
       ctx.beginPath();
       ctx.moveTo(padding, zeroY);
       ctx.lineTo(padding + drawW, zeroY);
       ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
       ctx.lineWidth = 1;
       ctx.setLineDash([4, 4]);
       ctx.stroke();
       ctx.setLineDash([]);
     }
   }
   ```

6. **Create `src/components/toast.js`:**

   Extract toast from `websocket.js`:

   ```javascript
   // ─── Toast Notification ────────────────────────────────────────
   
   export function showToast(message, type = 'info') {
     const toast = document.createElement('div');
     toast.className = `toast toast-${type}`;
     toast.textContent = message;
     document.body.appendChild(toast);
     requestAnimationFrame(() => toast.classList.add('show'));
     setTimeout(() => {
       toast.classList.remove('show');
       setTimeout(() => toast.remove(), 300);
     }, 2000);
   }
   ```

   Update `websocket.js` to import `showToast` from this module instead of defining it locally.

7. **Rewrite `src/main.js`:**

   The new entry point:
   - Imports all CSS files (Vite injects them)
   - Initializes the router
   - Renders tabs
   - Initializes canvases and WS connection
   - On mode change: calls `applyModeFilter()` to show/hide panels, updates tabs
   - Starts render loop (preserved from existing `main.js`)
   
   **Critical:** The render loop, canvas init, WS connection, and state reading are preserved EXACTLY from the existing `main.js`. Only the sidebar panel rendering changes.

### Anti-Patterns
- Do NOT put panel content HTML in `index.html`. All panels are JS-rendered.
- Do NOT break the canvas rendering loop or WebSocket connection during mode switches.
- Do NOT use `innerHTML` for user-provided content (XSS risk). Use `textContent` or `createElement`.

### Verification_Strategy
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

### Live_System_Impact: `safe`

---

## Task 04: Training Mode Panels

### Overview
Implement all panels that appear in Training Mode: Dashboard (enhanced from old training-overlay), ML Brain status, System Performance bars, and the shared panels (Telemetry, Inspector, Viewport Layers, Legend).

### Model Tier: `standard`

### Target Files
- `debug-visualizer/src/panels/index.js` — **NEW** (panel registry)
- `debug-visualizer/src/panels/shared/telemetry.js` — **NEW**
- `debug-visualizer/src/panels/shared/inspector.js` — **NEW**
- `debug-visualizer/src/panels/shared/viewport.js` — **NEW**
- `debug-visualizer/src/panels/shared/legend.js` — **NEW**
- `debug-visualizer/src/panels/training/dashboard.js` — **NEW**
- `debug-visualizer/src/panels/training/ml-brain.js` — **NEW**
- `debug-visualizer/src/panels/training/perf.js` — **NEW**

### Dependencies
T03 (app shell exists, accordion component exists, sparkline component exists)

### Context_Bindings
- `context/conventions` (JS naming)
- `context/ipc-protocol` (WS message types for ML brain data)
- `skills/frontend-ux-ui` (design aesthetic — stat cards, dashboard layout)

### Strict Instructions

1. **Create `src/panels/index.js` — Panel Registry:**

   ```javascript
   // ─── Panel Registry ──────────────────────────────────────────
   import { createAccordion, applyModeFilter } from '../components/accordion.js';
   import { getCurrentMode, onModeChange } from '../router.js';
   
   const panels = [];
   
   /**
    * Register a panel module.
    * @param {Object} panel
    * @param {string} panel.id
    * @param {string} panel.title
    * @param {string} [panel.icon]
    * @param {string[]} panel.modes - ['training'] | ['playground'] | ['training', 'playground']
    * @param {boolean} [panel.defaultExpanded=false]
    * @param {function} panel.render - (bodyElement: HTMLElement) => void
    * @param {function} [panel.update] - Called per frame or per WS update
    */
   export function registerPanel(panel) {
     panels.push(panel);
   }
   
   export function addPanels(newPanels) {
     newPanels.forEach(p => panels.push(p));
   }
   
   /** Build all panels into the sidebar scroll container. */
   export function renderAllPanels(container) {
     container.innerHTML = '';
     for (const panel of panels) {
       const { element, body, setExpanded } = createAccordion({
         id: panel.id,
         title: panel.title,
         icon: panel.icon || '',
         expanded: panel.defaultExpanded ?? false,
       });
       element.dataset.modes = panel.modes.join(',');
       panel.render(body);
       panel._accordionRef = { element, body, setExpanded };
       container.appendChild(element);
     }
     applyModeFilter(container, getCurrentMode());
   }
   
   /** Called when mode changes — show/hide panels. */
   export function onModeSwitch(container, newMode) {
     applyModeFilter(container, newMode);
   }
   
   /** Bulk update call — delegates to each panel's update(). */
   export function updatePanels() {
     const mode = getCurrentMode();
     for (const panel of panels) {
       if (panel.update && panel.modes.includes(mode)) {
         panel.update();
       }
     }
   }
   ```

2. **Create shared panels** (`src/panels/shared/`):

   Each panel follows the registry contract. Example for `telemetry.js`:
   - **id:** `'telemetry'`
   - **title:** `'Telemetry'`
   - **icon:** `'📡'`
   - **modes:** `['training', 'playground']`
   - **defaultExpanded:** `true`
   - **render:** Creates stat cards for TPS (with sparkline), Tick, Total Entities (with sparkline), Swarm count, Defender count. Uses existing DOM IDs (`stat-tps`, `stat-tick`, etc.) for continuity with existing update logic.
   - **update:** Reads from `state.js` and updates values.

   `inspector.js`:
   - **modes:** `['training', 'playground']`
   - **defaultExpanded:** `false`
   - Initially hidden. When `state.selectedEntityId` is set, auto-expands and populates entity data.

   `viewport.js`:
   - All layer toggle checkboxes (grid, spatial grid, flow field, velocity, density heatmap, zone modifiers, override markers, fog toggles, arena bounds).
   - Wires checkbox `onchange` handlers to state setters (preserved from existing `init.js`).

   `legend.js`:
   - Dynamic faction legend. Reads from `ADAPTER_CONFIG.factions` and `state.activeSubFactions`.

3. **Create training panels** (`src/panels/training/`):

   `dashboard.js` — **Replaces `training-overlay.js`:**
   - **modes:** `['training']`
   - **defaultExpanded:** `true`
   - **render:** Creates:
     - Episode count (large number)
     - Stage indicator with progress bar toward 80% graduation
     - Rolling win rate bar (gradient: red → yellow → green)
     - Win/Loss streak badge
     - Episode rate counter (episodes/minute)
     - Full-width reward sparkline chart (last 50 episodes)
   - **update:** Polls CSV on 5-second interval (same logic as old `training-overlay.js`). Updates all metrics.
   - **Key difference from old overlay:** This is a full sidebar panel, not a floating popup. Much more visual real estate. No T key toggle needed.

   `ml-brain.js`:
   - **modes:** `['training']`
   - **defaultExpanded:** `true`
   - Python status, intervention mode, last directive.
   - Reads from `state.mlBrainStatus` (set by WS handler).

   `perf.js`:
   - **modes:** `['training']`
   - **defaultExpanded:** `false`
   - System performance bars (spatial, flow field, interaction, removal, movement, WS sync).
   - Reads from `PerfTelemetry` WS messages (existing logic from `panels/index.js`).

### Anti-Patterns
- Do NOT duplicate logic from `websocket.js`. The WS handler still sets state; panels read from state.
- Do NOT create a competing render loop. Use the existing `requestAnimationFrame` loop in `main.js` to call `updatePanels()`.

### Verification_Strategy
```yaml
Test_Type: manual_steps
Test_Stack: Browser
Acceptance_Criteria:
  - "In Training Mode: Dashboard, ML Brain, Telemetry, Perf, Viewport, Legend panels visible"
  - "Dashboard shows episode count, win rate, reward chart (mock or real data)"
  - "Shared panels (Telemetry, Viewport) visible in both modes"
  - "Inspector auto-expands when entity selected"
  - "Accordion expand/collapse works smoothly"
Manual_Steps:
  - "Switch to Training mode → verify all training panels appear"
  - "Click entity on canvas → verify inspector expands"
  - "Collapse/expand panels → verify smooth animation"
```

### Live_System_Impact: `safe`

---

## Task 05: Playground Mode Panels

### Overview
Implement all panels that appear in Playground Mode. The headline feature is the **Game Setup** panel — a two-path launcher (Quick Presets + Custom Game wizard) that follows the **max-3-step rule** for non-technical users. Also: Simulation Controls, Spawn Tools, Terrain Editor, Zone Modifiers, Faction Splitter, Aggro Masks, and Faction Behavior.

### Model Tier: `advanced`

### Target Files
- `debug-visualizer/src/panels/index.js` — MODIFY (add playground panels via `addPanels()`)
- `debug-visualizer/src/panels/playground/game-setup.js` — **NEW** (wizard panel)
- `debug-visualizer/src/panels/playground/sim-controls.js` — **NEW**
- `debug-visualizer/src/panels/playground/spawn.js` — **NEW**
- `debug-visualizer/src/panels/playground/terrain.js` — **NEW**
- `debug-visualizer/src/panels/playground/zones.js` — **NEW**
- `debug-visualizer/src/panels/playground/splitter.js` — **NEW**
- `debug-visualizer/src/panels/playground/aggro.js` — **NEW**
- `debug-visualizer/src/panels/playground/behavior.js` — **NEW**

### Dependencies
T03 (app shell, accordion component)

### Context_Bindings
- `context/conventions` (JS naming, DOM IDs)
- `context/engine-mechanics` (zone modifiers, terrain, aggro masks, interaction rules)
- `context/ipc-protocol` (WS command payloads for spawn, rules, terrain)
- `skills/frontend-ux-ui` (design aesthetic — wizard UX, visual cards, control panels)

### Strict Instructions

1. **Each panel module** follows the registry contract from T04. Each file exports a single panel object.

2. **`game-setup.js`** — **Game Setup Panel (MOST IMPORTANT):**

   > **UX Principle: Max 3 Steps.** Users are lazy. Things must be straightforward and easy. No walls of text, no code-like forms, no raw JSON. Everything is visual.

   The panel renders **two paths** via toggle tabs at the top:

   **Path A: Quick Presets**
   - Grid of clickable **preset cards** (visual, not a dropdown).
   - Each card shows: preset name, faction count icon, brief one-line description.
   - Clicking a card immediately triggers: `applyPreset(key)` (reuses existing preset logic from `controls/algorithm-test.js`), then auto-scrolls to canvas.
   - Presets are loaded from the same `PRESETS` map in the existing `algorithm-test.js` control module.
   - Visual treatment: cards have subtle border glow on hover, selected card stays highlighted.

   **Path B: Custom Game (3-Step Wizard)**
   
   Three horizontal step indicators at the top (1 — 2 — 3), with active step highlighted.

   **Step 1: "Choose Factions"**
   - Visual faction cards in a 2-column grid.
   - Each card: color swatch (click to cycle through palette), name input (editable inline), unit count slider (50–1000, default 200).
   - Start with 2 faction cards. "+" button adds more (max 4). "×" removes.
   - "Next →" button advances to Step 2.

   **Step 2: "Set Combat Rules"**
   - **Header:** "Who fights whom?"
   - Visual grid of faction pairs: checkbox matrix (Faction A vs Faction B). Default: all checked (everyone attacks everyone).
   - **Damage:** 3-option segmented control: `Light` | `Normal` | `Heavy` (maps to stat delta values: -0.5, -1.0, -2.0).
   - **Range:** 3-option segmented control: `Close` | `Mid` | `Far` (maps to range values: 15, 30, 60).
   - **No raw numbers visible.** The semantic labels hide the implementation details.
   - "← Back" and "Next →" buttons.

   **Step 3: "Launch"**
   - **Map Size:** 3 visual cards: `Small (400×400)` | `Medium (600×600)` | `Large (1000×1000)`.
   - **Quick Summary:** Visual recap of factions + rules configured in Steps 1-2.
   - **"🚀 Start Simulation"** button (large, accent-colored, dominant).
   - **Optional:** "Save as Preset" text link below the launch button.
   - Clicking "Start Simulation" sends the following WS commands in sequence:
     1. `kill_all` — Clear existing entities
     2. `spawn` × N — One per faction with configured counts
     3. `set_interaction_rules` — Based on Step 2 configuration
     4. `set_removal_rules` — HP ≤ 0 removal for all factions
     5. `set_nav_rules` — Default chase behavior per faction pair
   
   **Advanced Toggle (collapsed by default):**
   - Below the wizard, a small "⚙ Advanced Controls" disclosure that reveals the old manual rule forms (nav rules, interaction rules, removal rules) for power users.
   - This preserves all existing functionality from `controls/algorithm-test.js` without cluttering the primary UX.

3. **`sim-controls.js`** — Play/Pause/Step:
   - Renders Play/Pause button + Step button + tick count input.
   - Wires `sendCommand("toggle_sim")`, `sendCommand("step", { count })`.
   - Preserves existing `isPaused` state toggle logic.

4. **`spawn.js`** — Spawn Tools:
   - Renders Spawn Mode toggle button, faction selector (with add/delete faction buttons), amount slider+input, spread slider+input.
   - Preserves existing spawn click handler logic from `controls/spawn.js`.
   - Includes the Add Faction modal (rendered dynamically, not in HTML).

5. **`terrain.js`** — Terrain Editor:
   - Paint Mode toggle, brush selector (Wall/Mud/Pushable/Clear), Save/Load/Clear terrain buttons.
   - Preserves file input logic for scenario load.

6. **`zones.js`** — Zone Modifiers:
   - Place Zone toggle, attract/repel type selector, faction dropdown, radius/intensity/duration inputs.
   - Ghost zone preview on canvas (existing logic in `entities.js` remains).

7. **`splitter.js`** — Faction Splitter:
   - Split Mode toggle, source faction selector, split percentage slider.
   - Active sub-faction list (populated from state).

8. **`aggro.js`** — Aggro Masks:
   - Renders the aggro mask grid (faction pair checkboxes).
   - Reads from `state.aggroMasks` and sends `set_aggro_mask` commands.

9. **`behavior.js`** — Faction Behavior:
   - Faction behavior mode toggles (populated dynamically from connected factions).

10. **Register all playground panels** by calling `addPanels()` from `panels/index.js` at module init time. **Game Setup must be the FIRST panel registered** (appears at top of sidebar). Import order determines render order.

### Anti-Patterns
- Do NOT modify `controls/init.js` yet — that's T06's job.
- Do NOT duplicate command-sending logic. Import `sendCommand` from `websocket.js`.
- Each panel renders its OWN DOM elements with unique IDs (no ID collisions with training panels).
- Do NOT show raw numeric values in the Custom Game wizard. Use semantic labels (Light/Normal/Heavy, Close/Mid/Far, Small/Medium/Large).
- Do NOT require users to type JSON or code-like syntax anywhere in the wizard.

### Verification_Strategy
```yaml
Test_Type: manual_steps
Test_Stack: Browser
Acceptance_Criteria:
  - "In Playground Mode: Game Setup is first panel, auto-expanded"
  - "Quick Presets: clicking a preset card spawns entities and applies rules"
  - "Custom Game: 3-step wizard navigates forward/backward correctly"
  - "Custom Game Step 1: can add/remove factions, adjust counts"
  - "Custom Game Step 2: combat grid shows, damage/range selectors work"
  - "Custom Game Step 3: Start Simulation sends correct WS commands"
  - "Advanced toggle reveals manual rule forms"
  - "Training-only panels (Dashboard, ML Brain) NOT visible"
  - "All other playground panels render correctly"
Manual_Steps:
  - "Switch to Playground mode → verify Game Setup at top"
  - "Click a Quick Preset card → entities appear on canvas"
  - "Walk through Custom Game wizard: 2 factions, Normal damage, Medium map → Launch"
  - "Expand Advanced toggle → verify manual rule forms appear"
  - "Expand Spawn panel → verify faction selector, sliders render"
```

### Live_System_Impact: `safe`

---

## Task 06: Integration & Polish

### Overview
Wire all panels into the app shell, connect control event handlers to the mode-aware panel system, implement mode transition animations, ensure cross-mode state persistence, and verify all existing functionality works end-to-end.

### Model Tier: `advanced`

### Target Files
- `debug-visualizer/src/controls/init.js` — **REWRITE** (mode-aware control initialization)
- `debug-visualizer/src/main.js` — MODIFY (final wiring)
- `debug-visualizer/src/websocket.js` — MODIFY (import toast from components, update panel callbacks)

### Dependencies
T04 (training panels exist), T05 (playground panels exist)

### Context_Bindings
- `context/conventions`
- `context/architecture`
- `skills/frontend-ux-ui` (design aesthetic — final polish, transitions, atmospheric effects)

### Strict Instructions

1. **Rewrite `src/controls/init.js`:**
   
   The current `initControls()` binds directly to DOM elements by ID. Since panels are now JS-rendered and may not exist in DOM until their mode is active, the control binding strategy changes:
   
   - **Canvas event handlers** (mousedown, mousemove, mouseup, wheel, dblclick) remain global — they don't depend on panels.
   - **Panel-specific handlers** (spawn button, paint button, etc.) are bound INSIDE each panel's `render()` function. They are NOT in `initControls()` anymore.
   - `initControls()` now only handles canvas events and keyboard shortcuts.
   
   Key changes:
   - Remove all `document.getElementById('spawn-mode-btn')`, etc. from `initControls()`.
   - Keep canvas drag/zoom/click logic.
   - Keep the `clearModes()` function, but it must be null-safe (panels may not be in DOM).

2. **Update `src/main.js`** — Final wiring:
   
   ```javascript
   // Import order matters — CSS first, then modules
   import './styles/reset.css';
   import './styles/variables.css';
   import './styles/layout.css';
   import './styles/panels.css';
   import './styles/controls.css';
   import './styles/canvas.css';
   import './styles/animations.css';
   import './styles/training.css';
   
   import { initRouter, onModeChange, getCurrentMode } from './router.js';
   import { renderTabs, updateTabs } from './components/tabs.js';
   import { renderAllPanels, onModeSwitch, updatePanels } from './panels/index.js';
   // Import panel registrations (side-effect imports)
   import './panels/shared/telemetry.js';
   import './panels/shared/inspector.js';
   import './panels/shared/viewport.js';
   import './panels/shared/legend.js';
   import './panels/training/dashboard.js';
   import './panels/training/ml-brain.js';
   import './panels/training/perf.js';
   import './panels/playground/game-setup.js';
   import './panels/playground/sim-controls.js';
   import './panels/playground/spawn.js';
   import './panels/playground/terrain.js';
   import './panels/playground/zones.js';
   import './panels/playground/splitter.js';
   import './panels/playground/aggro.js';
   import './panels/playground/behavior.js';
   
   import * as S from './state.js';
   import { initCanvases, resizeCanvas, drawEntities, drawFog, drawBackground, drawArenaBounds } from './draw/index.js';
   import { connectWebSocket } from './websocket.js';
   import { initControls } from './controls/init.js';
   
   // ── Initialize ────────────────────────────────────────────
   initRouter();
   
   const bgCanvas = document.getElementById('canvas-bg');
   const canvasEntities = document.getElementById('canvas-entities');
   initCanvases(bgCanvas, canvasEntities);
   
   renderTabs(document.getElementById('tab-bar'));
   renderAllPanels(document.getElementById('panel-scroll'));
   
   onModeChange((newMode, oldMode) => {
     updateTabs();
     onModeSwitch(document.getElementById('panel-scroll'), newMode);
   });
   
   window.addEventListener('resize', resizeCanvas);
   initControls();
   
   // ── Render Loop ───────────────────────────────────────────
   function renderFrame() {
     const ctx = canvasEntities.getContext('2d');
     ctx.clearRect(0, 0, canvasEntities.width, canvasEntities.height);
     drawEntities();
     if (S.showFog) drawFog();
     drawArenaBounds(ctx);
     updatePanels(); // NEW: per-frame panel updates
     requestAnimationFrame(renderFrame);
   }
   
   resizeCanvas();
   connectWebSocket();
   requestAnimationFrame(renderFrame);
   ```

3. **Update `src/websocket.js`:**
   - Import `showToast` from `./components/toast.js` instead of defining it inline.
   - Remove the inline `showToast` function.
   - Ensure `sendCommand` is still exported (used by panel modules).

4. **Cross-mode state persistence:**
   - When switching from Playground → Training, `state.spawnMode`, `state.paintMode` etc. are cleared (call `clearModes()`).
   - When switching from Training → Playground, the canvas state (zoom, pan, entities, WS connection) is preserved.
   - The WS connection is NEVER disconnected during mode switches.

5. **Clean up old files:**
   - Delete `js/` directory (replaced by `src/`)
   - Delete `css/` directory (replaced by `src/styles/`)
   - Delete `js/training-overlay.js` (replaced by `src/panels/training/dashboard.js`)
   - Keep `README.md`, `docs/`, `logs/` symlink, `index.html`

6. **Final verification checklist:**
   - [ ] `npm run dev` starts without errors
   - [ ] Training Mode shows correct panel set
   - [ ] Playground Mode shows correct panel set
   - [ ] Tab switching is instant (< 100ms)
   - [ ] Canvas renders 10K entities at 60fps (unchanged)
   - [ ] WS connects and receives SyncDelta messages
   - [ ] Spawn Mode works (click to place entities)
   - [ ] Paint Mode works (drag to paint terrain)
   - [ ] Zone placement works
   - [ ] Split Mode works
   - [ ] Algorithm Test presets load
   - [ ] Training Dashboard polls CSV and shows metrics
   - [ ] ML Brain panel updates from WS brain messages
   - [ ] Perf bars update from WS telemetry
   - [ ] Entity Inspector populates on click
   - [ ] Fog layer toggles work
   - [ ] `npm run build` produces clean dist/

### Anti-Patterns
- Do NOT refactor canvas rendering code. It is preserved as-is.
- Do NOT change the WebSocket message protocol. The Rust core is untouched.
- Do NOT break the render loop by adding blocking operations.

### Verification_Strategy
```yaml
Test_Type: manual_steps + e2e
Test_Stack: Browser + running micro-core
Acceptance_Criteria:
  - "All 12 verification checklist items pass"
  - "No console errors"
  - "npm run build succeeds"
  - "Production build (dist/) serves correctly"
Suggested_Test_Commands:
  - "cd debug-visualizer && npm run dev"
  - "cd micro-core && cargo run -- --smoke-test"
Manual_Steps:
  - "Full walkthrough of both modes"
  - "Switch between modes 10 times rapidly — no crashes"
  - "Connect to running micro-core, verify entities render"
  - "In Playground: spawn 500 entities, paint terrain, place zone"
  - "Switch to Training, verify training data, switch back, verify playground state persisted"
```

### Live_System_Impact: `safe`
