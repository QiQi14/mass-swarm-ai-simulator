# Task 04: JS Visualizer — WS Client + Render Engine + Interactions

Task_ID: task_04_js_visualizer
Execution_Phase: B
Model_Tier: standard

## Target_Files
- `debug-visualizer/visualizer.js` [NEW]

## Dependencies
- Task 01 (DOM element IDs — see DOM ID Contract below)
- Task 03 (WS protocol: SyncDelta with velocity, command schema)

## Context_Bindings
- context/ipc-protocol
- context/conventions

## Strict_Instructions

Create `debug-visualizer/visualizer.js` — the complete JavaScript application.

### DOM ID Contract (from Task 01)

These IDs MUST exist in the HTML. Reference them via `document.getElementById()`:

```
Canvas:          sim-canvas
Telemetry:       stat-tps, stat-ping, stat-ai-latency, stat-entities, stat-swarm, stat-defender, stat-tick
Controls:        play-pause-btn, step-btn, step-count-input
Layer toggles:   toggle-grid, toggle-velocity, toggle-fog
Connection:      status-dot, status-text
```

### WS Message Schema (from Task 03)

**Incoming (Server → Browser):**
```json
{
  "type": "SyncDelta",
  "tick": 1234,
  "moved": [
    { "id": 1, "x": 150.3, "y": 200.1, "dx": 0.5, "dy": -0.3, "team": "swarm" },
    { "id": 2, "x": 400.0, "y": 300.5, "dx": -0.1, "dy": 0.7, "team": "defender" }
  ]
}
```

**Outgoing (Browser → Server) — Command schema:**
```json
{ "type": "command", "cmd": "toggle_sim", "params": {} }
{ "type": "command", "cmd": "step", "params": { "count": 1 } }
{ "type": "command", "cmd": "spawn_wave", "params": { "team": "swarm", "amount": 10, "x": 500.0, "y": 500.0 } }
{ "type": "command", "cmd": "set_speed", "params": { "multiplier": 2.0 } }
{ "type": "command", "cmd": "kill_all", "params": { "team": "swarm" } }
```

---

### 1. Constants

```javascript
const WS_URL = "ws://127.0.0.1:8080";
const WORLD_WIDTH = 1000.0;
const WORLD_HEIGHT = 1000.0;
const GRID_DIVISIONS = 100;
const ENTITY_RADIUS = 3;
const RECONNECT_INTERVAL_MS = 2000;
const VELOCITY_VECTOR_SCALE = 15; // pixel length multiplier for velocity lines
```

### 2. State

```javascript
const entities = new Map();  // Map<id, { x, y, dx, dy, team }>
let currentTick = 0;
let ws = null;
let isPaused = false;

// View transform (pan/zoom)
let viewX = WORLD_WIDTH / 2;
let viewY = WORLD_HEIGHT / 2;
let viewScale = 1.0;

// Layer visibility
let showGrid = true;       // Reads initial state from toggle-grid checkbox
let showVelocity = false;  // Reads from toggle-velocity
let showFog = false;       // Reads from toggle-fog

// Telemetry
let lastTickTime = 0;
let tpsCounter = 0;
let currentTps = 0;
```

### 3. Canvas Setup

- Get canvas and 2D context
- `resizeCanvas()`: set `canvas.width/height` to match `clientWidth/clientHeight`
- Listen to `window.resize` event
- Call `resizeCanvas()` on init

### 4. Coordinate Transforms

- `worldToCanvas(wx, wy)` → `[cx, cy]`: maps world coordinates to canvas pixels using viewX, viewY, viewScale
- `canvasToWorld(cx, cy)` → `[wx, wy]`: inverse for click-to-spawn
- Scale factor: `Math.min(canvas.width, canvas.height) / WORLD_WIDTH * viewScale`

### 5. WebSocket Client

- `connectWebSocket()`: create `new WebSocket(WS_URL)`
- `onopen`: set connection status to "connected", clear entity buffer
- `onmessage`: parse JSON, handle `SyncDelta`:
  - Update `currentTick`
  - For each entity in `moved`: `entities.set(id, { x, y, dx, dy, team })`
  - Compute TPS: count SyncDelta messages per second
  - Update telemetry displays
- `onclose`: set status "disconnected", schedule reconnect after `RECONNECT_INTERVAL_MS`
- `onerror`: no-op (onclose handles reconnect)

Connection status display: update `status-dot` class and `status-text` content.

### 6. Render Loop (`requestAnimationFrame`)

```
renderFrame():
  1. Clear canvas
  2. Fill background (dark color)
  3. If showGrid: drawGrid() — 100×100 grid, major lines every 10 cells
  4. drawEntities() — for each entity in Map:
     - worldToCanvas(x, y) → canvas position
     - Skip if outside visible canvas (frustum culling)
     - Draw filled circle: team color (swarm=red-ish, defender=blue-ish)
     - If showVelocity: draw line from entity center in (dx, dy) direction
  5. If showFog: drawFog() — semi-transparent overlay (placeholder, basic implementation)
  6. Update FPS counter
  7. requestAnimationFrame(renderFrame)
```

Entity colors: use distinct colors for swarm vs defender. Choose any specific hex values that look good on dark background.

### 7. Pan/Zoom

- **Pan**: mousedown → track start position; mousemove → update viewX/viewY; mouseup → stop
- **Zoom**: wheel event → multiply viewScale by factor (e.g., 1.1); zoom toward cursor position; clamp viewScale (0.5–20.0)
- **Reset**: double-click → reset viewX, viewY, viewScale to defaults

### 8. Click to Spawn

- Canvas `click` event (when NOT dragging):
  - Convert click position to world coordinates via `canvasToWorld()`
  - Send `spawn_wave` command with `{ team: "swarm", amount: 10, x, y }`
  - Distinguish click from drag: only spawn if mouse didn't move significantly between mousedown and mouseup

### 9. Control Panel Handlers

```javascript
// Play/Pause toggle
getElementById("play-pause-btn").onclick = () => {
    isPaused = !isPaused;
    sendCommand("toggle_sim");
    // Update button text/icon
};

// Step
getElementById("step-btn").onclick = () => {
    const count = parseInt(getElementById("step-count-input").value) || 1;
    sendCommand("step", { count });
};

// Layer toggles
getElementById("toggle-grid").onchange = (e) => { showGrid = e.target.checked; };
getElementById("toggle-velocity").onchange = (e) => { showVelocity = e.target.checked; };
getElementById("toggle-fog").onchange = (e) => { showFog = e.target.checked; };
```

### 10. Command Sender

```javascript
function sendCommand(cmd, params = {}) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "command", cmd, params }));
    }
}
```

### 11. Telemetry Updates

- **TPS**: Count ticks received per second (compare `currentTick` deltas), update `stat-tps`
- **WS Ping**: Measure time between sending and receiving (or just show "< 1ms" for localhost), update `stat-ping`
- **AI Latency**: Show "N/A" for now (no data source yet), update `stat-ai-latency`
- **Entity counts**: Count from entity Map, update `stat-entities`, `stat-swarm`, `stat-defender`
- **Tick**: Update `stat-tick` with `currentTick`
- **FPS**: Count render frames per second

### 12. Initialization

```javascript
resizeCanvas();
connectWebSocket();
requestAnimationFrame(renderFrame);
```

## Verification_Strategy
  Test_Type: manual_steps + integration
  Acceptance_Criteria:
    - "Without Micro-Core: shows 'Disconnected', auto-retries every 2s"
    - "With Micro-Core: 'Connected', entities render as colored dots, tick counter increments"
    - "Pan (drag) and zoom (scroll wheel) work on canvas"
    - "Double-click resets view"
    - "Grid overlay toggles on/off via checkbox"
    - "Velocity vector toggle shows/hides direction lines on entities"
    - "Click on canvas spawns entities at that position"
    - "Play/Pause button sends toggle_sim command"
    - "Step button sends step command with count from input"
    - "TPS counter shows simulation tick rate"
    - "Entity counts in telemetry match simulation"
  Manual_Steps:
    - "Open index.html without Micro-Core → verify Disconnected"
    - "Start cargo run → verify rendering and telemetry"
    - "Test pan/zoom/reset"
    - "Toggle grid off/on"
    - "Enable velocity vectors → verify direction lines"
    - "Click canvas → verify entities spawn at click position"
    - "Click Play/Pause → verify simulation toggles"
    - "Enter step count, click Step → verify single-step advance"
    - "Stop cargo run → verify reconnect"
