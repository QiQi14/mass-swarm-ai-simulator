import { WORLD_WIDTH, WORLD_HEIGHT } from '../config.js';
import * as S from '../state.js';
import { sendCommand } from '../websocket.js';
import { canvasToWorld, drawBackground, getScaleFactor, getCanvasEntities } from '../draw/index.js';
import { addPaintCell } from './paint.js';
import { handleSpawnClick } from './spawn.js';
import { handleZoneClick } from './zones.js';
import { handleSplitClick } from './split.js';
import { boxSelect, factionClickSelect } from './selection.js';
import { orderMove, orderAttack, orderHold, orderRetreat } from '../squads/order-system.js';
import { disbandSquad } from '../squads/squad-manager.js';
import { showToast } from '../components/toast.js';

let dragStartX = 0;
let dragStartY = 0;
let viewStartDragX = 0;
let viewStartDragY = 0;
let isRetreatMode = false;

export function clearModes() {
    const canvasEntities = getCanvasEntities();

    S.setSpawnMode(false);
    const spawnBtn = document.getElementById('spawn-mode-btn');
    if (spawnBtn) spawnBtn.classList.remove('active');
    const spawnHint = document.getElementById('spawn-hint');
    if (spawnHint) spawnHint.style.display = 'none';
    if (canvasEntities) canvasEntities.classList.remove('spawn-mode');

    S.setZoneMode(false);
    const zoneBtn = document.getElementById('zone-mode-btn');
    if (zoneBtn) zoneBtn.classList.remove('active');
    const zoneTools = document.getElementById('zone-tools');
    if (zoneTools) zoneTools.style.display = 'none';
    const zoneHint = document.getElementById('zone-hint');
    if (zoneHint) zoneHint.style.display = 'none';

    S.setSplitMode(false);
    const splitBtn = document.getElementById('split-mode-btn');
    if (splitBtn) splitBtn.classList.remove('active');
    const splitTools = document.getElementById('split-tools');
    if (splitTools) splitTools.style.display = 'none';
    const splitHint = document.getElementById('split-hint');
    if (splitHint) splitHint.style.display = 'none';

    S.setPaintMode(false);
    const paintBtn = document.getElementById('paint-mode-btn');
    if (paintBtn) paintBtn.classList.remove('active');
    const brushTools = document.getElementById('brush-tools');
    if (brushTools) brushTools.style.display = 'none';
    
    const canvasBg = document.getElementById('canvas-bg');
    if (canvasBg) canvasBg.classList.remove('paint-mode');
    if (canvasEntities) canvasEntities.classList.remove('paint-mode');

    S.setSelectionMode(false);
    const selectBtn = document.getElementById('select-mode-btn');
    if (selectBtn) selectBtn.classList.remove('active');
    S.setIsBoxSelecting(false);
    S.clearSelection();
}

export function initControls() {
    const canvasEntities = getCanvasEntities();
    if (!canvasEntities) return;

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
        if (S.selectionMode) {
            S.setIsBoxSelecting(true);
            S.setSelectionBoxStart({ wx, wy });
            S.setSelectionBoxEnd({ wx, wy });
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
            if (S.selectionMode && S.isBoxSelecting) {
                S.setSelectionBoxEnd({ wx, wy });
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

        if (S.selectionMode && S.isBoxSelecting) {
            S.setIsBoxSelecting(false);
            const start = S.selectionBoxStart;
            const end = S.selectionBoxEnd;
            if (start && end) {
                const dx = Math.abs(end.wx - start.wx);
                const dy = Math.abs(end.wy - start.wy);
                if (dx < 5 && dy < 5) {
                    const res = factionClickSelect(end.wx, end.wy);
                    if (res) S.setSelectedEntities(res.entities);
                    else S.clearSelection();
                } else {
                    const entities = boxSelect(start.wx, start.wy, end.wx, end.wy);
                    S.setSelectedEntities(entities);
                }
            }
            return;
        }

        if (S.isDragging && !S.hasDragged && e.target === canvasEntities) {
            const rect = canvasEntities.getBoundingClientRect();
            const [wx, wy] = canvasToWorld(e.clientX - rect.left, e.clientY - rect.top);

            if (isRetreatMode && S.activeSquadId) {
                orderRetreat(S.activeSquadId, wx, wy);
            } else if (S.spawnMode) {
                handleSpawnClick(wx, wy);
            } else if (S.zoneMode) {
                handleZoneClick(wx, wy);
            } else if (S.splitMode) {
                handleSplitClick(wx, wy);
            } else {
                // fallthrough
            }
        }
        S.setIsDragging(false);
    });

    // --- Touch Events ---
    canvasEntities.addEventListener("touchstart", (e) => {
        if (e.touches.length !== 1) return;
        const touch = e.touches[0];
        if (S.paintMode) {
            S.setIsPainting(true);
            S.resetPaintCellsBatch();
            const rect = canvasEntities.getBoundingClientRect();
            const [wx, wy] = canvasToWorld(touch.clientX - rect.left, touch.clientY - rect.top);
            addPaintCell(wx, wy);
            return;
        }
        S.setIsDragging(true);
        S.setHasDragged(false);
        dragStartX = touch.clientX;
        dragStartY = touch.clientY;
        viewStartDragX = S.viewX;
        viewStartDragY = S.viewY;
    }, { passive: true });

    window.addEventListener("touchmove", (e) => {
        if (!S.isDragging && (!S.paintMode || !S.isPainting)) return;
        if (e.touches.length !== 1) return;
        const touch = e.touches[0];
        
        if (e.target === canvasEntities) {
            const rect = canvasEntities.getBoundingClientRect();
            const [wx, wy] = canvasToWorld(touch.clientX - rect.left, touch.clientY - rect.top);
            S.setMouseWorldX(wx);
            S.setMouseWorldY(wy);
            if (S.paintMode && S.isPainting) {
                e.preventDefault();
                addPaintCell(wx, wy);
                return;
            }
        }
        
        if (S.isDragging) {
            e.preventDefault();
            const dx = touch.clientX - dragStartX;
            const dy = touch.clientY - dragStartY;

            if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
                S.setHasDragged(true);
            }

            const scale = getScaleFactor();
            S.setViewX(viewStartDragX - dx / scale);
            S.setViewY(viewStartDragY - dy / scale);
            drawBackground();
        }
    }, { passive: false });

    window.addEventListener("touchend", (e) => {
        if (S.paintMode && S.isPainting) {
            S.setIsPainting(false);
            if (S.paintCellsBatch.length > 0) {
                sendCommand("set_terrain", { cells: S.paintCellsBatch });
            }
            return;
        }

        if (S.isDragging && !S.hasDragged && e.target === canvasEntities) {
            const touch = e.changedTouches[0];
            const rect = canvasEntities.getBoundingClientRect();
            const [wx, wy] = canvasToWorld(touch.clientX - rect.left, touch.clientY - rect.top);

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

    canvasEntities.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        if (!S.activeSquadId) return;

        const rect = canvasEntities.getBoundingClientRect();
        const [wx, wy] = canvasToWorld(e.clientX - rect.left, e.clientY - rect.top);

        // Check if right-clicked on an enemy entity
        let nearestEnemy = null;
        let nearestDist = Infinity;
        for (const [id, ent] of S.entities) {
            if (ent.faction_id === S.activeSquadId) continue;  // skip own squad
            const squad = S.squads ? S.squads.get(S.activeSquadId) : null;
            if (squad && ent.faction_id === squad.parentFactionId) continue;  // skip allies
            const d = (ent.x - wx) ** 2 + (ent.y - wy) ** 2;
            if (d < nearestDist) { nearestDist = d; nearestEnemy = ent; }
        }

        if (nearestEnemy && nearestDist < 2500) {  // 50px radius
            // Attack-move toward enemy faction
            orderAttack(S.activeSquadId, nearestEnemy.faction_id);
            showToast(`Attacking faction ${nearestEnemy.faction_id}`, 'success');
        } else {
            // Move to waypoint
            orderMove(S.activeSquadId, wx, wy);
        }
    });

    window.addEventListener("keydown", (e) => {
        if (!S.activeSquadId) return;

        if (e.key.toLowerCase() === 'r') {
            isRetreatMode = true;
        } else if (e.key.toLowerCase() === 'h') {
            orderHold(S.activeSquadId);
        } else if (e.key === 'Delete' || e.key === 'Backspace') {
            disbandSquad(S.activeSquadId);
        } else if (e.key === 'Escape') {
            S.setActiveSquadId(null);
            S.clearSelection();
        }
    });

    window.addEventListener("keyup", (e) => {
        if (e.key.toLowerCase() === 'r') {
            isRetreatMode = false;
        }
    });
}
