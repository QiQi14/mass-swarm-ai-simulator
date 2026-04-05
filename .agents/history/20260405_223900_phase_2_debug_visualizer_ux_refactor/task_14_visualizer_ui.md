# Task 14 — Debug Visualizer UI: Spawn, Fog, Terrain, Scenario

## Metadata
- **Task_ID:** task_14_visualizer_ui
- **Execution_Phase:** Phase 3 (depends on Tasks 11, 12, 13)
- **Model_Tier:** advanced
- **Dependencies:**
  - Task 11 (Terrain affects flow field + movement)
  - Task 12 (VisibilitySync WS messages)
  - Task 13 (spawn_wave spread, set_terrain, save/load_scenario WS commands)
- **Context_Bindings:**
  - `implementation_plan.md` → All Features (UI sections)

## Target Files
- `debug-visualizer/index.html` — **MODIFY**
- `debug-visualizer/visualizer.js` — **MODIFY**
- `debug-visualizer/style.css` — **MODIFY**

## Contract: UI ↔ Rust WS Protocol

### Outgoing Commands (Browser → Rust)
```js
// Mass spawn with spread
sendCommand("spawn_wave", { faction_id: 0, amount: 500, x: 300, y: 400, spread: 50 });

// Terrain painting (batch)
sendCommand("set_terrain", { cells: [{ x: 5, y: 3, hard: 65535, soft: 0 }, ...] });
sendCommand("clear_terrain", {});

// Scenario I/O
sendCommand("save_scenario", {});
sendCommand("load_scenario", { terrain: {...}, entities: [...] });

// Fog control
sendCommand("set_fog_faction", { faction_id: 0 });   // Enable fog for faction 0
sendCommand("set_fog_faction", {});                    // Disable fog streaming
```

### Incoming Messages (Rust → Browser)
```js
// VisibilitySync (every 6th tick) — within SyncDelta
{
  type: "SyncDelta",
  tick: 360,
  moved: [...],
  removed: [...],
  telemetry: {...},
  visibility: {                      // NEW
    faction_id: 0,
    grid_width: 50,
    grid_height: 50,
    explored: [u32, u32, ...],       // 79 integers, bit-packed
    visible: [u32, u32, ...],        // 79 integers, bit-packed
  }
}

// Scenario data response
{ type: "scenario_data", terrain: {...}, entities: [...] }
```

### Brush-to-Cost Mapping (UI-Only)
```js
const BRUSH_MAP = {
    wall:     { hard: 65535, soft: 0,   color: '#1a1a2e',  label: 'Wall' },
    mud:      { hard: 200,   soft: 30,  color: '#8b6914',  label: 'Mud' },
    pushable: { hard: 125,   soft: 50,  color: '#d4790e',  label: 'Pushable' },
    clear:    { hard: 100,   soft: 100, color: null,        label: 'Clear' },
};
```

## Strict Instructions

### 1. Modify `index.html`

**a. Add Spawn Tools section** (between "Simulation Controls" and "Faction Behavior"):
```html
<section class="panel-section">
    <h2>Spawn Tools</h2>
    <div class="spawn-controls">
        <div class="spawn-row">
            <label class="spawn-label">Faction</label>
            <select id="spawn-faction" class="input-field"></select>
        </div>
        <div class="spawn-row">
            <label class="spawn-label">Amount</label>
            <input type="range" id="spawn-amount-slider" min="1" max="500" value="50" class="slider">
            <input type="number" id="spawn-amount" class="input-field compact" value="50" min="1" max="10000">
        </div>
        <div class="spawn-row">
            <label class="spawn-label">Spread</label>
            <input type="range" id="spawn-spread-slider" min="0" max="100" value="20" class="slider">
            <input type="number" id="spawn-spread" class="input-field compact" value="20" min="0" max="200">
        </div>
    </div>
</section>
```

**b. Replace fog toggle** — Replace single `toggle-fog` checkbox with per-faction toggles. Use radio-like behavior (only one active). Dynamically populated from `ADAPTER_CONFIG.factions`.

**c. Add Terrain Editor section:**
```html
<section class="panel-section">
    <h2>Terrain Editor</h2>
    <div class="controls-row">
        <button id="paint-mode-btn" class="btn secondary">🖌 Paint Mode</button>
    </div>
    <div id="brush-tools" class="brush-toolbar" style="display: none;">
        <button class="brush-btn active" data-brush="wall">⬛ Wall</button>
        <button class="brush-btn" data-brush="mud">🟫 Mud</button>
        <button class="brush-btn" data-brush="pushable">🟧 Pushable</button>
        <button class="brush-btn" data-brush="clear">⬜ Clear</button>
    </div>
    <div class="controls-row" style="margin-top: 8px;">
        <button id="save-scenario-btn" class="btn secondary">💾 Save</button>
        <button id="load-scenario-btn" class="btn secondary">📂 Load</button>
        <input type="file" id="scenario-file-input" accept=".json" style="display:none">
    </div>
    <button id="clear-terrain-btn" class="btn secondary" style="margin-top:4px">🗑 Clear All Terrain</button>
</section>
```

### 2. Modify `visualizer.js`

**a. Spawn controls:**
- Populate `spawn-faction` dropdown from `ADAPTER_CONFIG.factions`
- Sync slider ↔ number inputs bidirectionally
- On canvas click (when NOT in paint mode): read faction/amount/spread from controls, send `spawn_wave`
- Show ghost circle at cursor (radius = spread) while hovering canvas (use canvas overlay or requestAnimationFrame)

**b. Terrain painting:**
- Track state: `let paintMode = false;`, `let activeBrush = 'wall';`
- Toggle paint mode: show/hide brush toolbar, change canvas cursor to `crosshair`
- On mousedown in paint mode: start collecting cells
- On mousemove while mousedown: calculate grid cell from mouse position, add to batch array, draw preview immediately
- On mouseup: send `set_terrain` command with all collected cells
- Render terrain on `#canvas-bg` (or a new canvas layer): iterate grid, draw colored cells for non-clear terrain
- Track terrain state locally: `const terrainLocal = new Uint16Array(GRID_W * GRID_H * 2)` (hard + soft interleaved)

**c. Fog of war rendering:**
- Receive `visibility` field from SyncDelta
- Store received explored/visible bit-packed arrays
- Bit-unpacking helper: `function getBit(arr, idx) { return (arr[idx >> 5] >> (idx & 31)) & 1; }`
- Create offscreen canvas same size as main canvas
- Draw fog: fill with rgba(0,0,0,1), then for each cell:
  - If visible: punch fully transparent circle/rect
  - If explored-only: punch semi-transparent (50% alpha)
  - Unexplored: stays black
- Composite offscreen canvas onto main canvas AFTER entity rendering
- On fog toggle change: send `set_fog_faction` command to Rust

**d. Scenario save/load:**
- Save: send `save_scenario` command, listen for `scenario_data` response, trigger browser download as `.json`
- Load: file input → parse JSON → send `load_scenario` command + update local terrain state

**e. Remove the old `drawFog()` function** (replace entirely with new fog renderer).

### 3. Modify `style.css`

Add styles for:
- `.spawn-controls`, `.spawn-row`, `.spawn-label` — compact layout
- `.brush-toolbar`, `.brush-btn`, `.brush-btn.active` — horizontal button group
- `.slider` — styled range input
- `.compact` input fields (width: 60px)
- Paint mode cursor: `canvas.paint-mode { cursor: crosshair; }`
- Ghost spawn circle preview styling

## Verification Strategy

**Test_Type:** manual_steps + browser
**Test_Stack:** Browser-based verification

**Manual Steps:**
1. Open `http://127.0.0.1:3000` in browser
2. **Spawn:** Set amount=200, faction=Defender(1), spread=50 → click canvas → 200 blue dots appear in spiral
3. **Terrain paint:** Click "Paint Mode" → select "Wall" brush → drag on canvas → black cells appear → flow field reroutes
4. **Pushable terrain:** Select "Pushable" brush → paint area → entities slow down when crossing
5. **Fog of war:** Toggle "Swarm Fog" → black overlay appears, vision circles around red entities
6. **Save scenario:** Click Save → JSON file downloads → contains terrain + entity data
7. **Load scenario:** Reload page → click Load → select saved JSON → terrain + entities restored
8. **Clear terrain:** Click "Clear All Terrain" → all terrain removed

**Commands:**
```bash
./dev.sh  # Start environment, then test manually in browser
```
