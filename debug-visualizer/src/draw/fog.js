import { GRID_W, GRID_H, TERRAIN_CELL_SIZE } from '../config.js';
import * as S from '../state.js';
import { worldToCanvas, getCanvasEntities, getCtx } from './terrain.js';

const fogCanvas = document.createElement('canvas');
const fogCtx = fogCanvas.getContext('2d');

export function drawFog() {
    if (!S.fogVisible || !S.fogExplored) return;

    const canvasEntities = getCanvasEntities();
    if (fogCanvas.width !== canvasEntities.width || fogCanvas.height !== canvasEntities.height) {
        fogCanvas.width = canvasEntities.width;
        fogCanvas.height = canvasEntities.height;
    }

    fogCtx.globalCompositeOperation = 'source-over';
    fogCtx.fillStyle = 'rgba(0,0,0,1)';
    fogCtx.fillRect(0, 0, fogCanvas.width, fogCanvas.height);

    fogCtx.globalCompositeOperation = 'destination-out';

    function getBit(arr, idx) { return (arr[idx >> 5] >> (idx & 31)) & 1; }

    for (let y = 0; y < GRID_H; y++) {
        for (let x = 0; x < GRID_W; x++) {
            const idx = y * GRID_W + x;
            const vis = getBit(S.fogVisible, idx);
            const exp = getBit(S.fogExplored, idx);

            if (!exp) continue;

            const [cx, cy] = worldToCanvas(x * TERRAIN_CELL_SIZE, y * TERRAIN_CELL_SIZE);
            const [cx2, cy2] = worldToCanvas((x + 1) * TERRAIN_CELL_SIZE, (y + 1) * TERRAIN_CELL_SIZE);

            if (vis) {
                fogCtx.fillStyle = 'rgba(0, 0, 0, 1)';
            } else if (exp) {
                fogCtx.fillStyle = 'rgba(0, 0, 0, 0.5)';
            }
            fogCtx.fillRect(cx, cy, cx2 - cx + 1.5, cy2 - cy + 1.5);
        }
    }

    getCtx().drawImage(fogCanvas, 0, 0);
}
