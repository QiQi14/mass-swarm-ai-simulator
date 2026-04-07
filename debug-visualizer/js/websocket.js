// ─── WebSocket Client ───────────────────────────────────────────────

import { WS_URL, RECONNECT_INTERVAL_MS, ADAPTER_CONFIG } from './config.js';
import * as S from './state.js';
import { updatePerfBars, updateAggroGrid, updateLegend, updateMlBrainPanel, initFactionToggles } from './panels/index.js';
import { drawBackground } from './draw/index.js';

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
 * Show a temporary toast notification.
 */
export function showToast(message, type = 'info') {
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
