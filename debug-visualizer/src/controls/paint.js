import { BRUSH_MAP, GRID_W, GRID_H, TERRAIN_CELL_SIZE } from '../config.js';
import * as S from '../state.js';
import { drawBackground } from '../draw/index.js';

export function addPaintCell(wx, wy) {
    const cx = Math.floor(wx / TERRAIN_CELL_SIZE);
    const cy = Math.floor(wy / TERRAIN_CELL_SIZE);
    if (cx >= 0 && cy >= 0 && cx < GRID_W && cy < GRID_H) {
        const brush = BRUSH_MAP[S.activeBrush] || BRUSH_MAP.wall;
        S.pushPaintCell({ x: cx, y: cy, hard: brush.hard, soft: brush.soft });
        // Local prediction
        S.terrainLocal[(cy * GRID_W + cx) * 2] = brush.hard;
        S.terrainLocal[(cy * GRID_W + cx) * 2 + 1] = brush.soft;
        drawBackground();
    }
}
