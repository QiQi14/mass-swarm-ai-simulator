# Feature 1: Foundation & Layout (Tasks 01, 05, 06)

## Task 01: Drawflow + CSS Foundation

**Model Tier:** `standard`
**Execution Phase:** 1 (Parallel)
**Live System Impact:** `safe` — new files only, no existing code modified except `package.json`

### Target Files
- `debug-visualizer/package.json` — add `drawflow` dependency
- `debug-visualizer/src/styles/node-editor.css` — [NEW] Drawflow theme overrides
- `debug-visualizer/src/node-editor/drawflow-setup.js` — [NEW] Drawflow initialization

### Context Bindings
- `context/project/conventions.md`
- `context/project/tech-stack.md`
- `skills/frontend-ux-ui`
- `strategy_brief.md` — Section "Library Recommendation: Drawflow"

### Strict Instructions

#### 1. Install Drawflow

Add to `package.json` devDependencies:
```json
"drawflow": "^0.0.60"
```

#### 2. Create `src/node-editor/drawflow-setup.js`

This module exports a factory function that:
1. Imports `Drawflow` from the `drawflow` package
2. Imports `drawflow/dist/drawflow.min.css`
3. Creates and configures a Drawflow instance on a given container element
4. Enables drag-and-drop, rerouting, and zoom
5. Exports `createEditor(containerElement)` → returns `{ editor, destroy }`

Key API contract:
```javascript
/**
 * Initialize a Drawflow editor within the given container.
 * @param {HTMLElement} container - Must be a div with id="drawflow"
 * @returns {{ editor: Drawflow, destroy: () => void }}
 */
export function createEditor(container) { ... }

/**
 * Register all custom node types with the editor.
 * Called after createEditor(). Node modules register via this function.
 * @param {Drawflow} editor
 */
export function registerAllNodes(editor) { ... }

/**
 * Node registration hook — other node modules call this to self-register.
 */
const nodeRegistry = new Map();
export function registerNodeType(typeName, { html, inputs, outputs }) { ... }
```

Configuration:
- `editor.reroute = true` (allow connection rerouting)
- `editor.reroute_fix_curvature = true`
- `editor.force_first_input = false`
- Default zoom: `editor.zoom_min = 0.3`, `editor.zoom_max = 2.0`

#### 3. Create `src/styles/node-editor.css`

Override Drawflow default styles to match the glassmorphic design system from `variables.css`:

**Node styling (`.drawflow-node`):**
- Background: `rgba(6, 10, 16, 0.25)` with `backdrop-filter: blur(12px) saturate(1.8) brightness(1.05)`
- Border: `1px solid rgba(255, 255, 255, 0.07)`, top border brighter `rgba(255, 255, 255, 0.12)`
- Border-radius: `12px`
- Box-shadow: same as `.overlay-card`
- Font: `var(--font-display)`, color: `var(--text-primary)`
- Min-width: `200px`

**Node header (custom `.node-header` class inside node HTML):**
- Same as `.overlay-card__header` — uppercase, 10px, letter-spacing 0.1em
- Color depends on node type: Faction = `--color-swarm`, Unit = `--accent-secondary`, etc.

**Connection lines (`.connection .main-path`):**
- Stroke: `var(--accent-primary)` with opacity 0.6
- Stroke-width: `2px`
- When hovered: `stroke-width: 3px`, full opacity

**Port dots (`.drawflow-node .input`, `.drawflow-node .output`):**
- Size: `12px × 12px`
- Border-radius: `50%`
- Background: `var(--accent-primary-dim)`
- Border: `2px solid var(--accent-primary)`
- Hover: glow effect `box-shadow: 0 0 8px var(--accent-primary-glow)`

**Editor canvas (`.drawflow`):**
- Background: `transparent` (shows simulation canvas underneath)
- Grid pattern CSS background for the node editor space (subtle dot grid, matching training page)

**Selected node (`.drawflow-node.selected`):**
- Border-color: `var(--accent-primary)` at 0.6 opacity
- Box-shadow adds glow: `0 0 20px var(--accent-primary-glow)`

**Context menu & delete (`.drawflow-delete`):**
- Style as a small circular button with `--accent-danger` background

**Focus Mode Toggle (`.drawflow-container`):**

The Drawflow container supports two opacity modes, controlled by a CSS custom property `--editor-opacity` and a class toggle:

```css
/* Default: semi-transparent (30%), sim visible underneath */
.drawflow-container {
  position: fixed;
  top: 40px;  /* below top bar */
  left: 0;
  right: 0;
  bottom: 60px;  /* above bottom toolbar */
  z-index: 10;
  background: rgba(5, 6, 8, var(--editor-opacity, 0.3));
  transition: background 0.4s var(--ease-out-expo),
              backdrop-filter 0.4s var(--ease-out-expo);
  backdrop-filter: blur(0px);
  -webkit-backdrop-filter: blur(0px);
}

/* Focus Mode: strong frost glass (90%) */
.drawflow-container--focus {
  --editor-opacity: 0.90;
  backdrop-filter: blur(20px) saturate(1.8);
  -webkit-backdrop-filter: blur(20px) saturate(1.8);
}
```

- Default (no class): 30% alpha, no blur → sim canvas clearly visible
- `.drawflow-container--focus`: 90% alpha + strong frost blur → focused editing
- Toggled by a button in the top bar (see Task 06)
- State persisted in `localStorage` key: `playground_focus_mode`

### Verification Strategy
```
Test_Type: manual_steps
Test_Stack: Vite dev server
Acceptance_Criteria:
  - "npm install succeeds with drawflow in node_modules"
  - "Importing createEditor does not throw"
  - "node-editor.css loads without syntax errors (check Vite console)"
Manual_Steps:
  - "Temporarily import drawflow-setup.js in main.js → verify no console errors"
  - "Verify CSS variables resolve correctly in browser dev tools"
```

---

## Task 05: Preset Gallery Splash

**Model Tier:** `standard`
**Execution Phase:** 1 (Parallel)
**Live System Impact:** `safe` — new files only

### Target Files
- `debug-visualizer/src/node-editor/preset-gallery.js` — [NEW] Preset splash overlay
- `debug-visualizer/src/styles/preset-gallery.css` — [NEW] Gallery styling

### Context Bindings
- `context/project/conventions.md`
- `skills/frontend-ux-ui`
- `strategy_brief.md` — Section "Preset Gallery (Splash Overlay)"

### Strict Instructions

#### 1. Create `src/node-editor/preset-gallery.js`

Exports:
```javascript
/**
 * Show the preset selection splash overlay.
 * @param {Object} callbacks
 * @param {(presetKey: string) => void} callbacks.onSelect — Called when user picks a preset
 * @param {() => void} callbacks.onBlank — Called when user chooses "Create from Scratch"
 */
export function showPresetGallery({ onSelect, onBlank }) { ... }

/**
 * Hide and remove the splash overlay from DOM.
 */
export function hidePresetGallery() { ... }
```

**Preset definitions** — reuse the existing 5 preset keys from `algorithm-test.js` plus add a "Blank Canvas" option:

| Card | Icon | Title | Subtitle |
|------|------|-------|----------|
| `swarm_vs_defender` | ⚔️ → SVG (swords) | Swarm vs Defender | 500 vs 100 |
| `three_faction_melee` | 🔺 → SVG (triangle) | 3-Faction Melee | 3×100 FFA |
| `ranged_vs_melee` | 🎯 → SVG (crosshair) | Ranged vs Melee | 200 vs 200 |
| `tank_screen` | 🛡️ → SVG (shield) | Tank Screen | 300+100+200 |
| `waypoint_navigation` | 📍 → SVG (map-pin) | Waypoint Rally | 500 → (800,800) |
| `blank` | ➕ → SVG (plus) | Blank Canvas | Start from scratch |

**All icons MUST use SVG from `icons.js` — NO emoji.** Extend `icons.js` if needed with: `swords`, `triangle`, `crosshair`, `shield`, `mapPin`, `plus`.

**DOM structure:**
```html
<div class="preset-gallery" id="preset-gallery">
  <div class="preset-gallery__backdrop"></div>
  <div class="preset-gallery__dialog">
    <h2 class="preset-gallery__title">SELECT A SCENARIO</h2>
    <div class="preset-gallery__grid">
      <!-- 6 cards -->
    </div>
    <div class="preset-gallery__footer">
      <button class="preset-gallery__blank-btn">Create from Scratch</button>
    </div>
  </div>
</div>
```

Card structure — each card is a button that triggers `onSelect(presetKey)` or `onBlank()`:
```html
<button class="preset-card" data-preset="swarm_vs_defender">
  <div class="preset-card__icon">{SVG}</div>
  <div class="preset-card__title">Swarm vs Defender</div>
  <div class="preset-card__desc">500 vs 100</div>
</button>
```

#### 2. Create `src/styles/preset-gallery.css`

Reuse the `stage-modal` pattern from `overlay.css`:

- `.preset-gallery` — same positioning as `.stage-modal` (fixed inset 0, z-2000)
- `.preset-gallery__backdrop` — `rgba(0,0,0,0.6)` with `backdrop-filter: blur(4px)`
- `.preset-gallery__dialog` — same glassmorphic treatment as `.stage-modal__dialog`
- `.preset-gallery__grid` — CSS Grid: `grid-template-columns: repeat(3, 1fr)`, gap `16px`
  - At `max-width: 600px`: `grid-template-columns: repeat(2, 1fr)`
- `.preset-card` — Clickable card with hover glow animation
  - Background: `rgba(255, 255, 255, 0.03)`
  - Border: `1px solid rgba(255, 255, 255, 0.06)`
  - Border-radius: `12px`
  - Hover: border → `var(--border-emphasis)`, box-shadow glow
  - Padding: `24px`
  - Cursor: pointer
  - Transition: `var(--transition-base)`
- `.preset-card__icon` — 48px container, `color: var(--accent-primary)`, `opacity: 0.7`
- `.preset-card__title` — `var(--font-display)`, 14px, `var(--text-primary)`, `font-weight: 600`
- `.preset-card__desc` — `var(--font-mono)`, 11px, `var(--text-secondary)`
- `.preset-gallery__title` — uppercase, letter-spacing, centered, `var(--text-primary)`
- `.preset-gallery__blank-btn` — styled as outline button, centered

**Show/hide animation:** Use opacity + transform transition (same as `stage-modal`):
```css
.preset-gallery { opacity: 0; pointer-events: none; transition: opacity 0.25s ease; }
.preset-gallery--open { opacity: 1; pointer-events: auto; }
```

### Verification Strategy
```
Test_Type: manual_steps
Test_Stack: Vite dev server
Acceptance_Criteria:
  - "showPresetGallery() renders a fullscreen modal with 6 cards"
  - "Clicking a preset card calls onSelect with the correct key"
  - "Clicking 'Create from Scratch' calls onBlank"
  - "hidePresetGallery() removes the overlay"
  - "Cards use SVG icons, not emoji"
  - "Modal is responsive at 375px width (2 columns)"
Manual_Steps:
  - "Import and call showPresetGallery() from browser console"
  - "Verify glassmorphic styling matches training page modals"
```

---

## Task 06: Layout Migration — index.html + playground-main.js

**Model Tier:** `advanced`
**Execution Phase:** 1 (Parallel with T01–T05)
**Live System Impact:** `additive` — creates new entry point, modifies `index.html` structure

### Target Files
- `debug-visualizer/index.html` — MODIFY (replace sidebar with floating overlay)
- `debug-visualizer/src/playground-main.js` — [NEW] New playground entry point

### Context Bindings
- `context/project/conventions.md`
- `strategy_brief.md` — Sections "Layout Decision" and "Playground Layout Decision"
- `skills/frontend-ux-ui`
- `.agents/knowledge/workflow/gotcha_dom_deletion_crashing_modules.md`
- `.agents/knowledge/frontend/gotcha_orphaned_css_files.md`

### Strict Instructions

#### 1. Modify `index.html`

Replace the sidebar-based layout with a fullscreen canvas + floating overlay layout matching the training page pattern.

**New HTML structure:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SwarmControl — Playground</title>
    <meta name="description" content="Visual node-based playground for the Mass-Swarm AI Simulator">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
</head>
<body class="playground-page">
    <!-- Fullscreen Canvas -->
    <main class="canvas-area" id="canvas-area" style="width:100vw;height:100vh;">
        <canvas id="canvas-bg"></canvas>
        <canvas id="canvas-entities"></canvas>
        <div class="canvas-hint" id="canvas-hint">
            Pan: drag · Zoom: scroll · Double-click: reset view
        </div>
    </main>

    <!-- Drawflow Node Editor Overlay -->
    <div id="drawflow-container" class="drawflow-container"></div>

    <!-- Overlay Root -->
    <div id="playground-overlay-root" class="overlay--expanded">
        <!-- Top Bar -->
        <div class="overlay-top-bar" id="overlay-top-bar"></div>

        <!-- Bottom Toolbar -->
        <div class="playground-bottom-toolbar" id="playground-bottom-toolbar"></div>

        <!-- Right Side Cards -->
        <div class="overlay-right-cluster" id="playground-right-cluster"></div>

        <!-- Minimized Strip -->
        <div class="overlay-mini-strip" id="overlay-mini-strip"></div>
    </div>

    <!-- Preset Gallery (injected by JS) -->

    <!-- DOM stubs for legacy modules (hidden, prevents crash) -->
    <div style="display:none">
        <div id="sidebar"></div>
        <nav id="tab-bar"></nav>
        <div id="panel-scroll"></div>
        <div id="bottom-sheet-handle"></div>
    </div>

    <script type="module" src="/src/playground-main.js"></script>
</body>
</html>
```

> [!CAUTION]
> **DOM Stub Rule:** The hidden `<div>` block with `#sidebar`, `#tab-bar`, `#panel-scroll`, and `#bottom-sheet-handle` MUST remain until the Integration task (T07) verifies no legacy module depends on them.

#### 2. Create `src/playground-main.js`

New entry point for the playground page. This replaces `main.js` as the playground's script root.

**Responsibilities:**
- Import all CSS (same order as `main.js`, plus add `node-editor.css` and `preset-gallery.css`)
- Initialize canvases (reuse `draw/index.js`)
- Connect WebSocket (reuse `websocket.js`)
- Initialize Drawflow node editor (import from `node-editor/drawflow-setup.js`)
- Build the top bar (title, preset button, **Focus Mode toggle**, launch button, minimize toggle)
- Build the bottom toolbar (add-node buttons, terrain toggle, sim controls)
- Build the right-side cards (telemetry strip, entity inspector)
- Show preset gallery on first load (`localStorage` key: `playground_has_visited`)
- Wire the ▶ Launch button to the graph compiler
- Run the render loop (same as `main.js`)

**Key difference from `main.js`:** Does NOT import the panel registry system or accordion components. The node editor replaces those.

**Do NOT modify `main.js`.** It remains functional for any legacy routes. `playground-main.js` is the new entry.

### Verification Strategy
```
Test_Type: manual_steps
Test_Stack: Vite dev server
Acceptance_Criteria:
  - "index.html renders fullscreen canvas without a sidebar"
  - "Top bar shows 'SwarmControl' with version badge"
  - "Drawflow container div exists in DOM"
  - "Bottom toolbar has placeholder buttons"
  - "Legacy modules do not crash on page load (check console for TypeError)"
  - "Training page (training.html) is completely unaffected"
Manual_Steps:
  - "Open http://localhost:5173/ — verify fullscreen canvas"
  - "Verify no sidebar visible"
  - "Check browser console for zero errors"
  - "Open http://localhost:5173/training.html — verify unchanged"
```
