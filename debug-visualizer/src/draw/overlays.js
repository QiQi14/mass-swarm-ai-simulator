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

export function drawArenaBounds(ctx) {
    if (!S.showArenaBounds) return;

    const b = S.arenaBounds;
    const [x1, y1] = worldToCanvas(b.x, b.y);
    const [x2, y2] = worldToCanvas(b.x + b.width, b.y + b.height);
    const w = x2 - x1;
    const h = y2 - y1;
    const canvasW = ctx.canvas.width;
    const canvasH = ctx.canvas.height;

    // Dim the area OUTSIDE the arena (semi-transparent dark overlay)
    ctx.fillStyle = 'rgba(0, 0, 0, 0.35)';
    // Top strip
    ctx.fillRect(0, 0, canvasW, y1);
    // Bottom strip
    ctx.fillRect(0, y2, canvasW, canvasH - y2);
    // Left strip
    ctx.fillRect(0, y1, x1, h);
    // Right strip
    ctx.fillRect(x2, y1, canvasW - x2, h);

    // Draw dashed arena boundary
    ctx.strokeStyle = '#00e5ff';
    ctx.lineWidth = 2;
    ctx.setLineDash([8, 4]);
    ctx.strokeRect(x1, y1, w, h);
    ctx.setLineDash([]);

    // Corner markers (small solid squares)
    const markerSize = 6;
    ctx.fillStyle = '#00e5ff';
    ctx.fillRect(x1 - markerSize/2, y1 - markerSize/2, markerSize, markerSize);
    ctx.fillRect(x2 - markerSize/2, y1 - markerSize/2, markerSize, markerSize);
    ctx.fillRect(x1 - markerSize/2, y2 - markerSize/2, markerSize, markerSize);
    ctx.fillRect(x2 - markerSize/2, y2 - markerSize/2, markerSize, markerSize);

    // Label
    const scale = getScaleFactor();
    const fontSize = Math.max(10, 12 * scale);
    ctx.font = `600 ${fontSize}px Inter, sans-serif`;
    ctx.fillStyle = '#00e5ff';
    ctx.textAlign = 'left';
    ctx.fillText(`Arena ${b.width}\u00d7${b.height}`, x1 + 4, y1 - 6);
}
