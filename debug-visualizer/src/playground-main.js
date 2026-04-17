// ═══════════════════════════════════════════════════════════════
// PLAYGROUND MAIN — Node-Based Scenario Editor & Live Canvas
// ═══════════════════════════════════════════════════════════════

// CSS imports
import './styles/reset.css';
import './styles/variables.css';
import './styles/canvas.css';
import './styles/animations.css';
import './styles/overlay.css';
import './styles/node-editor.css';
import './styles/preset-gallery.css';
import './styles/playground-overlay.css';

// Core modules
import { initCanvases, resizeCanvas, drawEntities, drawFog, drawBackground, drawArenaBounds } from './draw/index.js';
import { initEngine, sendEngineCommand, getEngine, getEngineMode, EngineMode } from './engine/index.js';
import * as S from './state.js';
import { initControls, clearModes } from './controls/init.js';

// Node editor
import { createEditor, registerAllNodes, getNodeHTML, getNodePorts } from './node-editor/drawflow-setup.js';
import { registerFactionNode } from './node-editor/nodes/faction.js';
import { registerRelationshipNode } from './node-editor/nodes/relationship.js';
import { registerUnitNode } from './node-editor/nodes/unit.js';
import { registerStatNode } from './node-editor/nodes/stat.js';
import { registerDeathNode } from './node-editor/nodes/death.js';
import { registerCombatNode } from './node-editor/nodes/combat.js';
import { registerNavigationNode } from './node-editor/nodes/navigation.js';
import { registerWaypointNode } from './node-editor/nodes/waypoint.js';
import { registerGeneralNode } from './node-editor/nodes/general.js';
import { compileGraph, executeScenario, presetToGraph } from './node-editor/compiler.js';
import { showPresetGallery, hidePresetGallery } from './node-editor/preset-gallery.js';

// Panels (shared)
import inspectorPanel, { updateInspectorPanel } from './panels/shared/inspector.js';
import telemetryPanel, { startTelemetryLoop } from './panels/shared/telemetry.js';
import legendPanel, { updateLegend, initFactionToggles } from './panels/shared/legend.js';

// Components
import { icon } from './components/icons.js';

// ── Initialize Canvases ───────────────────────────────────
const bgCanvas = document.getElementById('canvas-bg');
const canvasEntities = document.getElementById('canvas-entities');
initCanvases(bgCanvas, canvasEntities);
window.addEventListener('resize', resizeCanvas);
initControls();

// ── Initialize Drawflow Node Editor ───────────────────────
const drawflowContainer = document.getElementById('drawflow-container');
const { editor } = createEditor(drawflowContainer);

// Register ALL node types (must happen before registerAllNodes)
registerFactionNode(editor);
registerRelationshipNode(editor);
registerUnitNode(editor);
registerStatNode(editor);
registerDeathNode(editor);
registerCombatNode(editor);
registerNavigationNode(editor);
registerWaypointNode(editor);
registerGeneralNode(editor);
registerAllNodes(editor);

// ── Helper: Add a node with proper HTML template ──────────
function addNodeWithTemplate(typeName, data = {}, posX = 250, posY = 300) {
    const html = getNodeHTML(typeName);
    const ports = getNodePorts(typeName);
    editor.addNode(typeName, ports.inputs, ports.outputs, posX, posY, typeName, data, html);
}

// ── Build UI Components ───────────────────────────────────

function buildTopBar() {
    const bar = document.getElementById('overlay-top-bar');
    bar.innerHTML = `
    <div class="overlay-top-bar__left">
      <span class="overlay-top-bar__title">SWARM<span style="color:var(--accent-primary)">CONTROL</span></span>
      <span style="font-family:var(--font-mono);font-size:10px;color:var(--text-tertiary)">v0.4.0</span>
    </div>
    <div class="overlay-top-bar__center" style="flex:1; display:flex; justify-content:center; align-items:center;">
        <span id="status-dot" class="status-dot-inline status-dot-inline--wait"></span>
        <span id="status-text" class="node-mono-value" style="font-size: 11px; margin-left: 6px; color: var(--text-secondary);">READY</span>
    </div>
    <div class="overlay-top-bar__actions">
      <select id="engine-mode-select" class="engine-mode-select" title="Engine Backend">
        <option value="auto">Auto</option>
        <option value="wasm">WASM</option>
        <option value="ws">WebSocket</option>
      </select>
      <button class="overlay-btn" id="btn-presets" title="Presets">${icon('layers')}</button>
      <button class="overlay-btn overlay-btn--launch" id="btn-launch" title="Compile & Launch">▶</button>
      <button class="overlay-btn" id="btn-focus" title="Focus Mode">${icon('eye')}</button>
      <button class="overlay-btn" id="btn-minimize" title="Toggle Editor">${icon('minus')}</button>
    </div>
  `;
}

function buildBottomToolbar() {
    const bar = document.getElementById('playground-bottom-toolbar');
    bar.innerHTML = `
    <div class="toolbar-group">
        <span class="toolbar-label">NODES</span>
        <button class="toolbar-pill" id="btn-add-faction" title="Add Faction node">
            ${icon('layers', 14)} Faction
        </button>
        <button class="toolbar-pill" id="btn-add-unit" title="Add Unit node">
            ${icon('user', 14)} Unit
        </button>
        <button class="toolbar-pill" id="btn-add-stat" title="Add Stat node">
            ${icon('barChart', 14)} Stat
        </button>
        <button class="toolbar-pill" id="btn-add-combat" title="Add Combat node">
            ${icon('swords', 14)} Combat
        </button>
        <button class="toolbar-pill" id="btn-add-relationship" title="Add Relationship node">
            ${icon('link', 14)} Rel
        </button>
        <button class="toolbar-pill" id="btn-add-nav" title="Add Navigation node">
            ${icon('compass', 14)} Nav
        </button>
        <button class="toolbar-pill" id="btn-add-death" title="Add Death node">
            ${icon('skull', 14)} Death
        </button>
        <button class="toolbar-pill" id="btn-add-waypoint" title="Add Waypoint node">
            ${icon('mapPin', 14)} Waypoint
        </button>
    </div>
    <div class="toolbar-separator"></div>
    <div class="toolbar-group">
        <span class="toolbar-label">TOOLS</span>
        <button class="toolbar-pill toolbar-pill--tool" id="btn-tool-select" title="Select entities (box drag)">
            ${icon('crosshair', 14)} Select
        </button>
        <button class="toolbar-pill toolbar-pill--tool" id="btn-tool-paint" title="Paint terrain">
            ${icon('edit', 14)} Terrain
        </button>
        <button class="toolbar-pill toolbar-pill--tool" id="btn-tool-spawn" title="Click to spawn">
            ${icon('plus', 14)} Spawn
        </button>
    </div>
    <div class="toolbar-separator"></div>
    <div class="toolbar-group">
        <span class="toolbar-label">SIM</span>
        <button class="toolbar-pill toolbar-pill--sim" id="btn-sim-play" title="Play/Pause">▶</button>
        <button class="toolbar-pill toolbar-pill--sim" id="btn-sim-step" title="Step 1 tick">⏭</button>
        <button class="toolbar-pill toolbar-pill--sim" id="btn-sim-reset" title="Kill all">✕</button>
    </div>
    `;
}

buildTopBar();
buildBottomToolbar();

// ── Build Right-Side Panel Cluster ────────────────────────
function buildRightPanels() {
    const cluster = document.getElementById('playground-right-cluster');
    if (!cluster) return;

    cluster.innerHTML = `
    <div class="pg-panel" id="pg-panel-telemetry">
        <div class="pg-panel__header">
            <span class="pg-panel__title">TELEMETRY</span>
        </div>
        <div class="pg-panel__body">
            <div class="pg-stat-row"><span class="pg-stat-label">Entities</span><span class="pg-stat-value" id="pg-entity-count">0</span></div>
            <div class="pg-stat-row"><span class="pg-stat-label">TPS</span><span class="pg-stat-value" id="pg-tps">0</span></div>
            <div class="pg-stat-row"><span class="pg-stat-label">Tick</span><span class="pg-stat-value" id="pg-tick">0</span></div>
            <div class="pg-stat-row"><span class="pg-stat-label">Factions</span><span class="pg-stat-value" id="pg-factions">0</span></div>
        </div>
    </div>
    <div class="pg-panel" id="pg-panel-inspector">
        <div class="pg-panel__header">
            <span class="pg-panel__title">INSPECTOR</span>
        </div>
        <div class="pg-panel__body" id="pg-inspector-body">
            <span class="pg-hint">Hover over entities to inspect</span>
        </div>
    </div>
    `;
}
buildRightPanels();

// ── Preset Gallery ────────────────────────────────────────
const openGallery = () => {
    showPresetGallery({
        onSelect: (presetKey) => {
            hidePresetGallery();
            localStorage.setItem('playground_has_visited', 'true');
            setTimeout(() => {
                try {
                    const graphJson = presetToGraph(presetKey);
                    editor.import(graphJson);
                    console.log(`[Preset] Loaded '${presetKey}'`);
                } catch (e) {
                    console.error('[Preset] Failed to load:', presetKey, e);
                }
            }, 400);
        },
        onBlank: () => {
            hidePresetGallery();
            localStorage.setItem('playground_has_visited', 'true');
        }
    });
};

document.getElementById('btn-presets').addEventListener('click', openGallery);
if (!localStorage.getItem('playground_has_visited')) {
    openGallery();
}

// ── Launch Button ─────────────────────────────────────────
document.getElementById('btn-launch').addEventListener('click', async () => {
    const mode = document.getElementById('engine-mode-select')?.value || 'auto';
    showStatus('CONNECTING...', 'wait');

    try {
        const engine = await initEngine(mode);
        showStatus(engine.statusLabel(), 'ok');
    } catch (e) {
        showStatus('ENGINE FAILED', 'warn', 4000);
        console.error('[Launch] Engine init failed:', e);
        return;
    }

    const scenario = compileGraph(editor);
    if (scenario.errors && scenario.errors.length > 0) {
        console.error('Validation errors:', scenario.errors);
        showStatus(scenario.errors[0], 'warn', 4000);
        return;
    }
    showStatus('LAUNCHING...', 'ok');
    executeScenario(scenario, sendEngineCommand);
    setTimeout(() => {
        const eng = getEngine();
        showStatus(eng ? eng.statusLabel() : 'RUNNING', 'ok');
    }, 500);
});

function showStatus(text, type = 'ok', timeout = 0) {
    const statusText = document.getElementById('status-text');
    const statusDot = document.getElementById('status-dot');
    if (statusText && statusDot) {
        statusDot.className = `status-dot-inline status-dot-inline--${type}`;
        statusText.textContent = text;
        statusText.style.color = type === 'warn' ? 'var(--accent-danger, #ef4444)' : '';
        if (timeout > 0) {
            setTimeout(() => {
                statusDot.className = 'status-dot-inline status-dot-inline--ok';
                statusText.textContent = 'READY';
                statusText.style.color = '';
            }, timeout);
        }
    }
}

// ── Focus Mode ────────────────────────────────────────────
let focusMode = localStorage.getItem('playground_focus_mode') === 'true';
const updateFocusMode = () => {
    drawflowContainer.classList.toggle('drawflow-container--focus', focusMode);
};
updateFocusMode();

document.getElementById('btn-focus').addEventListener('click', () => {
    focusMode = !focusMode;
    localStorage.setItem('playground_focus_mode', focusMode);
    updateFocusMode();
});

// ── Minimize Node Editor ──────────────────────────────────
let isMinimized = false;
document.getElementById('btn-minimize').addEventListener('click', () => {
    isMinimized = !isMinimized;
    drawflowContainer.style.display = isMinimized ? 'none' : 'block';
});

// ── Add Node Buttons ──────────────────────────────────────
document.getElementById('btn-add-faction').addEventListener('click', () => {
    addNodeWithTemplate('faction', {
        name: 'New Faction', color: '#ef476f',
        spawnCount: 200, spawnX: 400, spawnY: 500, spawnSpread: 100
    }, 150 + Math.random() * 100, 200 + Math.random() * 100);
});
document.getElementById('btn-add-unit').addEventListener('click', () => {
    addNodeWithTemplate('unit', { unitName: 'Infantry', classId: 0 },
        400 + Math.random() * 100, 300 + Math.random() * 100);
});
document.getElementById('btn-add-stat').addEventListener('click', () => {
    addNodeWithTemplate('stat', { label: 'HP', statIndex: 0, initialValue: 100 },
        100 + Math.random() * 100, 500 + Math.random() * 100);
});
document.getElementById('btn-add-combat').addEventListener('click', () => {
    addNodeWithTemplate('combat', { attackType: 'melee', damage: -10, range: 15, cooldownTicks: 0 },
        400 + Math.random() * 100, 500 + Math.random() * 100);
});
document.getElementById('btn-add-relationship').addEventListener('click', () => {
    addNodeWithTemplate('relationship', { relationType: 'hostile' },
        300 + Math.random() * 100, 100 + Math.random() * 100);
});
document.getElementById('btn-add-nav').addEventListener('click', () => {
    addNodeWithTemplate('navigation', {},
        500 + Math.random() * 100, 100 + Math.random() * 100);
});
document.getElementById('btn-add-death').addEventListener('click', () => {
    addNodeWithTemplate('death', { condition: 'LessThanEqual', threshold: 0 },
        600 + Math.random() * 100, 400 + Math.random() * 100);
});
document.getElementById('btn-add-waypoint').addEventListener('click', () => {
    addNodeWithTemplate('waypoint', { x: 500, y: 500 },
        700 + Math.random() * 100, 100 + Math.random() * 100);
});

// ── Tool Buttons (Selection, Terrain, Spawn) ──────────────
const toolBtns = document.querySelectorAll('.toolbar-pill--tool');
function activateTool(toolId) {
    // Reset all tools
    toolBtns.forEach(b => b.classList.remove('toolbar-pill--active'));

    // clearModes is already imported at top
    clearModes();

    const btn = document.getElementById(toolId);
    if (btn) btn.classList.add('toolbar-pill--active');

    if (toolId === 'btn-tool-select') {
        S.setSelectionMode(true);
    } else if (toolId === 'btn-tool-paint') {
        S.setPaintMode(true);
        S.setActiveBrush('wall');
    } else if (toolId === 'btn-tool-spawn') {
        S.setSpawnMode(true);
    }
}

document.getElementById('btn-tool-select')?.addEventListener('click', () => activateTool('btn-tool-select'));
document.getElementById('btn-tool-paint')?.addEventListener('click', () => activateTool('btn-tool-paint'));
document.getElementById('btn-tool-spawn')?.addEventListener('click', () => activateTool('btn-tool-spawn'));

// ── Sim Control Buttons ───────────────────────────────────
document.getElementById('btn-sim-play')?.addEventListener('click', () => {
    sendEngineCommand('toggle_sim', {});
    const btn = document.getElementById('btn-sim-play');
    if (btn) {
        S.setIsPaused(!S.isPaused);
        btn.textContent = S.isPaused ? '▶' : '⏸';
    }
});
document.getElementById('btn-sim-step')?.addEventListener('click', () => {
    sendEngineCommand('step_sim', { ticks: 1 });
});
document.getElementById('btn-sim-reset')?.addEventListener('click', () => {
    sendEngineCommand('kill_all', { faction_id: 0 });
    sendEngineCommand('kill_all', { faction_id: 1 });
    sendEngineCommand('kill_all', { faction_id: 2 });
    showStatus('RESET', 'warn', 2000);
});

// ── Telemetry Update ──────────────────────────────────────
function updateTelemetry() {
    const entityCountEl = document.getElementById('pg-entity-count');
    const tpsEl = document.getElementById('pg-tps');
    const tickEl = document.getElementById('pg-tick');
    const factionsEl = document.getElementById('pg-factions');

    if (entityCountEl) entityCountEl.textContent = S.entities.size;
    if (tpsEl) tpsEl.textContent = S.tpsCounter || 0;
    if (tickEl) tickEl.textContent = S.currentTick || 0;

    // Count unique factions
    const factionSet = new Set();
    for (const [, ent] of S.entities) {
        factionSet.add(ent.faction_id);
    }
    if (factionsEl) factionsEl.textContent = factionSet.size;
}

// ── Inspector Update ──────────────────────────────────────
function updateInspector() {
    const body = document.getElementById('pg-inspector-body');
    if (!body) return;

    const wx = S.mouseWorldX;
    const wy = S.mouseWorldY;
    if (wx === null || wy === null || S.entities.size === 0) {
        return;
    }

    // Find nearest entity to mouse
    let nearest = null;
    let nearestDist = 30; // world-unit threshold
    for (const [id, ent] of S.entities) {
        const dist = Math.hypot(ent.x - wx, ent.y - wy);
        if (dist < nearestDist) {
            nearestDist = dist;
            nearest = {
                id,
                x: ent.x.toFixed(0),
                y: ent.y.toFixed(0),
                factionId: ent.faction_id,
                hp: ent.stats?.[0]?.toFixed(1) ?? '?',
            };
        }
    }

    if (nearest) {
        body.innerHTML = `
            <div class="pg-stat-row"><span class="pg-stat-label">Pos</span><span class="pg-stat-value">${nearest.x}, ${nearest.y}</span></div>
            <div class="pg-stat-row"><span class="pg-stat-label">Faction</span><span class="pg-stat-value">${nearest.factionId}</span></div>
            <div class="pg-stat-row"><span class="pg-stat-label">HP</span><span class="pg-stat-value">${nearest.hp}</span></div>
            <div class="pg-stat-row"><span class="pg-stat-label">ID</span><span class="pg-stat-value">${nearest.id}</span></div>
        `;
    }
}

// ── Render Loop ───────────────────────────────────────────
let frameCount = 0;
function renderFrame() {
    const ctx = canvasEntities.getContext('2d');
    ctx.clearRect(0, 0, canvasEntities.width, canvasEntities.height);
    drawEntities();
    if (S.showFog) drawFog();
    drawArenaBounds(ctx);

    // Update panels at reduced rate (every 10 frames)
    if (frameCount % 10 === 0) {
        updateTelemetry();
        updateInspector();
    }
    frameCount++;

    requestAnimationFrame(renderFrame);
}

resizeCanvas();
// NOTE: No connectWebSocket() here — playground connects only on Launch.
// This keeps the playground independent from training sessions.
requestAnimationFrame(renderFrame);
