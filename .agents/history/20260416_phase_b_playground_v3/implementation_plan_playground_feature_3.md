# Feature 3: Integration & Expansion (Tasks 07–11)

## Task 07: Integration & Wiring

**Model Tier:** `advanced`
**Execution Phase:** 2 (Depends on T04, T05, T06)
**Live System Impact:** `additive` — wires existing + new modules together

### Target Files
- `debug-visualizer/src/playground-main.js` — MODIFY (finalize)
- `debug-visualizer/index.html` — MODIFY (finalize, remove stubs if safe)
- `debug-visualizer/vite.config.js` — MODIFY (update entry points)

### Context Bindings
- `context/project/conventions.md`
- `implementation_plan.md` — Architecture Overview, Shared Contracts
- `strategy_brief.md`
- `.agents/knowledge/workflow/gotcha_dom_deletion_crashing_modules.md`
- `.agents/knowledge/frontend/gotcha_es_module_extraction_scope.md`
- `.agents/knowledge/frontend/gotcha_orphaned_css_files.md`

### Strict Instructions

#### 1. Finalize `playground-main.js`

Wire together all Phase 1 outputs:

```javascript
// CSS imports
import './styles/reset.css';
import './styles/variables.css';
import './styles/canvas.css';
import './styles/animations.css';
import './styles/overlay.css';
import './styles/node-editor.css';
import './styles/preset-gallery.css';

// Core modules
import { initCanvases, resizeCanvas, drawEntities, drawFog, drawBackground, drawArenaBounds } from './draw/index.js';
import { connectWebSocket, sendCommand } from './websocket.js';
import * as S from './state.js';

// Node editor
import { createEditor, registerAllNodes } from './node-editor/drawflow-setup.js';
import { registerFactionNode } from './node-editor/nodes/faction.js';
import { registerRelationshipNode } from './node-editor/nodes/relationship.js';
import { registerUnitNode } from './node-editor/nodes/unit.js';
import { registerStatNode } from './node-editor/nodes/stat.js';
import { registerDeathNode } from './node-editor/nodes/death.js';
import { compileGraph, executeScenario, presetToGraph } from './node-editor/compiler.js';
import { showPresetGallery, hidePresetGallery } from './node-editor/preset-gallery.js';

// Components
import { createSVG } from './components/icons.js';
```

**Top bar construction** (matches training page pattern):
```javascript
function buildTopBar() {
  const bar = document.getElementById('overlay-top-bar');
  bar.innerHTML = `
    <div class="overlay-top-bar__left">
      <span class="overlay-top-bar__title">SWARM<span style="color:var(--accent-primary)">CONTROL</span></span>
      <span style="font-family:var(--font-mono);font-size:10px;color:var(--text-tertiary)">v0.3.0</span>
    </div>
    <div class="overlay-top-bar__actions">
      <button class="overlay-btn" id="btn-presets" title="Presets">{gridSVG}</button>
      <button class="overlay-btn overlay-btn--launch" id="btn-launch" title="Launch">▶</button>
      <button class="overlay-btn" id="btn-settings" title="Settings">{settingsSVG}</button>
      <button class="overlay-btn" id="btn-minimize" title="Minimize">{minimizeSVG}</button>
    </div>
  `;
}
```

**Bottom toolbar construction:**
```javascript
function buildBottomToolbar() {
  const bar = document.getElementById('playground-bottom-toolbar');
  // Node add buttons — each calls editor.addNode() with default data
  // [+ Faction] [+ Unit] [+ Combat] [+ Nav] [+ Death]
  // [Terrain 🖌] [Sim Controls ⏯]
}
```

**Launch button handler:**
```javascript
document.getElementById('btn-launch').addEventListener('click', () => {
  const scenario = compileGraph(editor);
  if (scenario.errors.length > 0) {
    // Show validation toast
    return;
  }
  executeScenario(scenario, sendCommand);
});
```

**Preset gallery on first load:**
```javascript
const hasVisited = localStorage.getItem('playground_has_visited');
if (!hasVisited) {
  showPresetGallery({
    onSelect: (presetKey) => {
      const graphJson = presetToGraph(presetKey);
      editor.import(graphJson);
      hidePresetGallery();
      localStorage.setItem('playground_has_visited', 'true');
    },
    onBlank: () => {
      hidePresetGallery();
      localStorage.setItem('playground_has_visited', 'true');
    }
  });
}
```

**Preset button re-opens gallery:**
```javascript
document.getElementById('btn-presets').addEventListener('click', () => {
  showPresetGallery({ onSelect: ..., onBlank: ... });
});
```

#### 2. Update `vite.config.js`

The Vite config already has multi-page support. Verify the playground entry point works:

```javascript
rollupOptions: {
  input: {
    playground: resolve(__dirname, 'index.html'),
    training: resolve(__dirname, 'training.html'),
  },
},
```

Change `server.open` from `/training.html` to `/` (playground):
```javascript
server: {
  port: 5173,
  open: '/',
},
```

#### 3. Finalize `index.html`

- Remove DOM stubs if they are confirmed unnecessary (check all module imports in `playground-main.js`)
- Verify that **NO** import of `main.js` or old panel registry exists
- Connection badge (`status-dot`, `status-text`) should be part of the top bar now

### Verification Strategy
```
Test_Type: e2e
Test_Stack: Vite dev server + browser
Acceptance_Criteria:
  - "npm run dev opens playground at http://localhost:5173/"
  - "Preset gallery appears on first visit"
  - "Selecting a preset loads node graph into editor"
  - "▶ Launch compiles graph and spawns entities on canvas"
  - "Adding nodes via bottom toolbar works"
  - "Training page is unaffected"
  - "Zero console errors"
Manual_Steps:
  - "Clear localStorage → open page → verify splash appears"
  - "Select 'Swarm vs Defender' → verify graph loads → press Launch → verify simulation"
  - "Press [+Faction] → new Faction node appears"
  - "Open training.html in separate tab → verify unaffected"
```

---

## Task 08: Combat + Relationship Nodes (Extended)

**Model Tier:** `standard`
**Execution Phase:** 2 (Depends on T07)
**Live System Impact:** `safe` — new files + extending compiler

### Target Files
- `debug-visualizer/src/node-editor/nodes/combat.js` — [NEW]
- `debug-visualizer/src/node-editor/nodes/relationship.js` — MODIFY (extend from T02)
- `debug-visualizer/src/node-editor/compiler.js` — MODIFY (add combat + aggro compilation)

### Context Bindings
- `context/project/conventions.md`
- `context/engine/combat.md`
- `strategy_brief.md` — Sections "Combat Node" and "Relationship Node"
- `implementation_plan.md` — Shared Contracts

### Strict Instructions

#### 1. `src/node-editor/nodes/combat.js`

```html
<div class="node-header node-header--combat">
  <span class="node-header__icon">{swordsSVG}</span>
  <span>COMBAT</span>
</div>
<div class="node-body">
  <div class="node-field">
    <label>Attack Type</label>
    <div class="node-preset-btns">
      <button class="node-preset-btn" data-preset="melee">⚔️ Melee</button>
      <button class="node-preset-btn" data-preset="ranged">🏹 Ranged</button>
      <button class="node-preset-btn" data-preset="siege">💥 Siege</button>
    </div>
  </div>
  <div class="node-field">
    <label>Damage/sec</label>
    <input type="number" df-damage value="-10" class="node-input">
  </div>
  <div class="node-field">
    <label>Range</label>
    <input type="range" df-range min="5" max="200" value="15" class="node-slider">
    <span class="node-slider-value">15</span>
  </div>
  <div class="node-field">
    <label>Cooldown (ticks)</label>
    <input type="number" df-cooldownTicks value="0" min="0" class="node-input">
  </div>
</div>
```

**Preset button behavior** — clicking "Melee" sets: `damage=-10, range=15, cooldown=0`. "Ranged": `damage=-5, range=80, cooldown=0`. "Siege": `damage=-30, range=40, cooldown=60`.

**Ports:**
- Inputs: `attacker` (from Unit), `target` (from Unit or Faction), `damage_stat` (from Stat)
- No outputs

**Engine mapping:**
```javascript
// compileCombatNode(combatNode, connections) →
{
  source_faction: getFactionIdFromUnitConnection(combatNode.inputs.attacker),
  target_faction: getFactionIdFromConnection(combatNode.inputs.target),
  range: combatNode.data.range,
  effects: [{
    stat_index: getStatIndexFromConnection(combatNode.inputs.damage_stat) || 0,
    delta_per_second: combatNode.data.damage,
  }],
  cooldown_ticks: combatNode.data.cooldownTicks || null,
  // source_class, target_class — from connected Unit nodes (if available)
}
```

#### 2. Extend `relationship.js` — add visual feedback

When both inputs (`faction_a`, `faction_b`) are connected, show the two faction colors as dots with the relationship type icon between them.

#### 3. Extend `compiler.js`

Add compilation for:
- Combat nodes → `interaction.rules[]`
- Relationship nodes → `aggro[]` array with `set_aggro_mask` commands

**Relationship compilation:**
```javascript
// For each Relationship node:
const factionA = getConnectedFactionId(node, 'faction_a');
const factionB = getConnectedFactionId(node, 'faction_b');
const type = node.data.relationType;

if (type === 'hostile') {
  aggro.push({ source: factionA, target: factionB, allow_combat: true });
  aggro.push({ source: factionB, target: factionA, allow_combat: true });
} else {
  aggro.push({ source: factionA, target: factionB, allow_combat: false });
  aggro.push({ source: factionB, target: factionA, allow_combat: false });
}
```

### Verification Strategy
```
Test_Type: manual_steps
Test_Stack: Vite dev server
Acceptance_Criteria:
  - "Combat node renders with preset buttons"
  - "Clicking Melee/Ranged/Siege sets correct values"
  - "Combat node compiles to correct InteractionRule"
  - "Relationship node compiles to correct aggro_mask commands"
Manual_Steps:
  - "Build graph: Faction A → Unit A → Combat → Unit B ← Faction B"
  - "Add Relationship between A and B (Hostile)"
  - "Compile and verify WS commands contain interaction + aggro"
```

---

## Task 09: Navigation + Waypoint + Movement Nodes

**Model Tier:** `standard`
**Execution Phase:** 2 (Depends on T07)
**Live System Impact:** `safe`

### Target Files
- `debug-visualizer/src/node-editor/nodes/navigation.js` — [NEW]
- `debug-visualizer/src/node-editor/nodes/waypoint.js` — [NEW]
- `debug-visualizer/src/node-editor/nodes/movement.js` — [NEW]
- `debug-visualizer/src/node-editor/compiler.js` — MODIFY (add nav compilation)

### Context Bindings
- `context/project/conventions.md`
- `context/engine/navigation.md`
- `strategy_brief.md` — Sections "Navigation Node", "Waypoint Node", "Movement Node"

### Strict Instructions

#### 1. `nodes/navigation.js`

Minimal node — derived from connections. No user-configurable properties.

```html
<div class="node-header node-header--navigation">
  <span class="node-header__icon">{compassSVG}</span>
  <span>NAVIGATE</span>
</div>
<div class="node-body">
  <div class="node-hint">Connect follower faction and target</div>
</div>
```

**Ports:**
- Inputs: `follower` (from Faction), `target_faction` (from Faction), `waypoint` (from Waypoint)

**Compiler mapping:**
```javascript
{
  follower_faction: getConnectedFactionId(node, 'follower'),
  target: hasConnection(node, 'target_faction')
    ? { type: 'Faction', faction_id: getConnectedFactionId(node, 'target_faction') }
    : { type: 'Waypoint', x: getConnectedWaypoint(node, 'waypoint').x, y: ... }
}
```

#### 2. `nodes/waypoint.js`

```html
<div class="node-header node-header--waypoint">
  <span class="node-header__icon">{mapPinSVG}</span>
  <span>WAYPOINT</span>
</div>
<div class="node-body">
  <div class="node-field node-field--row">
    <div>
      <label>X</label>
      <input type="number" df-x value="500" class="node-input node-input--sm">
    </div>
    <div>
      <label>Y</label>
      <input type="number" df-y value="500" class="node-input node-input--sm">
    </div>
  </div>
</div>
```

**Ports:**
- Outputs: `position` (connects to Navigation's `waypoint` input)

**Future enhancement:** Click-on-map to set coordinates.

#### 3. `nodes/movement.js`

```html
<div class="node-header node-header--movement">
  <span class="node-header__icon">{moveSVG}</span>
  <span>MOVEMENT</span>
</div>
<div class="node-body">
  <div class="node-field">
    <label>Speed</label>
    <div class="node-preset-btns">
      <button class="node-preset-btn" data-preset="slow">🐢 Slow</button>
      <button class="node-preset-btn node-preset-btn--active" data-preset="normal">Normal</button>
      <button class="node-preset-btn" data-preset="fast">⚡ Fast</button>
    </div>
  </div>
  <div class="node-field">
    <label>Max Speed</label>
    <input type="number" df-maxSpeed value="100" class="node-input">
  </div>
  <div class="node-field">
    <label>Engagement Range</label>
    <input type="number" df-engagementRange value="15" class="node-input">
  </div>
</div>
```

**Ports:**
- Inputs: `unit` (from Unit node)

> [!WARNING]
> **Engine Gap:** Movement config data is compiled but NOT sent to the engine in Phase 1-2. The `spawn_wave` command does not accept `movement_config`. The node stores the data for future engine enhancement. The compiler should include it in the output but document that it is a no-op until the Rust `spawn_wave` handler is extended.

#### 4. Extend `compiler.js`

Add navigation rule compilation:
```javascript
// For each Navigation node without a General override:
navigation.rules.push({
  follower_faction: ...,
  target: ...
});
```

### Verification Strategy
```
Test_Type: manual_steps
Test_Stack: Vite dev server
Acceptance_Criteria:
  - "Navigation node connects Faction → Navigate → Faction (or Waypoint)"
  - "Waypoint node has X/Y inputs"
  - "Compiled navigation rules match expected format"
  - "Movement node stores speed config"
Manual_Steps:
  - "Build: Faction A → Navigate → Faction B (chase scenario)"
  - "Compile → verify set_navigation command"
  - "Build: Faction A → Navigate → Waypoint(800,800)"
  - "Compile → verify waypoint target"
```

---

## Task 10: Terrain + Sim Controls Overlay Panels

**Model Tier:** `standard`
**Execution Phase:** 2 (Depends on T07)
**Live System Impact:** `safe`

### Target Files
- `debug-visualizer/src/panels/playground/terrain-overlay.js` — [NEW]
- `debug-visualizer/src/panels/playground/sim-controls-overlay.js` — [NEW]
- `debug-visualizer/src/styles/playground-overlay.css` — [NEW]

### Context Bindings
- `context/project/conventions.md`
- `skills/frontend-ux-ui`

### Strict Instructions

These are **overlay card** versions of the existing terrain paint and sim controls panels, using the `overlay-card` CSS class from `overlay.css` instead of the sidebar accordion pattern.

#### 1. `terrain-overlay.js`

Exports a function that creates an overlay card for terrain painting:
```javascript
/**
 * Build and mount the terrain paint overlay card.
 * @param {HTMLElement} container — the bottom toolbar area
 */
export function mountTerrainOverlay(container) { ... }
```

Reuse the terrain painting logic from `controls/paint.js` and `panels/playground/terrain.js`. The overlay card contains:
- Brush selector (Wall / Mud / Pushable / Clear)
- Paint mode toggle button
- Clear all terrain button

Styled as a compact overlay card floating above the bottom toolbar when activated.

#### 2. `sim-controls-overlay.js`

Compact simulation controls:
- Play/Pause toggle
- Speed multiplier dropdown (1×, 2×, 5×, 10×)
- Step mode button (advance N ticks)
- Reset sim button

#### 3. `playground-overlay.css`

Styles specific to playground overlay panels:
- `.playground-bottom-toolbar` — fixed bottom, flex row, same glassmorphic bar as training
- Node add buttons — compact pill-shaped buttons
- Terrain/sim control popover positioning

### Verification Strategy
```
Test_Type: manual_steps
Test_Stack: Vite dev server
Acceptance_Criteria:
  - "Terrain paint mode activates from bottom toolbar"
  - "Sim controls (play/pause/speed) work"
  - "Overlay cards are glassmorphic, matching training page style"
```

---

## Task 11: General (Brain) Node — Phase 3

**Model Tier:** `advanced`
**Execution Phase:** 3 (Depends on T08, T09)
**Live System Impact:** `additive`

### Target Files
- `debug-visualizer/src/node-editor/nodes/general.js` — [NEW]
- `debug-visualizer/src/node-editor/brain-runner.js` — [NEW]
- `debug-visualizer/src/node-editor/compiler.js` — MODIFY (add brain phase)

### Context Bindings
- `context/project/conventions.md`
- `context/engine/architecture.md`
- `strategy_brief.md` — Section "General Node (Brain / AI Commander)"
- `implementation_plan.md` — Shared Contracts

### Strict Instructions

#### 1. `nodes/general.js`

```html
<div class="node-header node-header--general">
  <span class="node-header__icon">{brainSVG}</span>
  <span>GENERAL</span>
</div>
<div class="node-body">
  <div class="node-field">
    <label>Brain Model</label>
    <select df-brainModel class="node-select">
      <option value="">No Brain — Manual Mode</option>
      <option value="demo_aggressive">🔥 Aggressive</option>
      <option value="demo_defensive">🛡️ Defensive</option>
      <option value="custom">📁 Upload .onnx</option>
    </select>
  </div>
  <div class="node-field">
    <label>Decision Interval</label>
    <input type="range" df-decisionInterval min="10" max="60" value="30" class="node-slider">
    <span class="node-slider-value">30 ticks</span>
  </div>
  <div class="node-field">
    <label>Mode</label>
    <div class="node-toggle-group">
      <button class="node-toggle node-toggle--active" df-mode data-value="onnx">ONNX.js</button>
      <button class="node-toggle" df-mode data-value="zmq">Python ZMQ</button>
    </div>
  </div>
  <div class="node-status" id="brain-status">
    <span class="status-dot-inline status-dot-inline--wait"></span>
    <span class="node-mono-value">IDLE</span>
  </div>
</div>
```

**Ports:**
- Inputs: `faction` (from Faction's `general` output)

**Visual behavior:**
- When connected: Faction node shows a 🧠 badge
- Pulsing indicator when brain is actively issuing directives
- "No Brain — Manual Mode" in muted text when no model

#### 2. `brain-runner.js`

ONNX.js inference loop runner:

```javascript
/**
 * Start brain inference for a faction.
 * @param {Object} config — { factionId, modelPath, decisionInterval, mode }
 * @param {(cmd: string, params: object) => boolean} sendCommand
 * @returns {{ stop: () => void }}
 */
export function startBrainRunner(config, sendCommand) { ... }
```

**Runtime loop:**
```
Every config.decisionInterval ticks:
  1. Read latest ml_brain state from S.mlBrainStatus
  2. Build observation tensor (reuse state snapshot from WS tick payload)
  3. Run inference:
     - ONNX.js mode: ort.InferenceSession.create(modelPath) → session.run(feeds)
     - Python mode: Not implemented in this task (future)
  4. Decode action tensor → MacroDirective variant
  5. sendCommand('inject_directive', { directive: decodedDirective })
```

> [!IMPORTANT]
> **ONNX Runtime Web** must be added as a dependency: `npm i onnxruntime-web`. This is documented in the tech stack for Phase 5.

> [!WARNING]
> The engine currently hardcodes `brain_faction = 0`. For multi-brain playground scenarios, the observation data in `ml_brain` WS payload may not include data for other factions. This is a known limitation — document it as a Rust-side follow-up.

#### 3. Extend `compiler.js`

Add Phase 5 (Brain Init) to `executeScenario()`:
```javascript
// Phase 5: Brain Init
if (scenario.brains.length > 0) {
  for (const brain of scenario.brains) {
    const runner = startBrainRunner(brain, sendCommand);
    activeBrainRunners.push(runner);
  }
}
```

When a General node is connected to a Faction, **skip Navigation node compilation** for that faction:
```javascript
const factionHasGeneral = new Set(brainConfigs.map(b => b.factionId));
// Filter out nav rules for factions with generals
navigation.rules = navigation.rules.filter(r => !factionHasGeneral.has(r.follower_faction));
```

### Verification Strategy
```
Test_Type: manual_steps
Test_Stack: Vite dev server
Acceptance_Criteria:
  - "General node renders with model selector and decision interval"
  - "Connecting General to Faction dims/disables Navigation connections for that faction"
  - "With no model selected, compiles as normal (brain is no-op)"
  - "ONNX.js import resolves without error"
Manual_Steps:
  - "Add General node → connect to Faction A → compile → verify nav rules skip Faction A"
  - "Select 'Aggressive' demo model → Launch → verify inject_directive commands fire"
```
