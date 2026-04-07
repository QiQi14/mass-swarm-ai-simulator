import { ADAPTER_CONFIG, ENTITY_RADIUS, VELOCITY_VECTOR_SCALE, GRID_W, GRID_H, TERRAIN_CELL_SIZE, COLOR_VELOCITY } from '../config.js';
import * as S from '../state.js';
import { getCtx, getCanvasEntities, getScaleFactor, worldToCanvas } from './terrain.js';
import { drawHealthBars, drawDeathAnimations } from './effects.js';

export function getFactionColor(factionId) {
    if (ADAPTER_CONFIG.factions[factionId]) return ADAPTER_CONFIG.factions[factionId].color;
    const parent = factionId < 100 ? factionId : Math.floor(factionId / 100) - 1;
    const offset = (factionId % 100) * 30;
    const base = parent === 0 ? 220 : 0;
    return `hsl(${(base + offset) % 360}, 70%, 55%)`;
}

export function drawEntities() {
    const ctx = getCtx();
    const canvasEntities = getCanvasEntities();
    const scale = getScaleFactor();
    const radius = ENTITY_RADIUS * scale;

    const margin = 50;
    const cullLeft = -margin;
    const cullRight = canvasEntities.width + margin;
    const cullTop = -margin;
    const cullBottom = canvasEntities.height + margin;

    // Velocity vectors
    if (S.showVelocity) {
        ctx.strokeStyle = COLOR_VELOCITY;
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (const ent of S.entities.values()) {
            const [cx, cy] = worldToCanvas(ent.x, ent.y);
            if (cx >= cullLeft && cx <= cullRight && cy >= cullTop && cy <= cullBottom) {
                if (ent.dx !== undefined && ent.dy !== undefined && (ent.dx !== 0 || ent.dy !== 0)) {
                    const norm = Math.sqrt(ent.dx * ent.dx + ent.dy * ent.dy) || 1;
                    const vx = (ent.dx / norm) * VELOCITY_VECTOR_SCALE * scale;
                    const vy = (ent.dy / norm) * VELOCITY_VECTOR_SCALE * scale;
                    ctx.moveTo(cx, cy);
                    ctx.lineTo(cx + vx, cy + vy);
                }
            }
        }
        ctx.stroke();
    }

    // Density heatmap
    if (S.showDensityHeatmap && S.densityHeatmap) {
        const cellCount = GRID_W * GRID_H;
        const FACTION_HUE = { 0: 0, 1: 220 };

        for (const [factionIdStr, cells] of Object.entries(S.densityHeatmap)) {
            if (!cells || cells.length < cellCount) continue;
            const fid = parseInt(factionIdStr, 10);
            const hue = FACTION_HUE[fid] ?? 120;

            for (let y = 0; y < GRID_H; y++) {
                for (let x = 0; x < GRID_W; x++) {
                    const value = cells[y * GRID_W + x];
                    if (value < 0.001) continue;

                    const worldX = x * TERRAIN_CELL_SIZE;
                    const worldY = y * TERRAIN_CELL_SIZE;
                    const [screenX, screenY] = worldToCanvas(worldX, worldY);
                    const screenSize = TERRAIN_CELL_SIZE * scale;

                    const alpha = Math.min(Math.sqrt(value) * 0.7, 0.7);
                    ctx.fillStyle = `hsla(${hue}, 80%, 55%, ${alpha})`;
                    ctx.fillRect(screenX, screenY, screenSize + 1, screenSize + 1);
                }
            }
        }
    }

    // Zone modifiers
    if (S.showZoneModifiers && S.zoneModifiers) {
        for (const zone of S.zoneModifiers) {
            const [screenX, screenY] = worldToCanvas(zone.x, zone.y);
            const screenR = zone.radius * scale;

            ctx.beginPath();
            ctx.arc(screenX, screenY, screenR, 0, Math.PI * 2);

            if (zone.cost_modifier < 0) {
                const pulse = 0.3 + 0.2 * Math.sin(Date.now() / 300);
                ctx.fillStyle = `rgba(59, 130, 246, ${pulse})`;
                ctx.strokeStyle = 'rgba(59, 130, 246, 0.7)';
            } else {
                const pulse = 0.3 + 0.2 * Math.sin(Date.now() / 300);
                ctx.fillStyle = `rgba(239, 68, 68, ${pulse})`;
                ctx.strokeStyle = 'rgba(239, 68, 68, 0.7)';
            }

            ctx.fill();
            ctx.setLineDash([4, 4]);
            ctx.lineWidth = 2;
            ctx.stroke();
            ctx.setLineDash([]);

            ctx.fillStyle = '#fff';
            ctx.font = '11px Inter';
            ctx.textAlign = 'center';
            ctx.fillText(
                `${zone.cost_modifier > 0 ? '+' : ''}${zone.cost_modifier} (${zone.ticks_remaining}t)`,
                screenX, screenY
            );
        }
    }

    // Faction entities
    const activeFactionsSet = new Set();
    for (const ent of S.entities.values()) activeFactionsSet.add(ent.faction_id);

    for (const factionId of activeFactionsSet) {
        ctx.fillStyle = getFactionColor(factionId);
        ctx.beginPath();
        for (const ent of S.entities.values()) {
            if (ent.faction_id === factionId) {
                const [cx, cy] = worldToCanvas(ent.x, ent.y);
                if (cx >= cullLeft && cx <= cullRight && cy >= cullTop && cy <= cullBottom) {
                    ctx.moveTo(cx + radius, cy);
                    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
                }
            }
        }
        ctx.fill();
    }

    // Override markers
    if (S.showOverrideMarkers) {
        for (const ent of S.entities.values()) {
            if (ent.has_override) {
                const t = Date.now() / 200;
                const [cx, cy] = worldToCanvas(ent.x, ent.y);
                if (cx >= cullLeft && cx <= cullRight && cy >= cullTop && cy <= cullBottom) {
                    ctx.strokeStyle = `rgba(255, 215, 0, ${0.5 + 0.5 * Math.sin(t)})`;
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    ctx.moveTo(cx, cy - 6 * scale);
                    ctx.lineTo(cx + 6 * scale, cy);
                    ctx.lineTo(cx, cy + 6 * scale);
                    ctx.lineTo(cx - 6 * scale, cy);
                    ctx.closePath();
                    ctx.stroke();
                }
            }
        }
    }

    drawHealthBars(ctx, cullLeft, cullRight, cullTop, cullBottom);
    drawDeathAnimations(ctx);

    // Selected entity highlight
    if (S.selectedEntityId !== null) {
        const ent = S.entities.get(S.selectedEntityId);
        if (ent) {
            const [cx, cy] = worldToCanvas(ent.x, ent.y);
            ctx.strokeStyle = 'white';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(cx, cy, radius + 4 * scale, 0, Math.PI * 2);
            ctx.stroke();
        }
    }

    // Ghost spawn circle
    if (S.spawnMode && S.mouseWorldX !== null && S.mouseWorldY !== null && !S.isDragging) {
        const spread = parseFloat(document.getElementById('spawn-spread').value) || 0;
        const fid = parseInt(document.getElementById('spawn-faction').value);
        const fColor = ADAPTER_CONFIG.factions[fid]?.color || 'white';
        const [cx, cy] = worldToCanvas(S.mouseWorldX, S.mouseWorldY);

        if (spread > 0) {
            ctx.strokeStyle = fColor;
            ctx.globalAlpha = 0.5;
            ctx.setLineDash([5, 5]);
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(cx, cy, spread * scale, 0, Math.PI * 2);
            ctx.stroke();
            ctx.setLineDash([]);
            ctx.globalAlpha = 1.0;
        }

        ctx.strokeStyle = fColor;
        ctx.globalAlpha = 0.7;
        ctx.lineWidth = 1;
        const ch = 8;
        ctx.beginPath();
        ctx.moveTo(cx - ch, cy); ctx.lineTo(cx + ch, cy);
        ctx.moveTo(cx, cy - ch); ctx.lineTo(cx, cy + ch);
        ctx.stroke();
        ctx.globalAlpha = 1.0;
    }

    // Ghost split center
    if (S.splitMode && S.mouseWorldX !== null && S.mouseWorldY !== null && !S.isDragging) {
        const pct = parseInt(document.getElementById('split-pct').value) || 30;
        const splitSourceFaction = document.getElementById('split-source-faction');
        const fName = splitSourceFaction.options[splitSourceFaction.selectedIndex]?.text || "Faction";
        const [cx, cy] = worldToCanvas(S.mouseWorldX, S.mouseWorldY);

        ctx.strokeStyle = "#fff";
        ctx.globalAlpha = 0.8;
        ctx.lineWidth = 1;
        const ch = 10;
        ctx.beginPath();
        ctx.moveTo(cx - ch, cy); ctx.lineTo(cx + ch, cy);
        ctx.moveTo(cx, cy - ch); ctx.lineTo(cx, cy + ch);
        ctx.stroke();

        ctx.fillStyle = "#fff";
        ctx.font = '11px Inter';
        ctx.textAlign = 'left';
        ctx.fillText(`${pct}% of ${fName}`, cx + 15, cy + 4);
        ctx.globalAlpha = 1.0;
    }

    // Ghost zone center
    if (S.zoneMode && S.mouseWorldX !== null && S.mouseWorldY !== null && !S.isDragging) {
        const [cx, cy] = worldToCanvas(S.mouseWorldX, S.mouseWorldY);
        const screenR = (parseFloat(document.getElementById('zone-radius').value) || 100) * scale;

        if (S.activeZoneType === 'attract') {
            ctx.fillStyle = `rgba(59, 130, 246, 0.2)`;
            ctx.strokeStyle = `rgba(59, 130, 246, 0.6)`;
        } else {
            ctx.fillStyle = `rgba(239, 68, 68, 0.2)`;
            ctx.strokeStyle = `rgba(239, 68, 68, 0.6)`;
        }

        ctx.beginPath();
        ctx.arc(cx, cy, screenR, 0, Math.PI * 2);
        ctx.fill();
        ctx.setLineDash([4, 4]);
        ctx.stroke();
        ctx.setLineDash([]);
    }
}
