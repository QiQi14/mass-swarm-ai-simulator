import { WORLD_WIDTH, WORLD_HEIGHT, ADAPTER_CONFIG, GRID_W, GRID_H } from '../config.js';
import * as S from '../state.js';
import { sendCommand, showToast } from '../websocket.js';
import { canvasToWorld, drawBackground, getScaleFactor, getCanvasEntities } from '../draw/index.js';
import { deselectEntity } from '../panels/index.js';
import { addPaintCell } from './paint.js';
import { handleSpawnClick } from './spawn.js';
import { handleZoneClick } from './zones.js';
import { handleSplitClick, handleSelectClick } from './split.js';
import { applyPreset, getPresetKeys, getPreset, sendNavRule, sendInteractionRule, sendRemovalRule } from './algorithm-test.js';

let dragStartX = 0;
let dragStartY = 0;
let viewStartDragX = 0;
let viewStartDragY = 0;

export function clearModes() {
    const canvasEntities = getCanvasEntities();

    S.setSpawnMode(false);
    document.getElementById('spawn-mode-btn').classList.remove('active');
    document.getElementById('spawn-hint').style.display = 'none';
    canvasEntities.classList.remove('spawn-mode');

    S.setZoneMode(false);
    document.getElementById('zone-mode-btn').classList.remove('active');
    document.getElementById('zone-tools').style.display = 'none';
    document.getElementById('zone-hint').style.display = 'none';

    S.setSplitMode(false);
    document.getElementById('split-mode-btn').classList.remove('active');
    document.getElementById('split-tools').style.display = 'none';
    document.getElementById('split-hint').style.display = 'none';

    S.setPaintMode(false);
    document.getElementById('paint-mode-btn').classList.remove('active');
    document.getElementById('brush-tools').style.display = 'none';
    document.getElementById('canvas-bg').classList.remove('paint-mode');
    canvasEntities.classList.remove('paint-mode');
}

export function initControls() {
    const canvasEntities = getCanvasEntities();

    // --- Mouse Events ---

    canvasEntities.addEventListener("mousedown", (e) => {
        if (S.paintMode) {
            S.setIsPainting(true);
            S.resetPaintCellsBatch();
            const rect = canvasEntities.getBoundingClientRect();
            const [wx, wy] = canvasToWorld(e.clientX - rect.left, e.clientY - rect.top);
            addPaintCell(wx, wy);
            return;
        }
        S.setIsDragging(true);
        S.setHasDragged(false);
        dragStartX = e.clientX;
        dragStartY = e.clientY;
        viewStartDragX = S.viewX;
        viewStartDragY = S.viewY;
    });

    window.addEventListener("mousemove", (e) => {
        if (e.target === canvasEntities) {
            const rect = canvasEntities.getBoundingClientRect();
            const [wx, wy] = canvasToWorld(e.clientX - rect.left, e.clientY - rect.top);
            S.setMouseWorldX(wx);
            S.setMouseWorldY(wy);
            if (S.paintMode && S.isPainting) {
                addPaintCell(wx, wy);
                return;
            }
        } else {
            S.setMouseWorldX(null);
            S.setMouseWorldY(null);
        }

        if (S.isDragging) {
            const dx = e.clientX - dragStartX;
            const dy = e.clientY - dragStartY;

            if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
                S.setHasDragged(true);
            }

            const scale = getScaleFactor();
            S.setViewX(viewStartDragX - dx / scale);
            S.setViewY(viewStartDragY - dy / scale);
            drawBackground();
        }
    });

    window.addEventListener("mouseup", (e) => {
        if (S.paintMode && S.isPainting) {
            S.setIsPainting(false);
            if (S.paintCellsBatch.length > 0) {
                sendCommand("set_terrain", { cells: S.paintCellsBatch });
            }
            return;
        }

        if (S.isDragging && !S.hasDragged && e.target === canvasEntities) {
            const rect = canvasEntities.getBoundingClientRect();
            const [wx, wy] = canvasToWorld(e.clientX - rect.left, e.clientY - rect.top);

            if (S.spawnMode) {
                handleSpawnClick(wx, wy);
            } else if (S.zoneMode) {
                handleZoneClick(wx, wy);
            } else if (S.splitMode) {
                handleSplitClick(wx, wy);
            } else {
                handleSelectClick(wx, wy);
            }
        }
        S.setIsDragging(false);
    });

    canvasEntities.addEventListener("wheel", (e) => {
        e.preventDefault();
        const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
        const rect = canvasEntities.getBoundingClientRect();
        const cx = e.clientX - rect.left;
        const cy = e.clientY - rect.top;

        const [wxBefore, wyBefore] = canvasToWorld(cx, cy);
        S.setViewScale(Math.max(0.5, Math.min(20.0, S.viewScale * zoomFactor)));
        const [wxAfter, wyAfter] = canvasToWorld(cx, cy);

        S.setViewX(S.viewX + (wxBefore - wxAfter));
        S.setViewY(S.viewY + (wyBefore - wyAfter));
        drawBackground();
    });

    canvasEntities.addEventListener("dblclick", () => {
        S.setViewX(WORLD_WIDTH / 2);
        S.setViewY(WORLD_HEIGHT / 2);
        S.setViewScale(1.0);
        drawBackground();
    });

    // --- UI Buttons ---

    document.getElementById('insp-deselect').addEventListener('click', deselectEntity);

    document.getElementById('play-pause-btn').onclick = () => {
        S.setIsPaused(!S.isPaused);
        sendCommand("toggle_sim");
        document.getElementById('play-pause-btn').textContent = S.isPaused ? "Resume" : "Pause";
    };

    document.getElementById('step-btn').onclick = () => {
        const count = parseInt(document.getElementById('step-count-input').value) || 1;
        sendCommand("step", { count });
    };

    // Layer toggles
    document.getElementById('toggle-grid').onchange = (e) => { S.setShowGrid(e.target.checked); drawBackground(); };
    document.getElementById('toggle-spatial-grid').onchange = (e) => { S.setShowSpatialGrid(e.target.checked); drawBackground(); };
    document.getElementById('toggle-flow-field').onchange = (e) => { S.setShowFlowField(e.target.checked); drawBackground(); };
    document.getElementById('toggle-velocity').onchange = (e) => { S.setShowVelocity(e.target.checked); };
    document.getElementById('toggle-density-heatmap').onchange = (e) => { S.setShowDensityHeatmap(e.target.checked); };
    document.getElementById('toggle-zone-modifiers').onchange = (e) => { S.setShowZoneModifiers(e.target.checked); };
    document.getElementById('toggle-override-markers').onchange = (e) => { S.setShowOverrideMarkers(e.target.checked); };

    // Range/number sync
    const syncPair = (sliderId, numberId) => {
        document.getElementById(sliderId).oninput = (e) => document.getElementById(numberId).value = e.target.value;
        document.getElementById(numberId).oninput = (e) => document.getElementById(sliderId).value = e.target.value;
    };
    syncPair('spawn-amount-slider', 'spawn-amount');
    syncPair('spawn-spread-slider', 'spawn-spread');
    syncPair('zone-radius-slider', 'zone-radius');
    syncPair('zone-intensity-slider', 'zone-intensity');
    syncPair('split-pct-slider', 'split-pct');

    // --- Mode Toggles ---

    document.getElementById('spawn-mode-btn').onclick = () => {
        const wasSpawn = S.spawnMode;
        clearModes();
        S.setSpawnMode(!wasSpawn);
        document.getElementById('spawn-mode-btn').classList.toggle('active', S.spawnMode);
        document.getElementById('spawn-hint').style.display = S.spawnMode ? 'block' : 'none';
        canvasEntities.classList.toggle('spawn-mode', S.spawnMode);
        if (S.spawnMode) showToast('Spawn mode ON', 'info');
    };

    document.getElementById('zone-mode-btn').onclick = () => {
        const wasZone = S.zoneMode;
        clearModes();
        S.setZoneMode(!wasZone);
        document.getElementById('zone-mode-btn').classList.toggle('active', S.zoneMode);
        document.getElementById('zone-tools').style.display = S.zoneMode ? 'block' : 'none';
        document.getElementById('zone-hint').style.display = S.zoneMode ? 'block' : 'none';
        if (S.zoneMode) showToast('Zone Place mode ON', 'info');
    };

    document.querySelectorAll('.zone-type-btn').forEach(btn => {
        btn.onclick = () => {
            document.querySelectorAll('.zone-type-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            S.setActiveZoneType(btn.dataset.type);
        };
    });

    document.getElementById('split-mode-btn').onclick = () => {
        const wasSplit = S.splitMode;
        clearModes();
        S.setSplitMode(!wasSplit);
        document.getElementById('split-mode-btn').classList.toggle('active', S.splitMode);
        document.getElementById('split-tools').style.display = S.splitMode ? 'block' : 'none';
        document.getElementById('split-hint').style.display = S.splitMode ? 'block' : 'none';
        canvasEntities.classList.toggle('spawn-mode', S.splitMode);
        if (S.splitMode) showToast('Split mode ON — click to set epicenter', 'info');
    };

    document.getElementById('paint-mode-btn').onclick = () => {
        const wasPaint = S.paintMode;
        clearModes();
        S.setPaintMode(!wasPaint);
        document.getElementById('paint-mode-btn').classList.toggle('active', S.paintMode);
        document.getElementById('brush-tools').style.display = S.paintMode ? 'flex' : 'none';
        document.getElementById('canvas-bg').classList.toggle('paint-mode', S.paintMode);
        canvasEntities.classList.toggle('paint-mode', S.paintMode);
    };

    document.querySelectorAll('.brush-btn').forEach(btn => {
        btn.onclick = () => {
            document.querySelectorAll('.brush-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            S.setActiveBrush(btn.dataset.brush);
        };
    });

    // --- Faction Management ---

    const addFactionModal = document.getElementById('add-faction-modal');
    const addFactionInput = document.getElementById('add-faction-input');

    document.getElementById('add-faction-btn').onclick = () => {
        addFactionModal.style.display = 'flex';
        addFactionInput.value = '';
        addFactionInput.focus();
    };

    document.getElementById('add-faction-cancel').onclick = () => {
        addFactionModal.style.display = 'none';
    };

    document.getElementById('add-faction-confirm').onclick = () => {
        const name = addFactionInput.value.trim();
        addFactionModal.style.display = 'none';
        if (!name) return;
        
        const id = S.bumpNextFactionId();
        const hue = (id * 137) % 360;
        ADAPTER_CONFIG.factions[id] = { name, color: `hsl(${hue}, 70%, 55%)` };
        // Re-import to refresh toggles
        import('../panels/index.js').then(m => m.initFactionToggles());
        document.getElementById('spawn-faction').value = id;
        showToast(`Added faction: ${name} (ID: ${id})`, 'success');
    };

    document.getElementById('delete-faction-btn').onclick = () => {
        const fid = parseInt(document.getElementById('spawn-faction').value);
        if (isNaN(fid)) return;
        const fName = ADAPTER_CONFIG.factions[fid]?.name || `Faction ${fid}`;
        if (!confirm(`Delete faction "${fName}"? This will kill all its units.`)) return;
        sendCommand('kill_all', { faction_id: fid });
        delete ADAPTER_CONFIG.factions[fid];
        import('../panels/index.js').then(m => m.initFactionToggles());
        showToast(`Deleted faction: ${fName}`, 'warn');
    };

    // --- Terrain Commands ---

    document.getElementById('clear-terrain-btn').onclick = () => {
        sendCommand("clear_terrain", {});
        for (let i = 0; i < S.terrainLocal.length; i++) S.terrainLocal[i] = 100;
        drawBackground();
    };

    document.getElementById('save-scenario-btn').onclick = () => sendCommand("save_scenario", {});

    document.getElementById('load-scenario-btn').onclick = () => {
        document.getElementById('scenario-file-input').click();
    };

    document.getElementById('scenario-file-input').onchange = (e) => {
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
                            S.terrainLocal[i * 2] = data.terrain.hard_costs[i] || 100;
                            S.terrainLocal[i * 2 + 1] = data.terrain.soft_costs[i] || 100;
                        }
                    }
                    drawBackground();
                }
            } catch (err) {
                console.error("Failed to parse scenario file", err);
            }
        };
        reader.readAsText(file);
        document.getElementById('scenario-file-input').value = '';
    };

    // --- Algorithm Test ---

    const presetSelect = document.getElementById('preset-select');
    if (presetSelect) {
        getPresetKeys().forEach(key => {
            const opt = document.createElement('option');
            opt.value = key;
            opt.textContent = getPreset(key).label;
            presetSelect.appendChild(opt);
        });
        presetSelect.onchange = (e) => {
            const preset = getPreset(e.target.value);
            if (preset) {
                document.getElementById('preset-description').textContent = preset.description;
            }
        };
        // Trigger initial description
        if (presetSelect.options.length > 0) {
            presetSelect.onchange({ target: presetSelect });
        }
    }

    const loadPresetBtn = document.getElementById('load-preset-btn');
    if (loadPresetBtn) {
        loadPresetBtn.onclick = () => {
            const key = document.getElementById('preset-select').value;
            if (key) {
                applyPreset(key);
                showToast(`Loaded Preset: ${getPreset(key).label}`, 'info');
            }
        };
    }

    const toggleManualTestBtn = document.getElementById('toggle-manual-test-btn');
    if (toggleManualTestBtn) {
        toggleManualTestBtn.onclick = () => {
            const manualControls = document.getElementById('manual-test-controls');
            if (manualControls.style.display === 'none') {
                manualControls.style.display = 'flex';
                toggleManualTestBtn.classList.add('active');
            } else {
                manualControls.style.display = 'none';
                toggleManualTestBtn.classList.remove('active');
            }
        };
    }

    const applyNavBtn = document.getElementById('apply-nav-btn');
    if (applyNavBtn) {
        applyNavBtn.onclick = () => {
            const follower = document.getElementById('nav-follower').value;
            const targetType = document.getElementById('nav-target-type').value;
            const targetVal = document.getElementById('nav-target-val').value;
            if (follower && targetVal) {
                sendNavRule(follower, targetType, targetVal);
                showToast('Navigation Rule applied', 'info');
            }
        };
    }

    const applyIntBtn = document.getElementById('apply-int-btn');
    if (applyIntBtn) {
        applyIntBtn.onclick = () => {
            const src = document.getElementById('int-src').value;
            const tgt = document.getElementById('int-tgt').value;
            const range = document.getElementById('int-range').value;
            const stat = document.getElementById('int-stat').value;
            const delta = document.getElementById('int-delta').value;
            if (src && tgt && range && stat && delta) {
                sendInteractionRule(src, tgt, range, stat, delta);
                showToast('Interaction Rule applied', 'info');
            }
        };
    }

    const applyRemBtn = document.getElementById('apply-rem-btn');
    if (applyRemBtn) {
        applyRemBtn.onclick = () => {
            const stat = document.getElementById('rem-stat').value;
            const cond = document.getElementById('rem-cond').value;
            const thresh = document.getElementById('rem-thresh').value;
            if (stat && cond && thresh) {
                sendRemovalRule(stat, thresh, cond);
                showToast('Removal Rule applied', 'info');
            }
        };
    }
}
