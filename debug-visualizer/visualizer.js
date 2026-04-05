// Constants
const WS_URL = "ws://127.0.0.1:8080";
const WORLD_WIDTH = 1000.0;
const WORLD_HEIGHT = 1000.0;
const GRID_DIVISIONS = 100;
const ENTITY_RADIUS = 3;
const RECONNECT_INTERVAL_MS = 2000;
const VELOCITY_VECTOR_SCALE = 15;

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
let showFog = document.getElementById("toggle-fog").checked;

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
const toggleFog = document.getElementById("toggle-fog");

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
            } else if (msg.type === "FlowFieldSync") {
                handleFlowFieldSync(msg);
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
    }
}

// --- Interaction / Controls ---

let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;
let viewStartDragX = 0;
let viewStartDragY = 0;
let hasDragged = false;

canvasEntities.addEventListener("mousedown", (e) => {
    isDragging = true;
    hasDragged = false;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    viewStartDragX = viewX;
    viewStartDragY = viewY;

    // Wait until mouseup or checking drag to perform click actions
});

window.addEventListener("mousemove", (e) => {
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
    if (isDragging && !hasDragged && e.target === canvasEntities) {
        const rect = canvasEntities.getBoundingClientRect();
        const [wx, wy] = canvasToWorld(e.clientX - rect.left, e.clientY - rect.top);
    
        // O(N) nearest-entity search
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
    
        // Selection threshold (10 world units squared)
        if (bestId !== null && bestDist < 100) { 
            selectedEntityId = bestId;
            updateInspectorPanel();
            document.getElementById('inspector-panel').style.display = 'block';
        } else {
            sendCommand("spawn_wave", { faction_id: 0, amount: 10, x: wx, y: wy });
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

toggleGrid.onchange = (e) => { showGrid = e.target.checked; drawBackground(); };
toggleSpatialGrid.onchange = (e) => { showSpatialGrid = e.target.checked; drawBackground(); };
toggleFlowField.onchange = (e) => { showFlowField = e.target.checked; drawBackground(); };
toggleVelocity.onchange = (e) => { showVelocity = e.target.checked; };
toggleFog.onchange = (e) => { showFog = e.target.checked; };

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
    const defaultStatic = new Set([1]); // Default FactionBehaviorMode

    for (const [factionIdStr, config] of Object.entries(ADAPTER_CONFIG.factions)) {
        const factionId = parseInt(factionIdStr);
        let isStatic = defaultStatic.has(factionId);

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

function drawBackground() {
    bgCtx.clearRect(0, 0, bgCanvas.width, bgCanvas.height);
    bgCtx.fillStyle = COLOR_BG;
    bgCtx.fillRect(0, 0, bgCanvas.width, bgCanvas.height);

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

    // Draw Factions
    for (const factionId in ADAPTER_CONFIG.factions) {
        const config = ADAPTER_CONFIG.factions[factionId];
        ctx.fillStyle = config.color;
        ctx.beginPath();
        for (const ent of entities.values()) {
            if (ent.faction_id === parseInt(factionId)) {
                const [cx, cy] = worldToCanvas(ent.x, ent.y);
                if (cx >= cullLeft && cx <= cullRight && cy >= cullTop && cy <= cullBottom) {
                    ctx.moveTo(cx + radius, cy);
                    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
                }
            }
        }
        ctx.fill();
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
}

function drawFog() {
    ctx.fillStyle = COLOR_FOG;
    const scale = getScaleFactor();
    const cx = canvasEntities.width / 2;
    const cy = canvasEntities.height / 2;
    const baseRadius = 300 * scale;

    const grad = ctx.createRadialGradient(cx, cy, baseRadius, cx, cy, baseRadius * 1.5);
    grad.addColorStop(0, "rgba(0,0,0,0)");
    grad.addColorStop(1, COLOR_FOG);
    
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, canvasEntities.width, canvasEntities.height);
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
