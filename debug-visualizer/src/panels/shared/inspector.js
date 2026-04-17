import * as S from '../../state.js';
import { getFactionColor, getFactionName, ADAPTER_CONFIG } from '../../config.js';
import { icon } from '../../components/icons.js';

let ui = null;
let lastSelectedId = null;
let _inspectorAccordionRef = null;
// Track previous stat values for delta indicators
let prevStats = null;

export function deselectEntity() {
    S.setSelectedEntityId(null);
    prevStats = null;
    if (_inspectorAccordionRef) {
        _inspectorAccordionRef.setExpanded(false);
    }
}

export function updateInspectorPanel() {
    if (!ui) return;
    const entId = S.selectedEntityId;

    if (entId === null) {
        ui.container.innerHTML = `<div class="inspector-empty">Click an entity on the canvas to inspect</div>`;
        prevStats = null;
        return;
    }

    const ent = S.entities.get(entId);
    if (!ent) { deselectEntity(); return; }

    const fName = getFactionName(ent.faction_id);
    const fColor = getFactionColor(ent.faction_id);
    const stats = ent.stats || [];

    // Build anonymous stat rows with meters
    let statRows = '';
    for (let i = 0; i < stats.length; i++) {
        const val = stats[i];
        if (val === 0 && (!prevStats || (prevStats[i] || 0) === 0)) continue; // hide always-zero

        // Delta indicator: compare with previous snapshot
        let deltaIcon = '';
        if (prevStats && prevStats[i] !== undefined) {
            const diff = val - prevStats[i];
            if (diff > 0.01) deltaIcon = '<span class="stat-delta up">+</span>';
            else if (diff < -0.01) deltaIcon = '<span class="stat-delta down">−</span>';
        }

        // Meter: normalize assuming max ~100 for stat 0, otherwise use raw value bar
        const maxVal = (i === 0) ? (ADAPTER_CONFIG.factions[ent.faction_id]?.stats?.hp || 100) : Math.max(val, 1);
        const pct = Math.max(0, Math.min(100, (val / maxVal) * 100));
        const barColor = (i === 0)
            ? (pct > 50 ? 'var(--accent-primary)' : pct > 25 ? 'var(--accent-warning)' : 'var(--accent-danger)')
            : 'var(--accent-secondary, #6366f1)';

        statRows += `
            <div class="insp-stat-row">
                <span class="insp-stat-label">S${i}</span>
                <div class="insp-hp-bar-wrapper">
                    <div class="insp-hp-bar" style="width: ${pct}%; background: ${barColor};"></div>
                </div>
                <span class="insp-stat-val mono">${val.toFixed(1)}</span>
                ${deltaIcon}
            </div>`;
    }

    // Save current stats for next delta comparison
    prevStats = [...stats];

    ui.container.innerHTML = `
        <div class="insp-header">
            <div class="insp-id mono">#${entId}</div>
            <div class="insp-faction" style="color: ${fColor};">
                <span class="faction-dot" style="background: ${fColor}; box-shadow: 0 0 6px ${fColor};"></span>
                ${fName}
            </div>
        </div>
        <div class="insp-row">
            <span class="insp-label">Position</span>
            <span class="insp-val mono">(${ent.x.toFixed(1)}, ${ent.y.toFixed(1)})</span>
        </div>
        <div class="insp-row">
            <span class="insp-label">Velocity</span>
            <span class="insp-val mono">(${ent.dx.toFixed(2)}, ${ent.dy.toFixed(2)})</span>
        </div>
        ${statRows ? `<hr class="panel-divider" style="margin: var(--space-xs) 0;"><div class="insp-stats-block">${statRows}</div>` : ''}
        <button class="btn secondary" style="width: 100%; margin-top: var(--space-sm);" id="insp-deselect-btn">Deselect</button>
    `;
    ui.container.querySelector('#insp-deselect-btn').onclick = deselectEntity;

    if (entId !== lastSelectedId) {
        lastSelectedId = entId;
        if (_inspectorAccordionRef) {
            _inspectorAccordionRef.setExpanded(true);
        }
    }
}

export default {
    id: 'inspector',
    title: 'Entity Inspector',
    icon: icon('eye'),
    modes: ['training', 'playground'],
    defaultExpanded: false,
    render(body) {
        body.innerHTML = `<div id="inspector-container"></div>`;
        ui = {
            container: body.querySelector('#inspector-container')
        };
        updateInspectorPanel();
    },
    update() {
        if (this._accordionRef) {
            _inspectorAccordionRef = this._accordionRef;
        }
        updateInspectorPanel();
    }
};
