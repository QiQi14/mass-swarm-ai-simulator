import { ADAPTER_CONFIG, ENTITY_RADIUS } from '../config.js';
import * as S from '../state.js';
import { worldToCanvas, getScaleFactor } from './terrain.js';

export function drawHealthBars(ctx, cullLeft, cullRight, cullTop, cullBottom) {
    const barW = 10, barH = 2;
    for (const ent of S.entities.values()) {
        if (!ent.stats || ent.stats[0] === undefined || ent.stats[0] >= 1.0) continue;

        const [cx, cy] = worldToCanvas(ent.x, ent.y);
        if (cx < cullLeft || cx > cullRight || cy < cullTop || cy > cullBottom) continue;

        const scale = getScaleFactor();
        const bw = barW * scale, bh = barH * scale;
        const hp = Math.max(0, ent.stats[0]);

        ctx.fillStyle = 'rgba(255,255,255,0.15)';
        ctx.fillRect(cx - bw / 2, cy - 8 * scale, bw, bh);

        const r = Math.round(255 * (1 - hp));
        const g = Math.round(255 * hp);
        ctx.fillStyle = `rgb(${r}, ${g}, 50)`;
        ctx.fillRect(cx - bw / 2, cy - 8 * scale, bw * hp, bh);
    }
}

export function drawDeathAnimations(ctx) {
    const now = performance.now();
    for (let i = S.deathAnimations.length - 1; i >= 0; i--) {
        const anim = S.deathAnimations[i];
        const elapsed = now - anim.startTime;
        if (elapsed > 500) { S.deathAnimations.splice(i, 1); continue; }

        const progress = elapsed / 500;
        const scale = getScaleFactor();
        const radius = (ENTITY_RADIUS + progress * ENTITY_RADIUS * 3) * scale;
        const alpha = 1.0 - progress;

        const [cx, cy] = worldToCanvas(anim.x, anim.y);
        const color = ADAPTER_CONFIG.factions[anim.factionId]?.color || '#fff';

        ctx.strokeStyle = color.replace(')', `, ${alpha})`).replace('rgb', 'rgba');
        if (ctx.strokeStyle === color) {
            ctx.globalAlpha = alpha;
            ctx.strokeStyle = color;
        }

        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.stroke();
        ctx.globalAlpha = 1.0;
    }
}
