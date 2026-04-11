// ─── Main Entry Point ───────────────────────────────────────────────
// Initializes all modules and starts the render loop.

import * as S from './state.js';
import { initCanvases, resizeCanvas, drawEntities, drawFog, drawBackground, drawArenaBounds } from './draw/index.js';
import { connectWebSocket, sendCommand } from './websocket.js';
import { initControls } from './controls/index.js';
import { updateInspectorPanel, startTelemetryLoop } from './panels/index.js';

// Expose sendCommand globally for inline onclick handlers in dynamically created HTML
window.__sendCommand = sendCommand;

// ── Initialize Canvases ─────────────────────────────────────────────

const bgCanvas = document.getElementById("canvas-bg");
const canvasEntities = document.getElementById("canvas-entities");
initCanvases(bgCanvas, canvasEntities);

// ── Read initial toggle state from DOM ──────────────────────────────

S.setShowGrid(document.getElementById("toggle-grid").checked);
S.setShowSpatialGrid(document.getElementById("toggle-spatial-grid").checked);
S.setShowFlowField(document.getElementById("toggle-flow-field").checked);
S.setShowVelocity(document.getElementById("toggle-velocity").checked);
S.setShowDensityHeatmap(document.getElementById("toggle-density-heatmap").checked);
S.setShowZoneModifiers(document.getElementById("toggle-zone-modifiers").checked);
S.setShowOverrideMarkers(document.getElementById("toggle-override-markers").checked);
const arenaToggle = document.getElementById("toggle-arena-bounds");
if (arenaToggle) S.setShowArenaBounds(arenaToggle.checked);

// ── Wire Events ─────────────────────────────────────────────────────

window.addEventListener("resize", resizeCanvas);
initControls();

// ── Render Loop ─────────────────────────────────────────────────────

let frames = 0;
let lastFpsTime = performance.now();

function renderFrame() {
    const ctx = document.getElementById("canvas-entities").getContext("2d");
    ctx.clearRect(0, 0, canvasEntities.width, canvasEntities.height);

    drawEntities();

    if (S.showFog) {
        drawFog();
    }

    drawArenaBounds(ctx);

    updateInspectorPanel();

    // FPS counter
    frames++;
    const now = performance.now();
    if (now - lastFpsTime >= 1000) {
        S.setCurrentFps(frames);
        frames = 0;
        lastFpsTime = now;
    }

    requestAnimationFrame(renderFrame);
}

// ── Start ───────────────────────────────────────────────────────────

resizeCanvas();
connectWebSocket();
startTelemetryLoop();
requestAnimationFrame(renderFrame);
