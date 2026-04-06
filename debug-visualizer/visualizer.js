// Constants
const WS_URL = "ws://127.0.0.1:8080";
const WORLD_WIDTH = 1000.0;
const WORLD_HEIGHT = 1000.0;
const GRID_DIVISIONS = 100;
const ENTITY_RADIUS = 3;
const RECONNECT_INTERVAL_MS = 2000;
const VELOCITY_VECTOR_SCALE = 15;
const GRID_W = 50;
const GRID_H = 50;
const TERRAIN_CELL_SIZE = 20;

const BRUSH_MAP = {
    wall:     { hard: 65535, soft: 0,   color: '#1a1a2e',  label: 'Wall' },
    mud:      { hard: 200,   soft: 30,  color: '#8b6914',  label: 'Mud' },
    pushable: { hard: 125,   soft: 50,  color: '#d4790e',  label: 'Pushable' },
    clear:    { hard: 100,   soft: 100, color: null,        label: 'Clear' },
};

// Adapter Config
const ADAPTER_CONFIG = {
    factions: {
        0: { name: "Swarm",    color: "#ff3b30" },
        1: { name: "Defender", color: "#0a84ff" },
    },
    stats: {
        0: { name: "Health", display: "bar", color_low: "#ff3b30", color_high: "#30d158" },
    },
};

// State
const entities = new Map();  // Map<id, { x, y, dx, dy, faction_id, stats }>
const flowFieldCache = new Map(); // Map<factionId, { gridW, gridH, cellSize, vectors }>
const deathAnimations = [];
let selectedEntityId = null;
let paintMode = false;
let spawnMode = false;
let activeBrush = 'wall';
let nextFactionId = 2; // 0 and 1 already exist
const terrainLocal = new Uint16Array(GRID_W * GRID_H * 2);
for (let i = 0; i < terrainLocal.length; i++) terrainLocal[i] = 100;

let fogVisible = null;
let fogExplored = null;
let activeFogFaction = null;

let currentTick = 0;
let ws = null;
let isPaused = false;

// View transform (pan/zoom)
let viewX = WORLD_WIDTH / 2;
let viewY = WORLD_HEIGHT / 2;
let viewScale = 1.0;

// Layer visibility
let showGrid = document.getElementById("toggle-grid").checked;
let showSpatialGrid = document.getElementById("toggle-spatial-grid").checked;
let showFlowField = document.getElementById("toggle-flow-field").checked;
let showVelocity = document.getElementById("toggle-velocity").checked;
let showDensityHeatmap = document.getElementById("toggle-density-heatmap").checked;
let showZoneModifiers = document.getElementById("toggle-zone-modifiers").checked;
let showOverrideMarkers = document.getElementById("toggle-override-markers").checked;
let showFog = false; // Adjusted via dynamic toggles

// Phase 3 state
let zoneModifiers = null;
let activeSubFactions = [];
let aggroMasks = [];
let densityHeatmap = null;
let mlBrainStatus = null;
let zoneMode = false;
let splitMode = false;
let activeZoneType = 'attract';

// Telemetry
let lastTickTime = performance.now();
let tpsCounter = 0;
let currentTps = 0;
let lastFpsTime = performance.now();
let frames = 0;
let currentFps = 0;
let currentPing = 0;

// DOM Elements
const bgCanvas = document.getElementById("canvas-bg");
const bgCtx = bgCanvas.getContext("2d");
const canvasEntities = document.getElementById("canvas-entities");
const ctx = canvasEntities.getContext("2d");

const statTps = document.getElementById("stat-tps");
const statTick = document.getElementById("stat-tick");
const statEntities = document.getElementById("stat-entities");
const statSwarm = document.getElementById("stat-swarm");
const statDefender = document.getElementById("stat-defender");

const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");

const playPauseBtn = document.getElementById("play-pause-btn");
const stepBtn = document.getElementById("step-btn");
const stepCountInput = document.getElementById("step-count-input");

const toggleGrid = document.getElementById("toggle-grid");
const toggleSpatialGrid = document.getElementById("toggle-spatial-grid");
const toggleFlowField = document.getElementById("toggle-flow-field");
const toggleVelocity = document.getElementById("toggle-velocity");
const toggleDensityHeatmap = document.getElementById("toggle-density-heatmap");
const toggleZoneModifiers = document.getElementById("toggle-zone-modifiers");
const toggleOverrideMarkers = document.getElementById("toggle-override-markers");
const fogTogglesContainer = document.getElementById("fog-toggles-container");

// Phase 3 UI Elements
const zoneModeBtn = document.getElementById("zone-mode-btn");
const zoneTools = document.getElementById("zone-tools");
const zoneHint = document.getElementById("zone-hint");
const zoneFaction = document.getElementById("zone-faction");
const zoneRadiusSlider = document.getElementById("zone-radius-slider");
const zoneRadius = document.getElementById("zone-radius");
const zoneIntensitySlider = document.getElementById("zone-intensity-slider");
const zoneIntensity = document.getElementById("zone-intensity");
const zoneDuration = document.getElementById("zone-duration");
const zoneTypeBtns = document.querySelectorAll(".zone-type-btn");

const splitModeBtn = document.getElementById("split-mode-btn");
const splitTools = document.getElementById("split-tools");
const splitHint = document.getElementById("split-hint");
const splitSourceFaction = document.getElementById("split-source-faction");
const splitPctSlider = document.getElementById("split-pct-slider");
const splitPct = document.getElementById("split-pct");

const spawnFaction = document.getElementById("spawn-faction");
const spawnAmountSlider = document.getElementById("spawn-amount-slider");
const spawnAmount = document.getElementById("spawn-amount");
const spawnSpreadSlider = document.getElementById("spawn-spread-slider");
const spawnSpread = document.getElementById("spawn-spread");

const paintModeBtn = document.getElementById("paint-mode-btn");
const brushTools = document.getElementById("brush-tools");
const brushBtns = document.querySelectorAll(".brush-btn");
const saveScenarioBtn = document.getElementById("save-scenario-btn");
const loadScenarioBtn = document.getElementById("load-scenario-btn");
const scenarioFileInput = document.getElementById("scenario-file-input");
const clearTerrainBtn = document.getElementById("clear-terrain-btn");
const spawnModeBtn = document.getElementById("spawn-mode-btn");
const spawnHint = document.getElementById("spawn-hint");
const addFactionBtn = document.getElementById("add-faction-btn");
const deleteFactionBtn = document.getElementById("delete-faction-btn");

// Colors
const COLOR_BG = "#0f1115";
const COLOR_GRID = "rgba(255, 255, 255, 0.05)";
const COLOR_GRID_MAJOR = "rgba(255, 255, 255, 0.15)";
const COLOR_VELOCITY = "rgba(255, 255, 255, 0.5)";
const COLOR_FOG = "rgba(0, 0, 0, 0.6)";

// --- Classes ---

class Sparkline {
    constructor(canvasId, maxSamples = 60, color = '#30d158') {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.samples = [];
        this.maxSamples = maxSamples;
        this.color = color;
    }

    push(value) {
        this.samples.push(value);
        if (this.samples.length > this.maxSamples) this.samples.shift();
    }

    draw() {
        const { canvas, ctx, samples, color } = this;
        const w = canvas.width, h = canvas.height;
        ctx.clearRect(0, 0, w, h);
        if (samples.length < 2) return;

        const max = Math.max(...samples, 1);
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        for (let i = 0; i < samples.length; i++) {
            const x = (i / (this.maxSamples - 1)) * w;
            const y = h - (samples[i] / max) * (h - 2);
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.stroke();
    }
}

const sparklines = {
    tps: new Sparkline('graph-tps', 60, '#30d158'),
    entities: new Sparkline('graph-entities', 60, '#0a84ff'),
};

// --- Canvas Setup ---

function resizeCanvas() {
    bgCanvas.width = bgCanvas.clientWidth;
    bgCanvas.height = bgCanvas.clientHeight;
    canvasEntities.width = canvasEntities.clientWidth;
    canvasEntities.height = canvasEntities.clientHeight;
    drawBackground();
}
window.addEventListener("resize", resizeCanvas);

// --- Coordinate Transforms ---

function getScaleFactor() {
    return Math.min(canvasEntities.width, canvasEntities.height) / Math.max(WORLD_WIDTH, WORLD_HEIGHT) * viewScale;
}

function worldToCanvas(wx, wy) {
    const scale = getScaleFactor();
    const cx = (wx - viewX) * scale + canvasEntities.width / 2;
    const cy = (wy - viewY) * scale + canvasEntities.height / 2;
    return [cx, cy];
}

function canvasToWorld(cx, cy) {
    const scale = getScaleFactor();
    const wx = (cx - canvasEntities.width / 2) / scale + viewX;
    const wy = (cy - canvasEntities.height / 2) / scale + viewY;
    return [wx, wy];
}

// --- WebSocket Client ---

function connectWebSocket() {
    console.log("Connecting to WS...", WS_URL);
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
        statusDot.className = "dot connected";
        statusText.textContent = "Connected";
        entities.clear();
        flowFieldCache.clear();
        currentTick = 0;
        currentPing = 0;
        initFactionToggles();
    };

    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            if (msg.type === "SyncDelta") {
                if (msg.tick) {
                    if (msg.tick > currentTick) {
                        tpsCounter += (msg.tick - currentTick);
                    }
                    currentTick = msg.tick;
                }
                
                if (msg.moved) {
                    for (const diff of msg.moved) {
                        const existing = entities.get(diff.id) || { faction_id: 0, stats: [] };
                        entities.set(diff.id, {
                            ...existing,
                            x: diff.x !== undefined ? diff.x : existing.x,
                            y: diff.y !== undefined ? diff.y : existing.y,
                            dx: diff.dx !== undefined ? diff.dx : existing.dx,
                            dy: diff.dy !== undefined ? diff.dy : existing.dy,
                            faction_id: diff.faction_id !== undefined ? diff.faction_id : existing.faction_id,
                            stats: diff.stats !== undefined ? diff.stats : existing.stats
                        });
                    }
                }

                if (msg.removed) {
                    for (const id of msg.removed) {
                        addDeathAnimation(id);
                    }
                }

                if (msg.telemetry) {
                    updatePerfBars(msg.telemetry);
                }
                if (msg.visibility) {
                    activeFogFaction = msg.visibility.faction_id;
                    fogExplored = new Uint32Array(msg.visibility.explored);
                    fogVisible = new Uint32Array(msg.visibility.visible);
                }
                if (msg.zone_modifiers !== undefined) zoneModifiers = msg.zone_modifiers;
                if (msg.active_sub_factions !== undefined) {
                    activeSubFactions = msg.active_sub_factions;
                    updateLegend(activeSubFactions);
                }
                if (msg.aggro_masks !== undefined) {
                    aggroMasks = msg.aggro_masks;
                    updateAggroGrid(aggroMasks, Object.keys(ADAPTER_CONFIG.factions));
                }
                if (msg.ml_brain !== undefined) {
                    mlBrainStatus = msg.ml_brain;
                    updateMlBrainPanel(mlBrainStatus);
                }
                if (msg.density_heatmap !== undefined) densityHeatmap = msg.density_heatmap;
            } else if (msg.type === "FlowFieldSync") {
                handleFlowFieldSync(msg);
            } else if (msg.type === "scenario_data") {
                const blob = new Blob([JSON.stringify(msg, null, 2)], { type: "application/json" });
                const a = document.createElement("a");
                a.href = URL.createObjectURL(blob);
                a.download = "scenario.json";
                a.click();
            }
        } catch (e) {
            console.error("Failed to parse WS message", e);
        }
    };

    ws.onclose = () => {
        statusDot.className = "dot disconnected";
        statusText.textContent = "Disconnected";
        setTimeout(connectWebSocket, RECONNECT_INTERVAL_MS);
    };

    ws.onerror = () => {
        console.warn("WebSocket error occurred.");
    };
}

function sendCommand(cmd, params = {}) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "command", cmd, params }));
        return true;
    }
    return false;
}

function showToast(message, type = 'info') {
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

// --- Interaction / Controls ---

let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;
let viewStartDragX = 0;
let viewStartDragY = 0;
let hasDragged = false;
let isPainting = false;
let paintCellsBatch = [];
let mouseWorldX = null;
let mouseWorldY = null;

canvasEntities.addEventListener("mousedown", (e) => {
    if (paintMode) {
        isPainting = true;
        paintCellsBatch = [];
        // Apply instantly to the first cell
        const rect = canvasEntities.getBoundingClientRect();
        const [wx, wy] = canvasToWorld(e.clientX - rect.left, e.clientY - rect.top);
        addPaintCell(wx, wy);
        return;
    }
    isDragging = true;
    hasDragged = false;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    viewStartDragX = viewX;
    viewStartDragY = viewY;

    // Wait until mouseup or checking drag to perform click actions
});

function addPaintCell(wx, wy) {
    const cx = Math.floor(wx / TERRAIN_CELL_SIZE);
    const cy = Math.floor(wy / TERRAIN_CELL_SIZE);
    if (cx >= 0 && cy >= 0 && cx < GRID_W && cy < GRID_H) {
        const brush = BRUSH_MAP[activeBrush] || BRUSH_MAP.wall;
        // avoid duplicates if we want, but Rust core should handle
        paintCellsBatch.push({ x: cx, y: cy, hard: brush.hard, soft: brush.soft });
        // local prediction
        terrainLocal[(cy * GRID_W + cx) * 2] = brush.hard;
        terrainLocal[(cy * GRID_W + cx) * 2 + 1] = brush.soft;
        drawBackground();
    }
}

window.addEventListener("mousemove", (e) => {
    if (e.target === canvasEntities) {
        const rect = canvasEntities.getBoundingClientRect();
        const [wx, wy] = canvasToWorld(e.clientX - rect.left, e.clientY - rect.top);
        mouseWorldX = wx;
        mouseWorldY = wy;
        if (paintMode && isPainting) {
            addPaintCell(wx, wy);
            return;
        }
    } else {
        mouseWorldX = null;
        mouseWorldY = null;
    }

    if (isDragging) {
        const dx = e.clientX - dragStartX;
        const dy = e.clientY - dragStartY;
        
        if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
            hasDragged = true;
        }

        const scale = getScaleFactor();
        viewX = viewStartDragX - dx / scale;
        viewY = viewStartDragY - dy / scale;
        drawBackground();
    }
});

window.addEventListener("mouseup", (e) => {
    if (paintMode && isPainting) {
        isPainting = false;
        if (paintCellsBatch.length > 0) {
            sendCommand("set_terrain", { cells: paintCellsBatch });
        }
        return;
    }

    if (isDragging && !hasDragged && e.target === canvasEntities) {
        const rect = canvasEntities.getBoundingClientRect();
        const [wx, wy] = canvasToWorld(e.clientX - rect.left, e.clientY - rect.top);
    
        if (spawnMode) {
            // --- SPAWN MODE: Click always spawns ---
            const faction_id = parseInt(spawnFaction.value);
            if (isNaN(faction_id)) {
                showToast('Select a faction first', 'warn');
                isDragging = false;
                return;
            }
            const amount = parseInt(spawnAmount.value) || 50;
            const spread = parseFloat(spawnSpread.value) || 30;
            const ok = sendCommand("spawn_wave", { faction_id, amount, x: wx, y: wy, spread });
            if (ok) {
                const fName = ADAPTER_CONFIG.factions[faction_id]?.name || `Faction ${faction_id}`;
                showToast(`Spawned ${amount} ${fName} units`, 'success');
            } else {
                showToast('Not connected to server', 'error');
            }
        } else if (zoneMode) {
            // --- ZONE MODE: Place zone modifier ---
            const faction_id = parseInt(zoneFaction.value);
            if (isNaN(faction_id)) {
                showToast('Select a faction first', 'warn');
                isDragging = false;
                return;
            }
            const ok = sendCommand("place_zone_modifier", {
                target_faction: faction_id,
                x: wx,
                y: wy,
                radius: parseFloat(zoneRadius.value) || 100,
                cost_modifier: (activeZoneType === 'attract' ? -1 : 1) * (parseFloat(zoneIntensity.value) || 50),
                duration_ticks: parseInt(zoneDuration.value) || 300
            });
            if (ok) showToast('Placed zone modifier', 'success');
        } else if (splitMode) {
            // --- SPLIT MODE: Split faction ---
            const source_faction = parseInt(splitSourceFaction.value);
            if (isNaN(source_faction)) {
                showToast('Select a source faction', 'warn');
                isDragging = false;
                return;
            }
            let new_sub_faction = (source_faction + 1) * 100;
            while(activeSubFactions && activeSubFactions.includes(new_sub_faction)) new_sub_faction++;

            const ok = sendCommand("split_faction", {
                source_faction,
                new_sub_faction,
                percentage: (parseFloat(splitPct.value) || 30) / 100.0,
                epicenter_x: wx,
                epicenter_y: wy
            });
            if (ok) {
                showToast(`Split command sent (epicenter: ${Math.round(wx)}, ${Math.round(wy)})`, 'success');
                // Auto exit mode
                splitModeBtn.click();
            }
        } else {
            // --- SELECT MODE: Click selects nearest entity ---
            let bestDist = Infinity;
            let bestId = null;
            for (const [id, ent] of entities) {
                const dx = ent.x - wx, dy = ent.y - wy;
                const dist = dx * dx + dy * dy;
                if (dist < bestDist) {
                    bestDist = dist;
                    bestId = id;
                }
            }
        
            if (bestId !== null && bestDist < 100) { 
                selectedEntityId = bestId;
                updateInspectorPanel();
                document.getElementById('inspector-panel').style.display = 'block';
            } else {
                deselectEntity();
            }
        }
    }
    isDragging = false;
});

canvasEntities.addEventListener("wheel", (e) => {
    e.preventDefault();
    const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
    
    // Zoom toward mouse pointer logic
    const rect = canvasEntities.getBoundingClientRect();
    const cx = e.clientX - rect.left;
    const cy = e.clientY - rect.top;
    
    const [wxBefore, wyBefore] = canvasToWorld(cx, cy);
    
    viewScale = Math.max(0.5, Math.min(20.0, viewScale * zoomFactor));
    
    const [wxAfter, wyAfter] = canvasToWorld(cx, cy);
    
    viewX += (wxBefore - wxAfter);
    viewY += (wyBefore - wyAfter);
    drawBackground();
});

canvasEntities.addEventListener("dblclick", () => {
    viewX = WORLD_WIDTH / 2;
    viewY = WORLD_HEIGHT / 2;
    viewScale = 1.0;
    drawBackground();
});


document.getElementById('insp-deselect').addEventListener('click', deselectEntity);

function deselectEntity() {
    selectedEntityId = null;
    document.getElementById('inspector-panel').style.display = 'none';
}

function updateInspectorPanel() {
    if (selectedEntityId === null) return;
    const ent = entities.get(selectedEntityId);
    if (!ent) { deselectEntity(); return; }

    const factionName = ADAPTER_CONFIG.factions[ent.faction_id]?.name || `Faction ${ent.faction_id}`;
    document.getElementById('insp-id').textContent = selectedEntityId;
    document.getElementById('insp-faction').textContent = factionName;
    document.getElementById('insp-pos').textContent = `(${ent.x.toFixed(1)}, ${ent.y.toFixed(1)})`;
    document.getElementById('insp-vel').textContent = `(${ent.dx.toFixed(2)}, ${ent.dy.toFixed(2)})`;
    document.getElementById('insp-stats').textContent = (ent.stats || []).map(s => s.toFixed(2)).join(', ');
}

// UI Control bindings
playPauseBtn.onclick = () => {
    isPaused = !isPaused;
    sendCommand("toggle_sim");
    playPauseBtn.textContent = isPaused ? "Resume" : "Pause";
};

stepBtn.onclick = () => {
    const count = parseInt(stepCountInput.value) || 1;
    sendCommand("step", { count });
};

// Map toggles to variables
toggleGrid.onchange = (e) => { showGrid = e.target.checked; drawBackground(); };
toggleSpatialGrid.onchange = (e) => { showSpatialGrid = e.target.checked; drawBackground(); };
toggleFlowField.onchange = (e) => { showFlowField = e.target.checked; drawBackground(); };
toggleVelocity.onchange = (e) => { showVelocity = e.target.checked; };
toggleDensityHeatmap.onchange = (e) => { showDensityHeatmap = e.target.checked; };
toggleZoneModifiers.onchange = (e) => { showZoneModifiers = e.target.checked; };
toggleOverrideMarkers.onchange = (e) => { showOverrideMarkers = e.target.checked; };

// Sync range and number inputs
spawnAmountSlider.oninput = (e) => spawnAmount.value = e.target.value;
spawnAmount.oninput = (e) => spawnAmountSlider.value = e.target.value;
spawnSpreadSlider.oninput = (e) => spawnSpread.value = e.target.value;
spawnSpread.oninput = (e) => spawnSpreadSlider.value = e.target.value;
zoneRadiusSlider.oninput = (e) => zoneRadius.value = e.target.value;
zoneRadius.oninput = (e) => zoneRadiusSlider.value = e.target.value;
zoneIntensitySlider.oninput = (e) => zoneIntensity.value = e.target.value;
zoneIntensity.oninput = (e) => zoneIntensitySlider.value = e.target.value;
splitPctSlider.oninput = (e) => splitPct.value = e.target.value;
splitPct.oninput = (e) => splitPctSlider.value = e.target.value;

function getFactionColor(factionId) {
    if (ADAPTER_CONFIG.factions[factionId]) return ADAPTER_CONFIG.factions[factionId].color;
    // Sub-factions: derive from parent with hue rotation
    const parent = factionId < 100 ? factionId : Math.floor(factionId / 100) - 1;
    const offset = (factionId % 100) * 30; // 30° hue shift per sub-faction
    const base = parent === 0 ? 220 : 0; // Blue base or Red base
    return `hsl(${(base + offset) % 360}, 70%, 55%)`;
}

function clearModes() {
    spawnMode = false;
    spawnModeBtn.classList.remove('active');
    spawnHint.style.display = 'none';
    canvasEntities.classList.remove('spawn-mode');
    
    zoneMode = false;
    zoneModeBtn.classList.remove('active');
    zoneTools.style.display = 'none';
    zoneHint.style.display = 'none';
    
    splitMode = false;
    splitModeBtn.classList.remove('active');
    splitTools.style.display = 'none';
    splitHint.style.display = 'none';
    
    paintMode = false;
    paintModeBtn.classList.remove('active');
    brushTools.style.display = 'none';
    bgCanvas.classList.remove('paint-mode');
    canvasEntities.classList.remove('paint-mode');
}

// Spawn mode toggle
spawnModeBtn.onclick = () => {
    const wasSpawn = spawnMode;
    clearModes();
    spawnMode = !wasSpawn;
    spawnModeBtn.classList.toggle('active', spawnMode);
    spawnHint.style.display = spawnMode ? 'block' : 'none';
    canvasEntities.classList.toggle('spawn-mode', spawnMode);
    if (spawnMode) showToast('Spawn mode ON', 'info');
};

zoneModeBtn.onclick = () => {
    const wasZone = zoneMode;
    clearModes();
    zoneMode = !wasZone;
    zoneModeBtn.classList.toggle('active', zoneMode);
    zoneTools.style.display = zoneMode ? 'block' : 'none';
    zoneHint.style.display = zoneMode ? 'block' : 'none';
    if (zoneMode) showToast('Zone Place mode ON', 'info');
};

zoneTypeBtns.forEach(btn => {
    btn.onclick = () => {
        zoneTypeBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activeZoneType = btn.dataset.type;
    };
});

splitModeBtn.onclick = () => {
    const wasSplit = splitMode;
    clearModes();
    splitMode = !wasSplit;
    splitModeBtn.classList.toggle('active', splitMode);
    splitTools.style.display = splitMode ? 'block' : 'none';
    splitHint.style.display = splitMode ? 'block' : 'none';
    canvasEntities.classList.toggle('spawn-mode', splitMode); // crosshair
    if (splitMode) showToast('Split mode ON — click to set epicenter', 'info');
};


// Faction management
addFactionBtn.onclick = () => {
    const name = prompt('Enter faction name:');
    if (!name) return;
    const id = nextFactionId++;
    // Generate a random vibrant colour
    const hue = (id * 137) % 360;
    ADAPTER_CONFIG.factions[id] = { name, color: `hsl(${hue}, 70%, 55%)` };
    initFactionToggles();
    spawnFaction.value = id;
    showToast(`Added faction: ${name} (ID: ${id})`, 'success');
};

deleteFactionBtn.onclick = () => {
    const fid = parseInt(spawnFaction.value);
    if (isNaN(fid)) return;
    const fName = ADAPTER_CONFIG.factions[fid]?.name || `Faction ${fid}`;
    if (!confirm(`Delete faction "${fName}"? This will kill all its units.`)) return;
    sendCommand('kill_all', { faction_id: fid });
    delete ADAPTER_CONFIG.factions[fid];
    initFactionToggles();
    showToast(`Deleted faction: ${fName}`, 'warn');
};

// Terrain UI logic
paintModeBtn.onclick = () => {
    const wasPaint = paintMode;
    clearModes();
    paintMode = !wasPaint;
    paintModeBtn.classList.toggle('active', paintMode);
    brushTools.style.display = paintMode ? 'flex' : 'none';
    bgCanvas.classList.toggle('paint-mode', paintMode);
    canvasEntities.classList.toggle('paint-mode', paintMode);
};

brushBtns.forEach(btn => {
    btn.onclick = (e) => {
        brushBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activeBrush = btn.dataset.brush;
    };
});

clearTerrainBtn.onclick = () => {
    sendCommand("clear_terrain", {});
    for (let i = 0; i < terrainLocal.length; i++) terrainLocal[i] = 100;
    drawBackground();
};

saveScenarioBtn.onclick = () => sendCommand("save_scenario", {});
loadScenarioBtn.onclick = () => scenarioFileInput.click();
scenarioFileInput.onchange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
        try {
            const data = JSON.parse(ev.target.result);
            sendCommand("load_scenario", data);
            if (data.terrain) {
                if (data.terrain.hard_costs && data.terrain.soft_costs) {
                    const cellCount = GRID_W * GRID_H;
                    for (let i = 0; i < cellCount; i++) {
                        terrainLocal[i * 2] = data.terrain.hard_costs[i] || 100;
                        terrainLocal[i * 2 + 1] = data.terrain.soft_costs[i] || 100;
                    }
                }
                drawBackground();
            }
        } catch (err) {
            console.error("Failed to parse scenario file", err);
        }
    };
    reader.readAsText(file);
    scenarioFileInput.value = ''; // reset
};

const PERF_SYSTEMS = [
    { key: 'spatial_us', label: 'Spatial Grid' },
    { key: 'flow_field_us', label: 'Flow Field' },
    { key: 'interaction_us', label: 'Interaction' },
    { key: 'removal_us', label: 'Removal' },
    { key: 'movement_us', label: 'Movement' },
    { key: 'ws_sync_us', label: 'WS Sync' },
];

function updatePerfBars(telemetry) {
    const container = document.getElementById('perf-bars');
    for (const sys of PERF_SYSTEMS) {
        const us = telemetry[sys.key] || 0;
        let row = document.getElementById(`perf-${sys.key}`);
        if (!row) {
            row = document.createElement('div');
            row.id = `perf-${sys.key}`;
            row.className = 'perf-bar-row';
            row.innerHTML = `
                <span class="perf-bar-label">${sys.label}</span>
                <div class="perf-bar-track"><div class="perf-bar-fill"></div></div>
                <span class="perf-bar-value mono">0µs</span>`;
            container.appendChild(row);
        }
        const fill = row.querySelector('.perf-bar-fill');
        const valueEl = row.querySelector('.perf-bar-value');
        const pct = Math.min(100, (us / 2000) * 100); // 2000µs = 100%
        fill.style.width = pct + '%';
        fill.className = 'perf-bar-fill ' + (us < 200 ? 'green' : us < 1000 ? 'yellow' : 'red');
        valueEl.textContent = us + 'µs';
    }
}

function initFactionToggles() {
    const container = document.getElementById('faction-toggles');
    container.innerHTML = '';
    spawnFaction.innerHTML = '';
    fogTogglesContainer.innerHTML = '';
    const defaultStatic = new Set([1]); // Default FactionBehaviorMode

    for (const [factionIdStr, config] of Object.entries(ADAPTER_CONFIG.factions)) {
        const factionId = parseInt(factionIdStr);
        let isStatic = defaultStatic.has(factionId);

        // -- Spawn Faction Dropdown --
        const opt = document.createElement('option');
        opt.value = factionId;
        opt.textContent = config.name;
        spawnFaction.appendChild(opt);

        const zOpt = document.createElement('option');
        zOpt.value = factionId;
        zOpt.textContent = config.name;
        zoneFaction.appendChild(zOpt);

        const sOpt = document.createElement('option');
        sOpt.value = factionId;
        sOpt.textContent = config.name;
        splitSourceFaction.appendChild(sOpt);

        // -- Faction Behavior Toggles --
        const btn = document.createElement('button');
        btn.className = 'faction-toggle-btn';
        btn.innerHTML = `
            <span>${config.name}</span>
            <span class="faction-mode-badge ${isStatic ? 'static' : 'brain'}">${isStatic ? 'Static' : 'Brain'}</span>
        `;
        btn.style.borderLeftColor = config.color;
        btn.style.borderLeftWidth = '3px';

        btn.addEventListener('click', () => {
            isStatic = !isStatic;
            const badge = btn.querySelector('.faction-mode-badge');
            badge.textContent = isStatic ? 'Static' : 'Brain';
            badge.className = `faction-mode-badge ${isStatic ? 'static' : 'brain'}`;
            sendCommand('set_faction_mode', { faction_id: factionId, mode: isStatic ? 'static' : 'brain' });
        });

        container.appendChild(btn);

        // -- Fog Toggles --
        const fogLabel = document.createElement('label');
        fogLabel.className = 'toggle-control';
        fogLabel.innerHTML = `
            <input type="checkbox" id="toggle-fog-${factionId}" name="fog-group" value="${factionId}">
            <span class="control-indicator" style="border-color:${config.color}"></span>
            <span class="control-label">${config.name} Fog</span>
        `;
        const cb = fogLabel.querySelector('input');
        cb.addEventListener('change', (e) => {
            if (e.target.checked) {
                // uncheck others
                const allFog = fogTogglesContainer.querySelectorAll('input');
                for (const other of allFog) {
                    if (other !== e.target) other.checked = false;
                }
                showFog = true;
                sendCommand("set_fog_faction", { faction_id: factionId });
            } else {
                let anyChecked = false;
                const allFog = fogTogglesContainer.querySelectorAll('input');
                for (const other of allFog) {
                    if (other.checked) anyChecked = true;
                }
                if (!anyChecked) {
                    showFog = false;
                    fogVisible = null;
                    fogExplored = null;
                    sendCommand("set_fog_faction", {});
                }
            }
        });
        fogTogglesContainer.appendChild(fogLabel);
    }
}


// --- Telemetry Loop ---
setInterval(() => {
    const now = performance.now();
    const deltaMs = now - lastTickTime;
    
    if (deltaMs > 0) {
        currentTps = Math.round((tpsCounter / deltaMs) * 1000);
        statTps.textContent = currentTps;
        sparklines.tps.push(currentTps);
        sparklines.tps.draw();
    }
    
    tpsCounter = 0;
    lastTickTime = now;
    
    let swarmCount = 0;
    let defCount = 0;
    for (const ent of entities.values()) {
        if (ent.faction_id === 0) swarmCount++;
        else if (ent.faction_id === 1) defCount++;
    }
    
    statEntities.textContent = entities.size;
    sparklines.entities.push(entities.size);
    sparklines.entities.draw();
    statSwarm.textContent = swarmCount;
    statDefender.textContent = defCount;
    statTick.textContent = currentTick;
    
}, 1000);

// --- Drawing Helpers ---

function handleFlowFieldSync(msg) {
    flowFieldCache.set(msg.target_faction, {
        gridW: msg.grid_width,
        gridH: msg.grid_height,
        cellSize: msg.cell_size,
        vectors: msg.vectors,
    });
    drawBackground();
}

function drawCoordinateGrid(ctx) {
    ctx.strokeStyle = COLOR_GRID;
    ctx.lineWidth = 1;

    const cellWidth = WORLD_WIDTH / GRID_DIVISIONS;
    const cellHeight = WORLD_HEIGHT / GRID_DIVISIONS;
    
    ctx.beginPath();
    for (let i = 0; i <= GRID_DIVISIONS; i++) {
        const x = i * cellWidth;
        const [cxStart, cyStart] = worldToCanvas(x, 0);
        const [cxEnd, cyEnd] = worldToCanvas(x, WORLD_HEIGHT);
        
        ctx.strokeStyle = (i % 10 === 0) ? COLOR_GRID_MAJOR : COLOR_GRID;
        if (i % 10 === 0) ctx.lineWidth = 2; else ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(cxStart, cyStart);
        ctx.lineTo(cxEnd, cyEnd);
        ctx.stroke();
    }

    for (let i = 0; i <= GRID_DIVISIONS; i++) {
        const y = i * cellHeight;
        const [cxStart, cyStart] = worldToCanvas(0, y);
        const [cxEnd, cyEnd] = worldToCanvas(WORLD_WIDTH, y);
        
        ctx.strokeStyle = (i % 10 === 0) ? COLOR_GRID_MAJOR : COLOR_GRID;
        if (i % 10 === 0) ctx.lineWidth = 2; else ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(cxStart, cyStart);
        ctx.lineTo(cxEnd, cyEnd);
        ctx.stroke();
    }
}

function drawSpatialGrid(ctx) {
    const scale = getScaleFactor();
    const cellSize = 30; // Matches spatial grid config loosely
    ctx.strokeStyle = 'rgba(255, 255, 0, 0.2)';
    ctx.lineWidth = 1;

    ctx.beginPath();
    for (let x = 0; x <= WORLD_WIDTH; x += cellSize) {
        const [cx1, cy1] = worldToCanvas(x, 0);
        const [cx2, cy2] = worldToCanvas(x, WORLD_HEIGHT);
        ctx.moveTo(cx1, cy1);
        ctx.lineTo(cx2, cy2);
    }
    for (let y = 0; y <= WORLD_HEIGHT; y += cellSize) {
        const [cx1, cy1] = worldToCanvas(0, y);
        const [cx2, cy2] = worldToCanvas(WORLD_WIDTH, y);
        ctx.moveTo(cx1, cy1);
        ctx.lineTo(cx2, cy2);
    }
    ctx.stroke();
}

function drawFlowFieldArrows(ctx) {
    const scale = getScaleFactor();

    for (const [factionId, field] of flowFieldCache.entries()) {
        const color = ADAPTER_CONFIG.factions[factionId]?.color || '#fff';
        ctx.strokeStyle = color;
        ctx.fillStyle = color;
        ctx.lineWidth = 1;
        
        // draw arrows
        for (let y = 0; y < field.gridH; y++) {
            for (let x = 0; x < field.gridW; x++) {
                const vec = field.vectors[y * field.gridW + x];
                if (!vec || (vec[0] === 0 && vec[1] === 0)) continue;
                
                const wx = x * field.cellSize + field.cellSize / 2;
                const wy = y * field.cellSize + field.cellSize / 2;
                
                const [cx, cy] = worldToCanvas(wx, wy);
                const mag = 10 * scale; // Arrow length
                const angle = Math.atan2(vec[1], vec[0]);
                
                ctx.beginPath();
                ctx.moveTo(cx, cy);
                ctx.lineTo(cx + Math.cos(angle) * mag, cy + Math.sin(angle) * mag);
                ctx.stroke();

                // Arrow head
                ctx.beginPath();
                ctx.arc(cx + Math.cos(angle) * mag, cy + Math.sin(angle) * mag, 2 * scale, 0, Math.PI * 2);
                ctx.fill();
            }
        }
    }
}

function drawTerrain(ctx) {
    for (let y = 0; y < GRID_H; y++) {
        for (let x = 0; x < GRID_W; x++) {
            const idx = (y * GRID_W + x) * 2;
            const hard = terrainLocal[idx];
            const soft = terrainLocal[idx + 1];

            if (hard === 100 && soft === 100) continue;

            let color = null;
            if (hard === 65535) color = BRUSH_MAP.wall.color;
            else if (hard === 200) color = BRUSH_MAP.mud.color;
            else if (hard === 125) color = BRUSH_MAP.pushable.color;
            
            if (color) {
                ctx.fillStyle = color;
                const [cx, cy] = worldToCanvas(x * TERRAIN_CELL_SIZE, y * TERRAIN_CELL_SIZE);
                const [cx2, cy2] = worldToCanvas((x + 1) * TERRAIN_CELL_SIZE, (y + 1) * TERRAIN_CELL_SIZE);
                ctx.fillRect(cx, cy, cx2 - cx + 1, cy2 - cy + 1);
            }
        }
    }
}

function drawBackground() {
    bgCtx.clearRect(0, 0, bgCanvas.width, bgCanvas.height);
    bgCtx.fillStyle = COLOR_BG;
    bgCtx.fillRect(0, 0, bgCanvas.width, bgCanvas.height);

    drawTerrain(bgCtx);

    if (showGrid) drawCoordinateGrid(bgCtx);
    if (showSpatialGrid) drawSpatialGrid(bgCtx);
    if (showFlowField) drawFlowFieldArrows(bgCtx);
}

function addDeathAnimation(id) {
    const ent = entities.get(id);
    if (ent) {
        deathAnimations.push({
            x: ent.x, y: ent.y,
            startTime: performance.now(),
            factionId: ent.faction_id,
        });
    }
    entities.delete(id);
}

function drawDeathAnimations(ctx) {
    const now = performance.now();
    for (let i = deathAnimations.length - 1; i >= 0; i--) {
        const anim = deathAnimations[i];
        const elapsed = now - anim.startTime;
        if (elapsed > 500) { deathAnimations.splice(i, 1); continue; }

        const progress = elapsed / 500;
        const scale = getScaleFactor();
        const radius = (ENTITY_RADIUS + progress * ENTITY_RADIUS * 3) * scale;
        const alpha = 1.0 - progress;

        const [cx, cy] = worldToCanvas(anim.x, anim.y);
        const color = ADAPTER_CONFIG.factions[anim.factionId]?.color || '#fff';
        
        ctx.strokeStyle = color.replace(')', `, ${alpha})`).replace('rgb', 'rgba');
        if (ctx.strokeStyle === color) { // fallback if color format differs
            ctx.globalAlpha = alpha;
            ctx.strokeStyle = color;
        }

        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.stroke();
        ctx.globalAlpha = 1.0; // Reset
    }
}

function drawHealthBars(ctx, cullLeft, cullRight, cullTop, cullBottom) {
    const barW = 10, barH = 2;
    for (const ent of entities.values()) {
        if (!ent.stats || ent.stats[0] === undefined || ent.stats[0] >= 1.0) continue;

        const [cx, cy] = worldToCanvas(ent.x, ent.y);
        if (cx < cullLeft || cx > cullRight || cy < cullTop || cy > cullBottom) continue;

        const scale = getScaleFactor();
        const bw = barW * scale, bh = barH * scale;
        const hp = Math.max(0, ent.stats[0]); // 0.0–1.0

        // Background
        ctx.fillStyle = 'rgba(255,255,255,0.15)';
        ctx.fillRect(cx - bw/2, cy - 8*scale, bw, bh);

        // Fill (green→red lerp)
        const r = Math.round(255 * (1 - hp));
        const g = Math.round(255 * hp);
        ctx.fillStyle = `rgb(${r}, ${g}, 50)`;
        ctx.fillRect(cx - bw/2, cy - 8*scale, bw * hp, bh);
    }
}

function drawEntities() {
    const scale = getScaleFactor();
    const radius = ENTITY_RADIUS * scale;
    
    // Simple Frustum culling limits
    const margin = 50; // pixels
    const cullLeft = -margin;
    const cullRight = canvasEntities.width + margin;
    const cullTop = -margin;
    const cullBottom = canvasEntities.height + margin;

    // Draw lines first (velocity)
    if (showVelocity) {
        ctx.strokeStyle = COLOR_VELOCITY;
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (const ent of entities.values()) {
            const [cx, cy] = worldToCanvas(ent.x, ent.y);
            if (cx >= cullLeft && cx <= cullRight && cy >= cullTop && cy <= cullBottom) {
                if (ent.dx !== undefined && ent.dy !== undefined && (ent.dx !== 0 || ent.dy !== 0)) {
                    const norm = Math.sqrt(ent.dx*ent.dx + ent.dy*ent.dy) || 1;
                    const vx = (ent.dx / norm) * VELOCITY_VECTOR_SCALE * scale;
                    const vy = (ent.dy / norm) * VELOCITY_VECTOR_SCALE * scale;
                    
                    ctx.moveTo(cx, cy);
                    ctx.lineTo(cx + vx, cy + vy);
                }
            }
        }
        ctx.stroke();
    }

    // Draw density heatmap
    if (showDensityHeatmap && densityHeatmap) {
        for (let y = 0; y < GRID_H; y++) {
            for (let x = 0; x < GRID_W; x++) {
                const value = densityHeatmap[y * GRID_W + x];
                if (value < 0.01) continue; // Skip empty cells
    
                const worldX = x * TERRAIN_CELL_SIZE;
                const worldY = y * TERRAIN_CELL_SIZE;
                const [screenX, screenY] = worldToCanvas(worldX, worldY);
                const screenSize = TERRAIN_CELL_SIZE * scale;
    
                // Heat gradient: transparent → yellow → orange → red
                const alpha = Math.min(value * 0.6, 0.6);
                const hue = 60 - value * 60; // 60=yellow → 0=red
                ctx.fillStyle = `hsla(${hue}, 100%, 50%, ${alpha})`;
                ctx.fillRect(screenX, screenY, screenSize + 1, screenSize + 1);
            }
        }
    }

    // Draw zone modifiers
    if (showZoneModifiers && zoneModifiers) {
        for (const zone of zoneModifiers) {
            const [screenX, screenY] = worldToCanvas(zone.x, zone.y);
            const screenR = zone.radius * scale;
    
            ctx.beginPath();
            ctx.arc(screenX, screenY, screenR, 0, Math.PI * 2);
    
            if (zone.cost_modifier < 0) {
                // Attract: blue glow with pulsing alpha
                const pulse = 0.3 + 0.2 * Math.sin(Date.now() / 300);
                ctx.fillStyle = `rgba(59, 130, 246, ${pulse})`;
                ctx.strokeStyle = 'rgba(59, 130, 246, 0.7)';
            } else {
                // Repel: red glow
                const pulse = 0.3 + 0.2 * Math.sin(Date.now() / 300);
                ctx.fillStyle = `rgba(239, 68, 68, ${pulse})`;
                ctx.strokeStyle = 'rgba(239, 68, 68, 0.7)';
            }
    
            ctx.fill();
            ctx.setLineDash([4, 4]);
            ctx.lineWidth = 2;
            ctx.stroke();
            ctx.setLineDash([]);
    
            // Label: cost modifier + remaining ticks
            ctx.fillStyle = '#fff';
            ctx.font = '11px Inter';
            ctx.textAlign = 'center';
            ctx.fillText(
                `${zone.cost_modifier > 0 ? '+' : ''}${zone.cost_modifier} (${zone.ticks_remaining}t)`,
                screenX, screenY
            );
        }
    }

    // Draw Factions
    const activeFactionsSet = new Set();
    for (const ent of entities.values()) activeFactionsSet.add(ent.faction_id);
    
    for (const factionId of activeFactionsSet) {
        ctx.fillStyle = getFactionColor(factionId);
        ctx.beginPath();
        for (const ent of entities.values()) {
            if (ent.faction_id === factionId) {
                const [cx, cy] = worldToCanvas(ent.x, ent.y);
                if (cx >= cullLeft && cx <= cullRight && cy >= cullTop && cy <= cullBottom) {
                    ctx.moveTo(cx + radius, cy);
                    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
                }
            }
        }
        ctx.fill();
    }

    // EngineOverride Extracted drawing
    if (showOverrideMarkers) {
        for (const ent of entities.values()) {
            // Assume the rust backend may send this indirectly via velocity ignoring typical flow field
            // But if it's not present, we will fallback to a default marker if we detect an override manually
            // We need to implement marker drawing around entities.
            // Wait, we don't know who has override purely from EntityState unless added to `stats`.
            // The instructions refer to `has_override`. For now we rely on a hypothetical field `has_override`.
            if (ent.has_override) {
                const t = Date.now() / 200;
                const [cx, cy] = worldToCanvas(ent.x, ent.y);
                if (cx >= cullLeft && cx <= cullRight && cy >= cullTop && cy <= cullBottom) {
                    ctx.strokeStyle = `rgba(255, 215, 0, ${0.5 + 0.5 * Math.sin(t)})`;
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    ctx.moveTo(cx, cy - 6 * scale);
                    ctx.lineTo(cx + 6 * scale, cy);
                    ctx.lineTo(cx, cy + 6 * scale);
                    ctx.lineTo(cx - 6 * scale, cy);
                    ctx.closePath();
                    ctx.stroke();
                }
            }
        }
    }

    drawHealthBars(ctx, cullLeft, cullRight, cullTop, cullBottom);
    drawDeathAnimations(ctx);
    
    // Highlight Selected Entity
    if (selectedEntityId !== null) {
        const ent = entities.get(selectedEntityId);
        if (ent) {
            const [cx, cy] = worldToCanvas(ent.x, ent.y);
            ctx.strokeStyle = 'white';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(cx, cy, radius + 4 * scale, 0, Math.PI * 2);
            ctx.stroke();
        }
    }

    // Ghost Spawn Circle (only in spawn mode)
    if (spawnMode && mouseWorldX !== null && mouseWorldY !== null && !isDragging) {
        const spread = parseFloat(spawnSpread.value) || 0;
        const fid = parseInt(spawnFaction.value);
        const fColor = ADAPTER_CONFIG.factions[fid]?.color || 'white';
        const [cx, cy] = worldToCanvas(mouseWorldX, mouseWorldY);
        
        // Draw spread radius circle
        if (spread > 0) {
            ctx.strokeStyle = fColor;
            ctx.globalAlpha = 0.5;
            ctx.setLineDash([5, 5]);
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(cx, cy, spread * scale, 0, Math.PI * 2);
            ctx.stroke();
            ctx.setLineDash([]);
            ctx.globalAlpha = 1.0;
        }
        
        // Draw crosshair center
        ctx.strokeStyle = fColor;
        ctx.globalAlpha = 0.7;
        ctx.lineWidth = 1;
        const ch = 8;
        ctx.beginPath();
        ctx.moveTo(cx - ch, cy); ctx.lineTo(cx + ch, cy);
        ctx.moveTo(cx, cy - ch); ctx.lineTo(cx, cy + ch);
        ctx.stroke();
        ctx.globalAlpha = 1.0;
    }

    // Ghost Split Center (split mode)
    if (splitMode && mouseWorldX !== null && mouseWorldY !== null && !isDragging) {
        const pct = parseInt(splitPct.value) || 30;
        const fName = splitSourceFaction.options[splitSourceFaction.selectedIndex]?.text || "Faction";
        const [cx, cy] = worldToCanvas(mouseWorldX, mouseWorldY);
        
        ctx.strokeStyle = "#fff";
        ctx.globalAlpha = 0.8;
        ctx.lineWidth = 1;
        const ch = 10;
        ctx.beginPath();
        ctx.moveTo(cx - ch, cy); ctx.lineTo(cx + ch, cy);
        ctx.moveTo(cx, cy - ch); ctx.lineTo(cx, cy + ch);
        ctx.stroke();
        
        ctx.fillStyle = "#fff";
        ctx.font = '11px Inter';
        ctx.textAlign = 'left';
        ctx.fillText(`${pct}% of ${fName}`, cx + 15, cy + 4);
        ctx.globalAlpha = 1.0;
    }

    // Ghost Zone Center (zone mode)
    if (zoneMode && mouseWorldX !== null && mouseWorldY !== null && !isDragging) {
        const [cx, cy] = worldToCanvas(mouseWorldX, mouseWorldY);
        const screenR = (parseFloat(zoneRadius.value) || 100) * scale;
        
        if (activeZoneType === 'attract') {
            ctx.fillStyle = `rgba(59, 130, 246, 0.2)`;
            ctx.strokeStyle = `rgba(59, 130, 246, 0.6)`;
        } else {
            ctx.fillStyle = `rgba(239, 68, 68, 0.2)`;
            ctx.strokeStyle = `rgba(239, 68, 68, 0.6)`;
        }
        
        ctx.beginPath();
        ctx.arc(cx, cy, screenR, 0, Math.PI * 2);
        ctx.fill();
        ctx.setLineDash([4, 4]);
        ctx.stroke();
        ctx.setLineDash([]);
    }
}

function updateMlBrainPanel(mlBrain) {
    if (!mlBrain) return;

    const pythonEl = document.getElementById('ml-python-status');
    const interventionEl = document.getElementById('ml-intervention');
    const directiveEl = document.getElementById('ml-last-directive');

    if (pythonEl) {
        pythonEl.textContent = mlBrain.python_connected ? '🟢 Connected' : '🔴 Disconnected';
        pythonEl.style.color = mlBrain.python_connected ? '#22c55e' : '#ef4444';
    }

    if (interventionEl) {
        interventionEl.textContent = mlBrain.intervention_active ? '⚠️ Active' : '✅ Normal';
        interventionEl.style.color = mlBrain.intervention_active ? '#f59e0b' : '#22c55e';
    }

    if (directiveEl && mlBrain.last_directive) {
        try {
            const d = JSON.parse(mlBrain.last_directive);
            let summary = d.directive || 'Hold';
            if (d.directive === 'SplitFaction') {
                summary = `Split ${Math.round(d.percentage * 100)}% to ${d.new_sub_faction}`;
            } else if (d.directive === 'SetZoneModifier') {
                summary = `${d.cost_modifier < 0 ? 'Attract' : 'Repel'} at (${Math.round(d.x)}, ${Math.round(d.y)})`;
            } else if (d.directive === 'UpdateNavigation') {
                summary = `Nav ${d.follower_faction} to ${d.target.type}`;
            }
            directiveEl.textContent = summary;
        } catch {
            directiveEl.textContent = '—';
        }
    }
}

function updateAggroGrid(aggroMasks, activeFactionsIds) {
    const container = document.getElementById('aggro-mask-grid');
    if (!container) return;
    container.innerHTML = '';

    for (const mask of aggroMasks) {
        const cell = document.createElement('div');
        cell.className = `aggro-cell ${mask.allow_combat ? 'combat-on' : 'combat-off'}`;
        cell.innerHTML = `
            <span class="aggro-label">${mask.source_faction}→${mask.target_faction}</span>
            <span class="aggro-icon">${mask.allow_combat ? '⚔️' : '🛡️'}</span>
        `;
        cell.onclick = () => sendCommand('set_aggro_mask', {
            source_faction: mask.source_faction,
            target_faction: mask.target_faction,
            allow_combat: !mask.allow_combat,
        });
        container.appendChild(cell);
    }
}

function updateLegend(activeSubFactions) {
    const legend = document.getElementById('legend-list');
    if (!legend) return;
    // Keep base factions, remove old sub-faction entries
    legend.querySelectorAll('.legend-sub').forEach(el => el.remove());

    for (const sf of (activeSubFactions || [])) {
        const item = document.createElement('div');
        item.className = 'legend-item legend-sub';
        item.innerHTML = `
            <span class="color-swatch" style="background: ${getFactionColor(sf)};"></span>
            <span>Sub-Faction ${sf}</span>
        `;
        legend.appendChild(item);
    }
    
    const sflist = document.getElementById('sub-faction-list');
    if (sflist) {
        sflist.innerHTML = '';
        for (const sf of (activeSubFactions || [])) {
            const fi = document.createElement('div');
            fi.className = 'sub-faction-item';
            const parent = sf < 100 ? sf : Math.floor(sf / 100) - 1;
            fi.innerHTML = `
                <span style="color: ${getFactionColor(sf)}">Sub Faction ${sf}</span>
                <button class="btn secondary merge-btn" onclick="sendCommand('merge_faction', { source_faction: ${sf}, target_faction: ${parent} })">Merge to ${parent}</button>
            `;
            sflist.appendChild(fi);
        }
    }
}

const fogCanvas = document.createElement('canvas');
const fogCtx = fogCanvas.getContext('2d');

function drawFog() {
    if (!fogVisible || !fogExplored) return;

    if (fogCanvas.width !== canvasEntities.width || fogCanvas.height !== canvasEntities.height) {
        fogCanvas.width = canvasEntities.width;
        fogCanvas.height = canvasEntities.height;
    }

    fogCtx.globalCompositeOperation = 'source-over';
    fogCtx.fillStyle = 'rgba(0,0,0,1)';
    fogCtx.fillRect(0, 0, fogCanvas.width, fogCanvas.height);

    fogCtx.globalCompositeOperation = 'destination-out';

    function getBit(arr, idx) { return (arr[idx >> 5] >> (idx & 31)) & 1; }

    for (let y = 0; y < GRID_H; y++) {
        for (let x = 0; x < GRID_W; x++) {
            const idx = y * GRID_W + x;
            const vis = getBit(fogVisible, idx);
            const exp = getBit(fogExplored, idx);

            if (!exp) continue;

            const [cx, cy] = worldToCanvas(x * TERRAIN_CELL_SIZE, y * TERRAIN_CELL_SIZE);
            const [cx2, cy2] = worldToCanvas((x + 1) * TERRAIN_CELL_SIZE, (y + 1) * TERRAIN_CELL_SIZE);
            
            if (vis) {
                fogCtx.fillStyle = 'rgba(0, 0, 0, 1)'; // fully punch hole
            } else if (exp) {
                fogCtx.fillStyle = 'rgba(0, 0, 0, 0.5)'; // partially punch hole
            }
            fogCtx.fillRect(cx, cy, cx2 - cx + 1.5, cy2 - cy + 1.5);
        }
    }

    ctx.drawImage(fogCanvas, 0, 0);
}

function renderFrame() {
    ctx.clearRect(0, 0, canvasEntities.width, canvasEntities.height);

    drawEntities();

    if (showFog) {
        drawFog();
    }

    updateInspectorPanel();

    // FPS
    frames++;
    const now = performance.now();
    if (now - lastFpsTime >= 1000) {
        currentFps = frames;
        frames = 0;
        lastFpsTime = now;
    }

    requestAnimationFrame(renderFrame);
}

// --- Init ---
resizeCanvas();
connectWebSocket();
requestAnimationFrame(renderFrame);
