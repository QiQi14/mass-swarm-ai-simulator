import { PERF_SYSTEMS, ADAPTER_CONFIG } from '../config.js';
import * as S from '../state.js';

export class Sparkline {
    constructor(canvasId, maxSamples = 60, color = '#30d158') {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.samples = [];
        this.maxSamples = maxSamples;
        this.color = color;
    }

    push(value) {
        this.samples.push(value);
        if (this.samples.length > this.maxSamples) this.samples.shift();
    }

    draw() {
        const { canvas, ctx, samples, color } = this;
        const w = canvas.width, h = canvas.height;
        ctx.clearRect(0, 0, w, h);
        if (samples.length < 2) return;

        const max = Math.max(...samples, 1);
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        for (let i = 0; i < samples.length; i++) {
            const x = (i / (this.maxSamples - 1)) * w;
            const y = h - (samples[i] / max) * (h - 2);
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.stroke();
    }
}

export const sparklines = {
    tps: new Sparkline('graph-tps', 60, '#30d158'),
    entities: new Sparkline('graph-entities', 60, '#0a84ff'),
};

export function updatePerfBars(telemetry) {
    const container = document.getElementById('perf-bars');
    for (const sys of PERF_SYSTEMS) {
        const us = telemetry[sys.key] || 0;
        let row = document.getElementById(`perf-${sys.key}`);
        if (!row) {
            row = document.createElement('div');
            row.id = `perf-${sys.key}`;
            row.className = 'perf-bar-row';
            row.innerHTML = `
                <span class="perf-bar-label">${sys.label}</span>
                <div class="perf-bar-track"><div class="perf-bar-fill"></div></div>
                <span class="perf-bar-value mono">0µs</span>`;
            container.appendChild(row);
        }
        const fill = row.querySelector('.perf-bar-fill');
        const valueEl = row.querySelector('.perf-bar-value');
        const pct = Math.min(100, (us / 2000) * 100);
        fill.style.width = pct + '%';
        fill.className = 'perf-bar-fill ' + (us < 200 ? 'green' : us < 1000 ? 'yellow' : 'red');
        valueEl.textContent = us + 'µs';
    }
}

export function updateInspectorPanel() {
    if (S.selectedEntityId === null) return;
    const ent = S.entities.get(S.selectedEntityId);
    if (!ent) { deselectEntity(); return; }

    const factionName = ADAPTER_CONFIG.factions[ent.faction_id]?.name || `Faction ${ent.faction_id}`;
    document.getElementById('insp-id').textContent = S.selectedEntityId;
    document.getElementById('insp-faction').textContent = factionName;
    document.getElementById('insp-pos').textContent = `(${ent.x.toFixed(1)}, ${ent.y.toFixed(1)})`;
    document.getElementById('insp-vel').textContent = `(${ent.dx.toFixed(2)}, ${ent.dy.toFixed(2)})`;
    document.getElementById('insp-stats').textContent = (ent.stats || []).map(s => s.toFixed(2)).join(', ');
}

export function deselectEntity() {
    S.setSelectedEntityId(null);
    document.getElementById('inspector-panel').style.display = 'none';
}

let lastTickTime = performance.now();

export function startTelemetryLoop() {
    setInterval(() => {
        const now = performance.now();
        const deltaMs = now - lastTickTime;

        if (deltaMs > 0) {
            const tps = Math.round((S.tpsCounter / deltaMs) * 1000);
            S.setCurrentTps(tps);
            document.getElementById("stat-tps").textContent = tps;
            sparklines.tps.push(tps);
            sparklines.tps.draw();
        }

        S.setTpsCounter(0);
        lastTickTime = now;

        let swarmCount = 0;
        let defCount = 0;
        for (const ent of S.entities.values()) {
            if (ent.faction_id === 0) swarmCount++;
            else if (ent.faction_id === 1) defCount++;
        }

        document.getElementById("stat-entities").textContent = S.entities.size;
        sparklines.entities.push(S.entities.size);
        sparklines.entities.draw();
        document.getElementById("stat-swarm").textContent = swarmCount;
        document.getElementById("stat-defender").textContent = defCount;
        document.getElementById("stat-tick").textContent = S.currentTick;
    }, 1000);
}

export * from './ml-panel.js';
export * from './zone-panel.js';
export * from './faction-panel.js';
