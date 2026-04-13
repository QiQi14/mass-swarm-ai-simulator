import { WORLD_WIDTH, WORLD_HEIGHT, TERRAIN_CELL_SIZE, BRUSH_MAP, COLOR_BG, COLOR_GRID, COLOR_GRID_MAJOR, GRID_W, GRID_H } from '../config.js';
import * as S from '../state.js';
import { drawCoordinateGrid, drawSpatialGrid, drawFlowFieldArrows } from './overlays.js';

let bgCanvas, bgCtx, canvasEntities, ctx;

export function initCanvases(bg, ent) {
    bgCanvas = bg;
    bgCtx = bg.getContext('2d');
    canvasEntities = ent;
    ctx = ent.getContext('2d');
}

export function getCtx() { return ctx; }
export function getCanvasEntities() { return canvasEntities; }

export function getScaleFactor() {
    return Math.min(canvasEntities.width, canvasEntities.height) / Math.max(WORLD_WIDTH, WORLD_HEIGHT) * S.viewScale;
}

export function worldToCanvas(wx, wy) {
    const scale = getScaleFactor();
    const cx = (wx - S.viewX) * scale + canvasEntities.width / 2;
    // On mobile, draw map higher (30% from top instead of 50%)
    const yCenter = window.innerWidth <= 768 ? canvasEntities.height * 0.3 : canvasEntities.height / 2;
    const cy = (wy - S.viewY) * scale + yCenter;
    return [cx, cy];
}

export function canvasToWorld(cx, cy) {
    const scale = getScaleFactor();
    const wx = (cx - canvasEntities.width / 2) / scale + S.viewX;
    // On mobile, draw map higher (30% from top instead of 50%)
    const yCenter = window.innerWidth <= 768 ? canvasEntities.height * 0.3 : canvasEntities.height / 2;
    const wy = (cy - yCenter) / scale + S.viewY;
    return [wx, wy];
}

export function drawBackground() {
    bgCtx.clearRect(0, 0, bgCanvas.width, bgCanvas.height);
    bgCtx.fillStyle = COLOR_BG;
    bgCtx.fillRect(0, 0, bgCanvas.width, bgCanvas.height);

    drawTerrain(bgCtx);
    if (S.showGrid) drawCoordinateGrid(bgCtx);
    if (S.showSpatialGrid) drawSpatialGrid(bgCtx);
    if (S.showFlowField) drawFlowFieldArrows(bgCtx);
}

function drawTerrain(ctx) {
    for (let y = 0; y < GRID_H; y++) {
        for (let x = 0; x < GRID_W; x++) {
            const idx = (y * GRID_W + x) * 2;
            const hard = S.terrainLocal[idx];
            const soft = S.terrainLocal[idx + 1];

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

export function resizeCanvas() {
    bgCanvas.width = bgCanvas.clientWidth;
    bgCanvas.height = bgCanvas.clientHeight;
    canvasEntities.width = canvasEntities.clientWidth;
    canvasEntities.height = canvasEntities.clientHeight;
    drawBackground();
}
