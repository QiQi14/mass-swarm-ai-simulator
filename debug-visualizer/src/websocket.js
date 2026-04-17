// ─── WebSocket Client ───────────────────────────────────────────────

import { WS_URL, RECONNECT_INTERVAL_MS, ADAPTER_CONFIG, GRID_W, GRID_H } from './config.js';
import * as S from './state.js';
import { updatePerfBars } from './panels/training/perf.js';
import { updateAggroGrid, updateLegend, initFactionToggles } from './panels/shared/legend.js';
import { updateMlBrainPanel } from './panels/training/ml-brain.js';
import { drawBackground } from './draw/index.js';
export { showToast } from './components/toast.js';

/**
 * Establish WebSocket connection to the Rust micro-core.
 * Handles SyncDelta, FlowFieldSync, and scenario_data messages.
 */
export function connectWebSocket() {
    console.log("Connecting to WS...", WS_URL);
    const socket = new WebSocket(WS_URL);
    S.setWs(socket);

    socket.onopen = () => {
        document.getElementById("status-dot").className = "dot connected";
        document.getElementById("status-text").textContent = "Connected";
        S.entities.clear();
        S.flowFieldCache.clear();
        S.setCurrentTick(0);
        initFactionToggles();
    };

    socket.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            if (msg.type === "SyncDelta") {
                handleSyncDelta(msg);
            } else if (msg.type === "FlowFieldSync") {
                handleFlowFieldSync(msg);
            } else if (msg.type === "scenario_data") {
                handleScenarioData(msg);
            }
        } catch (e) {
            console.error("Failed to parse WS message", e);
        }
    };

    socket.onclose = () => {
        document.getElementById("status-dot").className = "dot disconnected";
        document.getElementById("status-text").textContent = "Disconnected";
        setTimeout(connectWebSocket, RECONNECT_INTERVAL_MS);
    };

    socket.onerror = () => {
        console.warn("WebSocket error occurred.");
    };
}

function handleSyncDelta(msg) {
    if (msg.tick) {
        if (msg.tick > S.currentTick) {
            S.addTpsCounter(msg.tick - S.currentTick);
        }
        S.setCurrentTick(msg.tick);
    }

    if (msg.moved) {
        for (const diff of msg.moved) {
            const existing = S.entities.get(diff.id) || { faction_id: 0, stats: [] };
            S.entities.set(diff.id, {
                ...existing,
                x: diff.x !== undefined ? diff.x : existing.x,
                y: diff.y !== undefined ? diff.y : existing.y,
                dx: diff.dx !== undefined ? diff.dx : existing.dx,
                dy: diff.dy !== undefined ? diff.dy : existing.dy,
                faction_id: diff.faction_id !== undefined ? diff.faction_id : existing.faction_id,
                stats: diff.stats !== undefined ? diff.stats : existing.stats,
            });
        }
    }

    if (msg.removed) {
        for (const id of msg.removed) {
            addDeathAnimation(id);
        }
    }

    // Auto-detect arena bounds from entity positions on spawn events
    // A spawn event = entity count jumps significantly (reset)
    if (msg.moved && msg.moved.length > 10) {
        autoDetectArenaBounds();
    }

    if (msg.telemetry) {
        updatePerfBars(msg.telemetry);
    }

    if (msg.visibility) {
        S.setActiveFogFaction(msg.visibility.faction_id);
        S.setFogExplored(new Uint32Array(msg.visibility.explored));
        S.setFogVisible(new Uint32Array(msg.visibility.visible));
    }

    if (msg.zone_modifiers !== undefined) S.setZoneModifiers(msg.zone_modifiers);

    if (msg.active_sub_factions !== undefined) {
        S.setActiveSubFactions(msg.active_sub_factions);
        updateLegend(msg.active_sub_factions);
    }

    if (msg.aggro_masks !== undefined) {
        // Rust sends AggroMaskSync { masks: { "0_1": false, ... } }
        const rawMasks = msg.aggro_masks.masks || msg.aggro_masks;
        const masksArray = Object.entries(rawMasks).map(([key, allow]) => {
            const [src, tgt] = key.split('_').map(Number);
            return { source_faction: src, target_faction: tgt, allow_combat: allow };
        });
        S.setAggroMasks(masksArray);
        updateAggroGrid(masksArray, Object.keys(ADAPTER_CONFIG.factions));
    }

    if (msg.ml_brain !== undefined) {
        S.setMlBrainStatus(msg.ml_brain);
        updateMlBrainPanel(msg.ml_brain);
    }

    if (msg.density_heatmap !== undefined) S.setDensityHeatmap(msg.density_heatmap);
    if (msg.ecp_density_maps !== undefined) S.setEcpDensityMaps(msg.ecp_density_maps);

    // Terrain data broadcast — sent once per environment reset
    if (msg.terrain_sync) {
        const t = msg.terrain_sync;
        const srcW = t.width;
        const srcH = t.height;

        // Store actual grid dimensions for drawTerrain
        S.setTerrainGridW(srcW);
        S.setTerrainGridH(srcH);
        if (t.cell_size) S.setTerrainCellSize(t.cell_size);

        // Clear existing terrain to default (100/100)
        for (let i = 0; i < S.terrainLocal.length; i++) S.terrainLocal[i] = 100;

        // Write broadcast data into terrainLocal using GRID_W stride
        // terrainLocal layout: interleaved [hard, soft] at (y * GRID_W + x) * 2
        const maxY = Math.min(srcH, GRID_H);
        const maxX = Math.min(srcW, GRID_W);
        for (let y = 0; y < maxY; y++) {
            for (let x = 0; x < maxX; x++) {
                const srcIdx = y * srcW + x;
                const dstIdx = (y * GRID_W + x) * 2;
                S.terrainLocal[dstIdx] = t.hard_costs[srcIdx];
                S.terrainLocal[dstIdx + 1] = t.soft_costs ? t.soft_costs[srcIdx] : 100;
            }
        }
        drawBackground(); // Force terrain redraw (walls + mud)
    }
}

function handleFlowFieldSync(msg) {
    S.flowFieldCache.set(msg.target_faction, {
        gridW: msg.grid_width,
        gridH: msg.grid_height,
        cellSize: msg.cell_size,
        vectors: msg.vectors,
    });
    drawBackground();
}

function handleScenarioData(msg) {
    const blob = new Blob([JSON.stringify(msg, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "scenario.json";
    a.click();
}

function addDeathAnimation(id) {
    const ent = S.entities.get(id);
    if (ent) {
        S.deathAnimations.push({
            x: ent.x, y: ent.y,
            startTime: performance.now(),
            factionId: ent.faction_id,
        });
    }
    S.entities.delete(id);
}

/**
 * Send a command to the Rust micro-core via WebSocket.
 */
export function sendCommand(cmd, params = {}) {
    if (S.ws && S.ws.readyState === WebSocket.OPEN) {
        S.ws.send(JSON.stringify({ type: "command", cmd, params }));
        return true;
    }
    return false;
}

/**
 * Auto-detect arena bounds from current entity positions.
 * Finds the bounding box, rounds up to nearest 100, and updates state.
 */
function autoDetectArenaBounds() {
    if (S.entities.size < 2) return;

    let maxX = 0, maxY = 0;
    for (const ent of S.entities.values()) {
        if (ent.x > maxX) maxX = ent.x;
        if (ent.y > maxY) maxY = ent.y;
    }

    // Round up to nearest 100 (+ buffer for spread)
    const w = Math.ceil((maxX + 50) / 100) * 100;
    const h = Math.ceil((maxY + 50) / 100) * 100;

    // Clamp to world bounds
    const clampedW = Math.min(1000, Math.max(200, w));
    const clampedH = Math.min(1000, Math.max(200, h));

    S.setArenaBounds({ x: 0, y: 0, width: clampedW, height: clampedH });

    // Update UI inputs
    const wInput = document.getElementById('arena-width');
    const hInput = document.getElementById('arena-height');
    if (wInput) wInput.value = clampedW;
    if (hInput) hInput.value = clampedH;
}
