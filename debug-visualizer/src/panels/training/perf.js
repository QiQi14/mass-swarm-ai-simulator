import { PERF_SYSTEMS } from '../../config.js';
import { icon } from '../../components/icons.js';

let container = null;

export function updatePerfBars(telemetry) {
    if (!container) return;
    
    for (const sys of PERF_SYSTEMS) {
        const us = telemetry[sys.key] || 0;
        let row = container.querySelector(`#perf-${sys.key}`);
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
        fill.style.backgroundColor = us < 200 ? 'var(--accent-primary)' : us < 1000 ? 'var(--accent-warning)' : 'var(--accent-danger)';
        valueEl.textContent = us + 'µs';
    }
}

export default {
    id: 'perf',
    title: 'System Performance',
    icon: icon('zap'),
    modes: ['training'],
    defaultExpanded: false,
    render(body) {
        body.innerHTML = `<div class="perf-container" style="display: flex; flex-direction: column; gap: var(--space-xs);"></div>`;
        container = body.querySelector('.perf-container');
    }
};
