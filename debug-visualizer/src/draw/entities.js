import { ADAPTER_CONFIG, ENTITY_RADIUS, VELOCITY_VECTOR_SCALE, GRID_W, GRID_H, TERRAIN_CELL_SIZE, COLOR_VELOCITY, getFactionColor } from '../config.js';
import * as S from '../state.js';
import { getCtx, getCanvasEntities, getScaleFactor, worldToCanvas } from './terrain.js';
import { drawHealthBars, drawDeathAnimations } from './effects.js';

export { getFactionColor };

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

    // ── Observation Channel Overlays ───────────────────────────────────

    // Ch0 — Ally Density (faction 0 only)
    if (S.showDensityHeatmap && S.densityHeatmap) {
        drawDensityChannel(ctx, scale, S.densityHeatmap, 0, 120); // green hue for allies
    }

    // Ch1 — Enemy Density (all non-zero factions merged)
    if (S.showEnemyDensity && S.densityHeatmap) {
        for (const [factionIdStr, cells] of Object.entries(S.densityHeatmap)) {
            const fid = parseInt(factionIdStr, 10);
            if (fid === 0) continue; // skip allies
            drawDensityChannel(ctx, scale, S.densityHeatmap, fid, 0); // red hue for enemies
        }
    }

    // Ch4 — Terrain Cost visualization
    if (S.showTerrainCost) {
        drawTerrainCostOverlay(ctx, scale);
    }

    // Ch7 — Threat Density with GLOW effect for brightness differentiation
    if (S.showThreatDensity && S.ecpDensityMaps) {
        drawThreatGlow(ctx, scale, S.ecpDensityMaps);
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

    // Dim entities when any observation channel overlay is active
    const anyOverlayActive = S.showDensityHeatmap || S.showEnemyDensity || S.showTerrainCost || S.showThreatDensity;
    if (anyOverlayActive) ctx.globalAlpha = 0.3;

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

    if (anyOverlayActive) ctx.globalAlpha = 1.0;

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

// ── Channel Drawing Helpers ────────────────────────────────────────

/**
 * Draw a single faction's density as a heatmap overlay.
 * @param {number} factionId - Which faction to draw from the density data
 * @param {number} hue - HSL hue for the overlay color
 */
function drawDensityChannel(ctx, scale, densityData, factionId, hue) {
    const cells = densityData[factionId];
    if (!cells || cells.length < GRID_W * GRID_H) return;

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

/**
 * Draw terrain cost overlay (Ch4) from the local terrain grid.
 * Walls = solid, mud/pushable = semi-transparent.
 */
function drawTerrainCostOverlay(ctx, scale) {
    for (let y = 0; y < GRID_H; y++) {
        for (let x = 0; x < GRID_W; x++) {
            const idx = (y * GRID_W + x) * 2;
            const hard = S.terrainLocal[idx];

            // Skip passable terrain (cost 100 = normal)
            if (hard === 100) continue;

            let alpha, hue;
            if (hard === 65535) {
                // Wall — impassable
                alpha = 0.6;
                hue = 0; // red
            } else if (hard === 200) {
                // Mud — high cost
                alpha = 0.35;
                hue = 40; // amber
            } else if (hard === 125) {
                // Pushable — moderate cost
                alpha = 0.25;
                hue = 30; // orange
            } else {
                alpha = 0.15;
                hue = 60; // yellow for unknown
            }

            const worldX = x * TERRAIN_CELL_SIZE;
            const worldY = y * TERRAIN_CELL_SIZE;
            const [screenX, screenY] = worldToCanvas(worldX, worldY);
            const screenSize = TERRAIN_CELL_SIZE * scale;

            ctx.fillStyle = `hsla(${hue}, 80%, 55%, ${alpha})`;
            ctx.fillRect(screenX, screenY, screenSize + 1, screenSize + 1);
        }
    }
}

/**
 * Draw Ch7 Threat Density with multi-pass glow effect.
 * Merges all enemy faction densities, then renders:
 *  Pass 1: Wide outer glow (large shadowBlur) — shows threat zones
 *  Pass 2: Bright core fill — shows density concentration
 *  Pass 3: Hot-spot bloom on high-value cells — highlights strongest threats
 */
function drawThreatGlow(ctx, scale, densityData) {
    const cellCount = GRID_W * GRID_H;

    // Merge all enemy faction densities into a single threat grid
    const merged = new Float32Array(cellCount);
    for (const [factionIdStr, cells] of Object.entries(densityData)) {
        const fid = parseInt(factionIdStr, 10);
        if (fid === 0 || !cells || cells.length < cellCount) continue;
        for (let i = 0; i < cellCount; i++) {
            merged[i] += cells[i];
        }
    }

    // Find max for normalization
    let maxVal = 0;
    for (let i = 0; i < cellCount; i++) {
        if (merged[i] > maxVal) maxVal = merged[i];
    }
    if (maxVal < 0.001) return; // nothing to draw

    const screenCellSize = TERRAIN_CELL_SIZE * scale;

    // ── Pass 1: Outer glow halo ─────────────────────────────────
    ctx.save();
    ctx.shadowColor = 'rgba(200, 50, 255, 0.8)';
    ctx.shadowBlur = 16 * scale;
    for (let y = 0; y < GRID_H; y++) {
        for (let x = 0; x < GRID_W; x++) {
            const value = merged[y * GRID_W + x];
            if (value < 0.01) continue;

            const norm = value / maxVal;
            const [screenX, screenY] = worldToCanvas(x * TERRAIN_CELL_SIZE, y * TERRAIN_CELL_SIZE);

            // Outer glow — wider, dimmer
            const glowAlpha = norm * 0.4;
            ctx.fillStyle = `rgba(180, 60, 255, ${glowAlpha})`;
            ctx.fillRect(screenX - 2, screenY - 2, screenCellSize + 4, screenCellSize + 4);
        }
    }
    ctx.restore();

    // ── Pass 2: Bright core fill ────────────────────────────────
    for (let y = 0; y < GRID_H; y++) {
        for (let x = 0; x < GRID_W; x++) {
            const value = merged[y * GRID_W + x];
            if (value < 0.01) continue;

            const norm = value / maxVal;
            const [screenX, screenY] = worldToCanvas(x * TERRAIN_CELL_SIZE, y * TERRAIN_CELL_SIZE);

            // Core: shift from cool purple (low) → hot magenta/white (high)
            const lightness = 45 + norm * 30; // 45% → 75%
            const sat = 90 - norm * 20;       // 90% → 70% (whiter at peak)
            const alpha = 0.15 + norm * 0.55;
            ctx.fillStyle = `hsla(280, ${sat}%, ${lightness}%, ${alpha})`;
            ctx.fillRect(screenX, screenY, screenCellSize + 1, screenCellSize + 1);
        }
    }

    // ── Pass 3: Hot-spot bloom on high-value cells ──────────────
    ctx.save();
    ctx.shadowColor = 'rgba(255, 100, 255, 1)';
    ctx.shadowBlur = 24 * scale;
    for (let y = 0; y < GRID_H; y++) {
        for (let x = 0; x < GRID_W; x++) {
            const value = merged[y * GRID_W + x];
            const norm = value / maxVal;
            if (norm < 0.5) continue; // only bloom on top 50%

            const [screenX, screenY] = worldToCanvas(x * TERRAIN_CELL_SIZE, y * TERRAIN_CELL_SIZE);
            const bloomAlpha = (norm - 0.5) * 0.8; // 0 at 50%, 0.4 at 100%
            ctx.fillStyle = `rgba(255, 160, 255, ${bloomAlpha})`;
            ctx.fillRect(screenX + 2, screenY + 2, screenCellSize - 3, screenCellSize - 3);
        }
    }
    ctx.restore();
}
