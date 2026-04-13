# Feature 1: Vite Migration & Design System (Tasks 01–02)

## Task 01: Vite Setup & Project Restructure

### Overview
Migrate the debug visualizer from a zero-build-step static HTML app to a Vite-powered vanilla JS project. This is a structural refactor only — no logic changes. All existing code moves from `js/` and `css/` into `src/` with updated import paths.

### Model Tier: `standard`

### Target Files
- `debug-visualizer/package.json` — **NEW**
- `debug-visualizer/vite.config.js` — **NEW**
- `debug-visualizer/.gitignore` — **NEW**
- `debug-visualizer/src/config.js` — MOVE from `js/config.js`
- `debug-visualizer/src/state.js` — MOVE from `js/state.js`
- `debug-visualizer/src/websocket.js` — MOVE from `js/websocket.js`
- `debug-visualizer/src/draw/index.js` — MOVE from `js/draw/index.js`
- `debug-visualizer/src/draw/terrain.js` — MOVE from `js/draw/terrain.js`
- `debug-visualizer/src/draw/entities.js` — MOVE from `js/draw/entities.js`
- `debug-visualizer/src/draw/overlays.js` — MOVE from `js/draw/overlays.js`
- `debug-visualizer/src/draw/fog.js` — MOVE from `js/draw/fog.js`
- `debug-visualizer/src/draw/effects.js` — MOVE from `js/draw/effects.js`
- `debug-visualizer/src/controls/index.js` — MOVE from `js/controls/index.js`
- `debug-visualizer/src/controls/init.js` — MOVE from `js/controls/init.js`
- `debug-visualizer/src/controls/paint.js` — MOVE from `js/controls/paint.js`
- `debug-visualizer/src/controls/spawn.js` — MOVE from `js/controls/spawn.js`
- `debug-visualizer/src/controls/zones.js` — MOVE from `js/controls/zones.js`
- `debug-visualizer/src/controls/split.js` — MOVE from `js/controls/split.js`
- `debug-visualizer/src/controls/algorithm-test.js` — MOVE from `js/controls/algorithm-test.js`
- `debug-visualizer/src/main.js` — MOVE from `js/main.js` (temporary scaffold)

### Dependencies
None.

### Context_Bindings
- `context/conventions` (JS file naming, module patterns)
- `context/architecture` (debug-visualizer folder structure)

### Strict Instructions

1. **Create `package.json`:**
   ```json
   {
     "name": "debug-visualizer",
     "version": "0.2.0",
     "private": true,
     "type": "module",
     "scripts": {
       "dev": "vite",
       "build": "vite build",
       "preview": "vite preview"
     },
     "devDependencies": {
       "vite": "^6.0.0"
     }
   }
   ```

2. **Create `vite.config.js`:**
   ```javascript
   import { defineConfig } from 'vite';

   export default defineConfig({
     root: '.',
     publicDir: 'public',
     server: {
       port: 5173,
       open: true,
       proxy: {
         '/logs': {
           target: 'http://localhost:8080',
           changeOrigin: true,
         }
       }
     },
     build: {
       outDir: 'dist',
       emptyOutDir: true,
     }
   });
   ```
   
   > **Note:** The `/logs` proxy forwards training CSV requests to the Rust HTTP server (port 8080) during dev. In production, both are served from the same origin.

3. **Create `.gitignore`:**
   ```
   node_modules/
   dist/
   ```

4. **Create `src/` directory** and move all JS files:
   - `js/config.js` → `src/config.js`
   - `js/state.js` → `src/state.js`
   - `js/websocket.js` → `src/websocket.js`
   - `js/main.js` → `src/main.js`
   - `js/draw/*` → `src/draw/*`
   - `js/controls/*` → `src/controls/*`

5. **Update all import paths** in moved files. Relative imports remain the same since directory structure is preserved. The key change is that `index.html` now points to `src/main.js` instead of `js/main.js`:
   ```html
   <script type="module" src="/src/main.js"></script>
   ```

6. **Move CSS files** to `src/styles/`:
   - `css/variables.css` → `src/styles/variables.css`
   - `css/layout.css` → `src/styles/layout.css`
   - `css/panels.css` → `src/styles/panels.css`
   - `css/controls.css` → `src/styles/controls.css`
   - `css/canvas.css` → `src/styles/canvas.css`
   - `css/animations.css` → `src/styles/animations.css`
   - `css/training-overlay.css` → `src/styles/training.css`

7. **Update `index.html`** CSS link paths from `css/` to `src/styles/` (Vite resolves these).

8. **Create `public/` directory** and move the `logs` symlink there (if it exists).

9. **Remove the old `js/training-overlay.js`** — its functionality will be rebuilt as `src/panels/training/dashboard.js` in T04.

10. **Verify:** Run `npm install && npm run dev`. The app should load in the browser with the existing UI fully functional (just served by Vite now). All canvas rendering, WS connection, controls should work identically.

### Anti-Patterns
- Do NOT install React, Vue, or any framework.
- Do NOT rename any exported functions or state variables — downstream code depends on exact names.
- Do NOT change any logic. This is purely a structural move.

### Verification_Strategy
```yaml
Test_Type: manual_steps
Test_Stack: Browser + Vite dev server
Acceptance_Criteria:
  - "npm run dev starts Vite dev server without errors"
  - "Browser opens and shows the existing visualizer UI"
  - "WebSocket connects to micro-core (green dot)"
  - "npm run build produces dist/ directory"
Manual_Steps:
  - "cd debug-visualizer && npm install && npm run dev"
  - "Verify canvas renders, sidebar appears, WS connects"
  - "npm run build — verify no build errors"
```

### Live_System_Impact: `safe`

---

## Task 02: Design System & CSS Rewrite

### Overview
Rewrite the CSS design system with a **bold "Tactical Command Center" aesthetic** following the `frontend-ux-ui` skill. This is NOT a generic dark theme — it must feel like commanding a swarm from a military war room. Distinctive typography, atmospheric textures, and intentional motion design.

### Model Tier: `advanced`

### Target Files
- `debug-visualizer/src/styles/variables.css` — **REWRITE**
- `debug-visualizer/src/styles/reset.css` — **NEW**
- `debug-visualizer/src/styles/layout.css` — **REWRITE**
- `debug-visualizer/src/styles/panels.css` — **REWRITE**
- `debug-visualizer/src/styles/controls.css` — MOVE + restyle from `css/controls.css`
- `debug-visualizer/src/styles/canvas.css` — MOVE (no changes)
- `debug-visualizer/src/styles/animations.css` — **REWRITE**
- `debug-visualizer/src/styles/training.css` — **NEW** (replaces `training-overlay.css`)

### Dependencies
None (parallel with T01, but needs T01's file structure).

### Context_Bindings
- `context/conventions` (CSS variables naming)
- `skills/frontend-ux-ui` (design aesthetic guidelines — MUST READ)

### Strict Instructions

> **Aesthetic Direction: Tactical Command Center**
> Think: military tactical display, mission control dashboard, radar screen. NOT: generic SaaS dark mode, glassmorphism template, Stripe clone. The user will be demonstrating this to stakeholders — it must be **unforgettable**.

1. **Rewrite `variables.css`** — Tactical design tokens:

   **Typography:** Use [Geist](https://vercel.com/font) (variable weight) for UI text and Geist Mono for data values. Import via Google Fonts or Fontsource. These are distinctive, high-quality fonts that signal "built by engineers" without being generic.

   ```css
   @import url('https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=Geist+Mono:wght@400;500;600&display=swap');
   /* NOTE: If Geist is not on Google Fonts at execution time, use 
      @fontsource/geist via npm, or fall back to 'DM Sans' + 'IBM Plex Mono' 
      as alternatives with similar character. NEVER fall back to Inter/Roboto. */

   :root {
     /* ── Void (Base Surface) ── */
     --bg-void: #050608;
     --bg-surface: rgba(8, 12, 18, 0.92);
     --bg-surface-raised: rgba(14, 20, 30, 0.94);
     --bg-surface-overlay: rgba(20, 28, 42, 0.96);
     --bg-input: rgba(6, 10, 16, 0.85);
     
     /* ── Tactical Accent: Electric Cyan ── */
     --accent-primary: #06d6a0;
     --accent-primary-dim: rgba(6, 214, 160, 0.15);
     --accent-primary-glow: rgba(6, 214, 160, 0.35);
     --accent-secondary: #118ab2;
     --accent-secondary-dim: rgba(17, 138, 178, 0.15);
     --accent-warning: #ffd166;
     --accent-warning-dim: rgba(255, 209, 102, 0.15);
     --accent-danger: #ef476f;
     --accent-danger-dim: rgba(239, 71, 111, 0.15);
     
     /* ── Entity/Faction Colors (neon treatment) ── */
     --color-swarm: #ef476f;
     --color-swarm-glow: rgba(239, 71, 111, 0.4);
     --color-defender: #06d6a0;
     --color-defender-glow: rgba(6, 214, 160, 0.4);
     
     /* ── Text Hierarchy ── */
     --text-primary: #e8ecf0;
     --text-secondary: #7a8ba3;
     --text-tertiary: #3d4f63;
     --text-accent: var(--accent-primary);
     --text-data: var(--accent-primary);  /* For numeric data readouts */
     
     /* ── Borders (subtle glow, not flat lines) ── */
     --border-subtle: rgba(6, 214, 160, 0.06);
     --border-default: rgba(6, 214, 160, 0.12);
     --border-emphasis: rgba(6, 214, 160, 0.22);
     --border-active: rgba(6, 214, 160, 0.40);
     
     /* ── Status ── */
     --status-connected: #06d6a0;
     --status-disconnected: #ef476f;
     --status-reconnecting: #ffd166;
     
     /* ── Typography ── */
     --font-display: 'Geist', 'DM Sans', system-ui, sans-serif;
     --font-body: 'Geist', 'DM Sans', system-ui, sans-serif;
     --font-mono: 'Geist Mono', 'IBM Plex Mono', 'Courier New', monospace;
     --font-size-2xs: 0.625rem;   /* 10px — micro labels */
     --font-size-xs: 0.6875rem;   /* 11px */
     --font-size-sm: 0.75rem;     /* 12px */
     --font-size-base: 0.8125rem; /* 13px — slightly tighter than typical */
     --font-size-lg: 1rem;        /* 16px */
     --font-size-xl: 1.25rem;     /* 20px */
     --font-size-2xl: 1.5rem;     /* 24px — dashboard numbers */
     --font-size-hero: 2rem;      /* 32px — big stat readouts */
     
     /* ── Spacing (compact for command center density) ── */
     --space-2xs: 2px;
     --space-xs: 4px;
     --space-sm: 6px;
     --space-md: 10px;
     --space-lg: 14px;
     --space-xl: 18px;
     --space-2xl: 24px;
     --space-3xl: 32px;
     
     /* ── Sizing ── */
     --sidebar-width: 380px;
     --tab-height: 44px;
     --radius-sm: 4px;
     --radius-md: 8px;
     --radius-lg: 12px;
     --radius-full: 9999px;
     
     /* ── Shadows (colored glows, not generic box-shadow) ── */
     --shadow-inset: inset 0 1px 0 rgba(255, 255, 255, 0.03);
     --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.5);
     --shadow-md: 0 4px 20px rgba(0, 0, 0, 0.6);
     --shadow-lg: 0 8px 40px rgba(0, 0, 0, 0.7);
     --shadow-glow: 0 0 20px var(--accent-primary-glow);
     --shadow-glow-danger: 0 0 20px var(--accent-danger-dim);
     
     /* ── Atmospheric Effects ── */
     --noise-opacity: 0.03;
     --scanline-opacity: 0.015;
     --grid-line-opacity: 0.04;
     
     /* ── Transitions ── */
     --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
     --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
     --transition-fast: 120ms var(--ease-out-expo);
     --transition-base: 220ms var(--ease-out-expo);
     --transition-slow: 400ms var(--ease-out-expo);
     --transition-spring: 500ms var(--ease-spring);
   }
   ```

2. **Create `reset.css`** — Base styles with atmospheric body treatment:
   ```css
   *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
   
   body {
     font-family: var(--font-body);
     font-size: var(--font-size-base);
     font-weight: 400;
     letter-spacing: 0.01em;
     background-color: var(--bg-void);
     color: var(--text-primary);
     overflow: hidden;
     height: 100vh;
     width: 100vw;
     -webkit-font-smoothing: antialiased;
     -moz-osx-font-smoothing: grayscale;
   }
   
   /* Noise texture overlay — creates atmospheric depth */
   body::before {
     content: '';
     position: fixed;
     inset: 0;
     background-image: url("data:image/svg+xml,..."); /* inline SVG noise */
     opacity: var(--noise-opacity);
     pointer-events: none;
     z-index: 9999;
   }
   ```
   
   > NOTE: The inline SVG noise pattern should be a `<filter>` with `feTurbulence`. The executor should generate this procedurally or use a CSS `background-image` with a tiny repeating noise PNG.

3. **Rewrite `layout.css`** — Tactical app shell:

   Key classes to define:
   - `.app-container` — Flex row (canvas + sidebar)
   - `.canvas-area` — Flex-grow, position relative, subtle vignette on edges
   - `.sidebar` — Fixed width, flex column. Background: `--bg-surface` with subtle vertical scanlines (`repeating-linear-gradient` at 2px intervals, `--scanline-opacity`). Left border: 1px `--border-emphasis` with `--shadow-glow` outward.
   - `.sidebar-header` — App title with tracking/uppercase treatment. Title uses `--font-display` at weight 700. The accent word uses `--text-accent` color. Subtle bottom border with gradient fade.
   - `.tab-bar` — Horizontal container with `--bg-surface-raised` background. No visible borders between tabs — differentiation through opacity and the sliding indicator.
   - `.tab-btn` — Uppercase, `--font-size-xs`, letter-spacing `0.15em`, `--text-tertiary` when inactive, `--text-primary` when active. NO background changes on hover — only text color transition.
   - `.tab-indicator` — Absolute-positioned bottom bar (2px height), `--accent-primary` color with `--shadow-glow`, slides with `--transition-spring`.
   - `.panel-scroll` — Scrollable area with custom scrollbar (thin, accent-colored thumb). Subtle grid-line background pattern.
   - `.connection-badge` — Positioned top-left of canvas. Minimal: just a dot + text. The dot pulses with `--status-connected` glow. Feels like a radar ping.
   - `.canvas-hint` — `--text-tertiary`, uppercase, tiny font, centered bottom of canvas. Fades on first interaction.

4. **Rewrite `panels.css`** — Tactical accordion panels:

   Key classes:
   - `.panel-group` — Margin-bottom for negative space between groups. No visible outer border — separation through spacing, not lines.
   - `.panel-header` — Flex row, `--font-size-xs`, uppercase, `letter-spacing: 0.12em`, `--text-secondary`. Chevron icon rotates on expand. On hover: `--text-primary` with subtle left-border glow (`border-left: 2px solid var(--accent-primary-dim)`).
   - `.panel-header[data-expanded="true"]` — `--text-accent` color, left border full `--accent-primary`.
   - `.panel-body.collapsed` — `max-height: 0; opacity: 0; overflow: hidden; padding: 0`
   - `.panel-body.expanded` — `max-height: 600px; opacity: 1; padding: var(--space-lg)`. Transition all simultaneously.
   - `.stat-card` — Dark inset card (`--bg-surface-raised`, `--shadow-inset`). Border: 1px `--border-subtle`. On active/live data: border transitions to `--border-emphasis` with faint glow.
   - `.stat-grid` — 2-column CSS grid with `--space-sm` gap. Compact layout.
   - `.stat-label` — `--font-size-2xs`, uppercase, `--text-tertiary`, letter-spacing `0.1em`
   - `.stat-value` — `--font-mono`, `--font-size-lg`, `--text-data` (accent colored). Data readouts should feel like tactical instruments, not plain text.
   - `.stat-value.hero` — `--font-size-hero`, for dashboard headline numbers.

5. **Rewrite `animations.css`** — Tactical motion design:
   
   Key animations:
   - `@keyframes panelCascadeIn` — Panels enter staggered: slide from `translateY(8px)` + `opacity: 0`. Each `.panel-group` gets `animation-delay: calc(var(--cascade-index, 0) * 60ms)`. JS sets `--cascade-index` via inline style.
   - `@keyframes radarPulse` — Status dot: scale 1→1.4→1 + opacity 1→0.6→1. Duration 2s, infinite.
   - `@keyframes dataFlash` — When a `.stat-value` updates: brief text-shadow glow flash (`0 0 8px var(--accent-primary-glow)`), 300ms.
   - `@keyframes shimmer` — Loading skeleton: horizontal gradient sweep.
   - `@keyframes scanline` — Slow vertical sweep of a thin bright line across the sidebar (30s cycle, very subtle).
   - `.mode-enter` — Applied to panel groups during mode switch. Triggers `panelCascadeIn`.
   - `.toast` — Slide-in from right, accent-colored left border, auto-dismiss.

6. **Create `training.css`** — Training-mode dashboard styles:
   
   Key classes:
   - `.training-dashboard` — Full-width panel with extra visual treatment. Background: subtle radial gradient from center.
   - `.metric-hero` — Large number readout (episode count) using `.stat-value.hero`.
   - `.win-rate-bar` — Full-width progress bar. Fill: gradient `--accent-danger` (0%) → `--accent-warning` (50%) → `--accent-primary` (100%). 80% graduation marker as thin white vertical line.
   - `.stage-badge` — Pill-shaped badge. Background: `--accent-primary-dim`, text: `--accent-primary`.
   - `.reward-chart` — Full sidebar width sparkline container with vertical grid lines.
   - `.streak-badge.win` — `--accent-primary-dim` background, green text
   - `.streak-badge.loss` — `--accent-danger-dim` background, red text

7. **Migrate `controls.css`** — Move to `src/styles/controls.css`. Restyle ALL controls:
   - Buttons: Sharp `--radius-sm` corners. Primary: `--accent-primary` background with `--shadow-glow` on hover. Active mode buttons: left border accent.
   - Inputs: `--bg-input` dark fields with `--border-subtle`. Focus ring: `--accent-primary` 1px + glow.
   - Sliders: Custom thumb in `--accent-primary`, narrow track in `--border-default`.
   - Toggles/Checkboxes: Custom-styled to match tactical theme.

### Anti-Patterns
- **NEVER** use Inter, Roboto, Arial, or system fonts as the primary face.
- **NEVER** use the overused purple-to-blue gradient pattern.
- Do NOT hard-code any colors outside `variables.css`.
- Do NOT use `!important`.
- Do NOT apply `backdrop-filter` to canvas elements.
- Do NOT make it look like a generic admin dashboard template.

### Verification_Strategy
```yaml
Test_Type: manual_steps
Test_Stack: Browser visual inspection
Acceptance_Criteria:
  - "All CSS files load without console errors"
  - "Typography is clearly NOT Inter/Roboto — Geist or fallback renders"
  - "Electric cyan accent (#06d6a0) visible on borders, active states, data values"
  - "Sidebar has atmospheric depth (noise texture, not flat solid)"
  - "Panel accordion transitions are smooth, staggered"
  - "The design feels like a tactical command center, NOT a generic SaaS dashboard"
Manual_Steps:
  - "Load page after T01 + T02 merged"
  - "Verify font rendering (Geist or DM Sans, NOT Inter)"
  - "Verify accent color (#06d6a0) on active elements"
  - "Verify noise texture overlay is visible but subtle"
  - "Check stat values use mono font in accent color"
```

### Live_System_Impact: `safe`

