import { WORLD_WIDTH, WORLD_HEIGHT, GRID_DIVISIONS, ADAPTER_CONFIG, COLOR_GRID, COLOR_GRID_MAJOR } from '../config.js';
import * as S from '../state.js';
import { worldToCanvas, getScaleFactor } from './terrain.js';

export function drawCoordinateGrid(ctx) {
    const cellWidth = WORLD_WIDTH / GRID_DIVISIONS;
    const cellHeight = WORLD_HEIGHT / GRID_DIVISIONS;

    for (let i = 0; i <= GRID_DIVISIONS; i++) {
        const x = i * cellWidth;
        const [cxStart, cyStart] = worldToCanvas(x, 0);
        const [cxEnd, cyEnd] = worldToCanvas(x, WORLD_HEIGHT);

        ctx.strokeStyle = (i % 10 === 0) ? COLOR_GRID_MAJOR : COLOR_GRID;
        ctx.lineWidth = (i % 10 === 0) ? 2 : 1;
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
        ctx.lineWidth = (i % 10 === 0) ? 2 : 1;
        ctx.beginPath();
        ctx.moveTo(cxStart, cyStart);
        ctx.lineTo(cxEnd, cyEnd);
        ctx.stroke();
    }
}

export function drawSpatialGrid(ctx) {
    const cellSize = 30;
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

export function drawFlowFieldArrows(ctx) {
    const scale = getScaleFactor();

    for (const [factionId, field] of S.flowFieldCache.entries()) {
        const color = ADAPTER_CONFIG.factions[factionId]?.color || '#fff';
        ctx.strokeStyle = color;
        ctx.fillStyle = color;
        ctx.lineWidth = 1;

        for (let y = 0; y < field.gridH; y++) {
            for (let x = 0; x < field.gridW; x++) {
                const vec = field.vectors[y * field.gridW + x];
                if (!vec || (vec[0] === 0 && vec[1] === 0)) continue;

                const wx = x * field.cellSize + field.cellSize / 2;
                const wy = y * field.cellSize + field.cellSize / 2;

                const [cx, cy] = worldToCanvas(wx, wy);
                const mag = 10 * scale;
                const angle = Math.atan2(vec[1], vec[0]);

                ctx.beginPath();
                ctx.moveTo(cx, cy);
                ctx.lineTo(cx + Math.cos(angle) * mag, cy + Math.sin(angle) * mag);
                ctx.stroke();

                ctx.beginPath();
                ctx.arc(cx + Math.cos(angle) * mag, cy + Math.sin(angle) * mag, 2 * scale, 0, Math.PI * 2);
                ctx.fill();
            }
        }
    }
}
