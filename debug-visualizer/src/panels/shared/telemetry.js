import * as S from '../../state.js';
import { drawSparkline } from '../../components/sparkline.js';
import { getFactionColor, getFactionName } from '../../config.js';

let lastTickTime = performance.now();
const tpsSamples = [];
const entSamples = [];
let ui = null;
let factionContainer = null;
let factionUIs = new Map(); // Map<factionId, { el, countEl }>

export function startTelemetryLoop() {
    setInterval(() => {
        if (!ui) return;
        const now = performance.now();
        const deltaMs = now - lastTickTime;

        if (deltaMs > 0) {
            const tps = Math.round((S.tpsCounter / deltaMs) * 1000);
            S.setCurrentTps(tps);
            
            tpsSamples.push(tps);
            if (tpsSamples.length > 60) tpsSamples.shift();
            
            ui.tps.textContent = tps;
            drawSparkline(ui.tpsCanvas, tpsSamples);
        }

        S.setTpsCounter(0);
        lastTickTime = now;

        // Count entities by faction — fully dynamic, no hardcoding
        const factionCounts = new Map();
        for (const ent of S.entities.values()) {
            const fid = ent.faction_id;
            factionCounts.set(fid, (factionCounts.get(fid) || 0) + 1);
        }

        const size = S.entities.size;
        entSamples.push(size);
        if (entSamples.length > 60) entSamples.shift();

        ui.ent.textContent = size;
        drawSparkline(ui.entCanvas, entSamples, { strokeColor: '#118ab2', fillColor: 'rgba(17, 138, 178, 0.15)' });
        ui.tick.textContent = S.currentTick;

        // Update dynamic faction rows
        if (factionContainer) {
            updateFactionRows(factionCounts);
        }
    }, 1000);
}

// getFactionName and getFactionColor imported from config.js

function updateFactionRows(factionCounts) {
    // Sort factions by ID for consistent order
    const sortedFactions = [...factionCounts.keys()].sort((a, b) => a - b);

    for (const fid of sortedFactions) {
        const count = factionCounts.get(fid);

        if (!factionUIs.has(fid)) {
            // Create row for new faction
            const row = document.createElement('div');
            row.className = 'faction-row';
            const color = getFactionColor(fid);
            const name = getFactionName(fid);
            row.innerHTML = `
                <div class="faction-dot" style="background-color: ${color}; box-shadow: 0 0 6px ${color};"></div>
                <span class="faction-name">${name}</span>
                <span class="faction-count mono" style="color: ${color};">0</span>
            `;
            factionContainer.appendChild(row);
            factionUIs.set(fid, {
                el: row,
                countEl: row.querySelector('.faction-count')
            });
        }

        factionUIs.get(fid).countEl.textContent = count;
    }

    // Set factions not in current counts to 0, but keep them visible
    for (const [fid, { countEl }] of factionUIs) {
        if (!factionCounts.has(fid)) {
            countEl.textContent = '0';
        }
    }
}

export default {
    id: 'telemetry',
    title: 'Telemetry',
    icon: '📡',
    modes: ['training', 'playground'],
    defaultExpanded: true,
    render(body) {
        body.innerHTML = `
            <div class="stat-grid">
                <div class="stat-card">
                    <div class="stat-label">TPS</div>
                    <div class="stat-value mono" style="font-size: var(--font-size-sm);" id="stat-tps">0</div>
                    <canvas id="canvas-tps-spark" width="160" height="30" style="width: 100%; height: 30px; display: block; margin-top: 8px;"></canvas>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Tick</div>
                    <div class="stat-value mono" style="font-size: var(--font-size-sm);" id="stat-tick">0</div>
                </div>
                <div class="stat-card" style="grid-column: span 2;">
                    <div class="stat-label">Total Entities</div>
                    <div class="stat-value mono" style="font-size: var(--font-size-sm);" id="stat-entities">0</div>
                    <canvas id="canvas-ent-spark" width="300" height="30" style="width: 100%; height: 30px; display: block; margin-top: 8px;"></canvas>
                </div>
            </div>

            <hr class="panel-divider">
            <h4 class="section-heading">Faction Forces</h4>
            <div id="faction-forces" class="faction-list"></div>
        `;
        ui = {
            tps: body.querySelector('#stat-tps'),
            tpsCanvas: body.querySelector('#canvas-tps-spark'),
            tick: body.querySelector('#stat-tick'),
            ent: body.querySelector('#stat-entities'),
            entCanvas: body.querySelector('#canvas-ent-spark'),
        };
        factionContainer = body.querySelector('#faction-forces');
        factionUIs = new Map();
        
        if (!window.__telemetryLoopStarted) {
            window.__telemetryLoopStarted = true;
            startTelemetryLoop();
        }
    },
    update() {}
};
