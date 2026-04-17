import * as S from '../state.js';
import { worldToCanvas, getScaleFactor } from './terrain.js';
import { getSquadStats } from '../squads/squad-manager.js';
import { ENTITY_RADIUS } from '../config.js';

function getSquadEntityIds(squadId) {
  const ids = new Set();
  for (const [id, ent] of S.entities) {
    if (ent.faction_id === squadId) ids.add(id);
  }
  return ids;
}

function roundRect(ctx, x, y, width, height, radius) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
}

function drawDiamond(ctx, x, y, size) {
  ctx.beginPath();
  ctx.moveTo(x, y - size);
  ctx.lineTo(x + size, y);
  ctx.lineTo(x, y + size);
  ctx.lineTo(x - size, y);
  ctx.closePath();
  ctx.fill();
}

/**
 * Draw all tactical overlays on the entity canvas.
 * @param {CanvasRenderingContext2D} ctx
 * @param {number} cullLeft - Culling bounds
 * @param {number} cullRight - Culling bounds
 * @param {number} cullTop - Culling bounds
 * @param {number} cullBottom - Culling bounds
 */
export function drawTacticalOverlay(ctx, cullLeft, cullRight, cullTop, cullBottom) {
  drawSelectionBox(ctx);
  drawSelectedEntityHighlights(ctx, cullLeft, cullRight, cullTop, cullBottom);
  drawSquadBanners(ctx);
  drawOrderArrows(ctx);
  drawRallyPoints(ctx);
}

function drawSelectionBox(ctx) {
  if (!S.isBoxSelecting || !S.selectionBoxStart || !S.selectionBoxEnd) return;
  const [sx, sy] = worldToCanvas(S.selectionBoxStart.wx, S.selectionBoxStart.wy);
  const [ex, ey] = worldToCanvas(S.selectionBoxEnd.wx, S.selectionBoxEnd.wy);

  ctx.strokeStyle = 'rgba(6, 214, 160, 0.8)';  // accent-primary
  ctx.lineWidth = 1.5;
  ctx.setLineDash([4, 4]);
  ctx.strokeRect(sx, sy, ex - sx, ey - sy);
  ctx.setLineDash([]);

  ctx.fillStyle = 'rgba(6, 214, 160, 0.08)';
  ctx.fillRect(sx, sy, ex - sx, ey - sy);
}

function drawSelectedEntityHighlights(ctx, cullLeft, cullRight, cullTop, cullBottom) {
  if (S.selectedEntities.size === 0 && !S.activeSquadId) return;

  const targetSet = S.activeSquadId
    ? getSquadEntityIds(S.activeSquadId)  // highlight all squad members
    : S.selectedEntities;
    
  if (targetSet.size === 0) return;

  const scale = getScaleFactor();
  const radius = ENTITY_RADIUS * scale;

  ctx.strokeStyle = 'rgba(6, 214, 160, 0.6)';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  
  // Batch path
  for (const id of targetSet) {
    const ent = S.entities.get(id);
    if (!ent) continue;
    
    const [cx, cy] = worldToCanvas(ent.x, ent.y);
    if (cx >= cullLeft && cx <= cullRight && cy >= cullTop && cy <= cullBottom) {
        ctx.moveTo(cx + (radius + 3), cy);
        ctx.arc(cx, cy, radius + 3, 0, Math.PI * 2);
    }
  }
  ctx.stroke();
}

function drawSquadBanners(ctx) {
  if (!S.squads) return;
  for (const [squadId, info] of S.squads) {
    const stats = getSquadStats(squadId);
    if (stats.count === 0) continue;

    const [cx, cy] = worldToCanvas(stats.centroid.x, stats.centroid.y);

    // Banner background (glassmorphic pill)
    const text = `${info.name} (${stats.count})`;
    const metrics = ctx.measureText(text);
    const pw = metrics.width + 16;
    const ph = 22;

    ctx.fillStyle = 'rgba(6, 10, 16, 0.7)';
    roundRect(ctx, cx - pw / 2, cy - 30 - ph, pw, ph, 6);
    ctx.fill();

    // Border
    ctx.strokeStyle = info.color || 'rgba(255,255,255,0.2)';
    ctx.lineWidth = 1;
    roundRect(ctx, cx - pw / 2, cy - 30 - ph, pw, ph, 6);
    ctx.stroke();

    // Text
    ctx.fillStyle = '#e8ecf0';
    ctx.font = '11px "IBM Plex Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText(text, cx, cy - 30 - 6);

    // Order icon
    const orderIcon = { idle: '•', move: '→', attack: '⚔', hold: '■', retreat: '←' };
    ctx.fillStyle = info.currentOrder === 'attack' ? '#ef476f' : '#06d6a0';
    ctx.fillText(orderIcon[info.currentOrder] || '•', cx + pw / 2 + 8, cy - 30 - 6);
  }
}

function drawOrderArrows(ctx) {
  if (!S.squads) return;
  for (const [squadId, info] of S.squads) {
    if (!info.currentTarget) continue;
    const stats = getSquadStats(squadId);
    if (stats.count === 0) continue;

    const [sx, sy] = worldToCanvas(stats.centroid.x, stats.centroid.y);
    const [tx, ty] = worldToCanvas(info.currentTarget.x, info.currentTarget.y);

    // Pulsing dashed line
    const pulse = 0.4 + 0.3 * Math.sin(Date.now() / 400);
    ctx.strokeStyle = info.currentOrder === 'attack'
      ? `rgba(239, 71, 111, ${pulse})`
      : `rgba(6, 214, 160, ${pulse})`;
    ctx.lineWidth = 2;
    ctx.setLineDash([8, 4]);
    ctx.beginPath();
    ctx.moveTo(sx, sy);
    ctx.lineTo(tx, ty);
    ctx.stroke();
    ctx.setLineDash([]);

    // Target marker (diamond)
    ctx.fillStyle = ctx.strokeStyle;
    drawDiamond(ctx, tx, ty, 8);
  }
}

function drawRallyPoints(ctx) {
  if (!S.squads) return;
  for (const [squadId, info] of S.squads) {
    if (info.currentOrder !== 'move' || !info.currentTarget) continue;
    const [tx, ty] = worldToCanvas(info.currentTarget.x, info.currentTarget.y);

    // Animated concentric circles
    const t = (Date.now() % 2000) / 2000;
    const maxR = 20;
    ctx.strokeStyle = `rgba(6, 214, 160, ${1 - t})`;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(tx, ty, t * maxR, 0, Math.PI * 2);
    ctx.stroke();
  }
}
