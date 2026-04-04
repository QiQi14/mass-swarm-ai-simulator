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
let currentTick = 0;
let ws = null;
let isPaused = false;

// View transform (pan/zoom)
let viewX = WORLD_WIDTH / 2;
let viewY = WORLD_HEIGHT / 2;
let viewScale = 1.0;

// Layer visibility
let showGrid = document.getElementById("toggle-grid").checked;
let showVelocity = document.getElementById("toggle-velocity").checked;
let showFog = document.getElementById("toggle-fog").checked;

// Telemetry
let lastTickTime = performance.now();
let tpsCounter = 0;
let currentTps = 0;
let lastFpsTime = performance.now();
let frames = 0;
let currentFps = 0;
let lastPingTime = 0;
let currentPing = 0;

// DOM Elements
const canvas = document.getElementById("sim-canvas");
const ctx = canvas.getContext("2d");

const statTps = document.getElementById("stat-tps");
const statTick = document.getElementById("stat-tick");
const statPing = document.getElementById("stat-ping");
const statAiLatency = document.getElementById("stat-ai-latency");
const statEntities = document.getElementById("stat-entities");
const statSwarm = document.getElementById("stat-swarm");
const statDefender = document.getElementById("stat-defender");

const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");

const playPauseBtn = document.getElementById("play-pause-btn");
const stepBtn = document.getElementById("step-btn");
const stepCountInput = document.getElementById("step-count-input");

const toggleGrid = document.getElementById("toggle-grid");
const toggleVelocity = document.getElementById("toggle-velocity");
const toggleFog = document.getElementById("toggle-fog");

// Colors
const COLOR_BG = "#0f1115";
const COLOR_GRID = "rgba(255, 255, 255, 0.05)";
const COLOR_GRID_MAJOR = "rgba(255, 255, 255, 0.15)";
const COLOR_SWARM = "#ff3b30";
const COLOR_DEFENDER = "#0a84ff";
const COLOR_VELOCITY = "rgba(255, 255, 255, 0.5)";
const COLOR_FOG = "rgba(0, 0, 0, 0.6)";

// --- Canvas Setup ---

function resizeCanvas() {
    canvas.width = canvas.clientWidth;
    canvas.height = canvas.clientHeight;
}
window.addEventListener("resize", resizeCanvas);

// --- Coordinate Transforms ---

function getScaleFactor() {
    return Math.min(canvas.width, canvas.height) / Math.max(WORLD_WIDTH, WORLD_HEIGHT) * viewScale;
}

function worldToCanvas(wx, wy) {
    const scale = getScaleFactor();
    const cx = (wx - viewX) * scale + canvas.width / 2;
    const cy = (wy - viewY) * scale + canvas.height / 2;
    return [cx, cy];
}

function canvasToWorld(cx, cy) {
    const scale = getScaleFactor();
    const wx = (cx - canvas.width / 2) / scale + viewX;
    const wy = (cy - canvas.height / 2) / scale + viewY;
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
        currentTick = 0;
        lastPingTime = performance.now();
        // Send a ping-like command just to measure latency if we wanted, 
        // but for now we just assume connected = 0ms if on localhost.
        currentPing = "< 1";
    };

    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            if (msg.type === "SyncDelta" || msg.type === "full_sync" || msg.type === "delta_update") {
                if (msg.tick) {
                    // Update TPS counter if tick advanced
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
                if (msg.spawned) {
                    for (const ent of msg.spawned) {
                        entities.set(ent.id, ent);
                    }
                }
                if (msg.died) {
                    for (const id of msg.died) {
                        entities.delete(id);
                    }
                }
            } else if (msg.type === "state_snapshot") {
                 // Might handle full snapshot similarly if broadcast
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
        // Log error, let onclose handle reconnect
        console.warn("WebSocket error occurred.");
    };
}

function sendCommand(cmd, params = {}) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "command", cmd, params }));
    }
}

// --- Interaction / Controls ---

// Pan state
let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;
let viewStartDragX = 0;
let viewStartDragY = 0;
let hasDragged = false;

canvas.addEventListener("mousedown", (e) => {
    isDragging = true;
    hasDragged = false;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    viewStartDragX = viewX;
    viewStartDragY = viewY;
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
    }
});

window.addEventListener("mouseup", (e) => {
    isDragging = false;
});

canvas.addEventListener("click", (e) => {
    if (!hasDragged) {
        // Spawn wave at click position
        const rect = canvas.getBoundingClientRect();
        const cx = e.clientX - rect.left;
        const cy = e.clientY - rect.top;
        const [wx, wy] = canvasToWorld(cx, cy);
        
        sendCommand("spawn_wave", { faction_id: 0, amount: 10, x: wx, y: wy });
    }
});

canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
    
    // Zoom toward mouse pointer logic
    const rect = canvas.getBoundingClientRect();
    const cx = e.clientX - rect.left;
    const cy = e.clientY - rect.top;
    
    const [wxBefore, wyBefore] = canvasToWorld(cx, cy);
    
    viewScale = Math.max(0.5, Math.min(20.0, viewScale * zoomFactor));
    
    const [wxAfter, wyAfter] = canvasToWorld(cx, cy);
    
    viewX += (wxBefore - wxAfter);
    viewY += (wyBefore - wyAfter);
});

canvas.addEventListener("dblclick", () => {
    viewX = WORLD_WIDTH / 2;
    viewY = WORLD_HEIGHT / 2;
    viewScale = 1.0;
});

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

toggleGrid.onchange = (e) => { showGrid = e.target.checked; };
toggleVelocity.onchange = (e) => { showVelocity = e.target.checked; };
toggleFog.onchange = (e) => { showFog = e.target.checked; };


// --- Telemetry Loop ---
setInterval(() => {
    const now = performance.now();
    const deltaMs = now - lastTickTime;
    
    if (deltaMs > 0) {
        currentTps = Math.round((tpsCounter / deltaMs) * 1000);
        statTps.textContent = currentTps;
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
    statSwarm.textContent = swarmCount;
    statDefender.textContent = defCount;
    statTick.textContent = currentTick;
    statPing.textContent = currentPing === 0 ? "0ms" : currentPing + "ms";
    statAiLatency.textContent = "N/A";
    
}, 1000);

// --- Render Loop ---

function drawGrid() {
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

function drawEntities() {
    const scale = getScaleFactor();
    const radius = ENTITY_RADIUS * scale;
    
    // Simple Frustum culling limits
    const margin = 50; // pixels
    const cullLeft = -margin;
    const cullRight = canvas.width + margin;
    const cullTop = -margin;
    const cullBottom = canvas.height + margin;

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
}

function drawFog() {
    // Basic fog placeholder - darken outer edges
    // In a real implementation this would use spatial grid visibility data
    ctx.fillStyle = COLOR_FOG;
    const scale = getScaleFactor();
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const baseRadius = 300 * scale;

    const grad = ctx.createRadialGradient(cx, cy, baseRadius, cx, cy, baseRadius * 1.5);
    grad.addColorStop(0, "rgba(0,0,0,0)");
    grad.addColorStop(1, COLOR_FOG);
    
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
}

function renderFrame() {
    ctx.fillStyle = COLOR_BG;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    if (showGrid) {
        drawGrid();
    }

    drawEntities();

    if (showFog) {
        drawFog();
    }

    // FPS
    frames++;
    const now = performance.now();
    if (now - lastFpsTime >= 1000) {
        currentFps = frames;
        frames = 0;
        lastFpsTime = now;
        // Could update FPS display here if it existed in DOM
    }

    requestAnimationFrame(renderFrame);
}

// --- Init ---
resizeCanvas();
connectWebSocket();
requestAnimationFrame(renderFrame);
