export let ui = null;

export function updateMlBrainPanel(mlBrain) {
    if (!ui || !mlBrain) return;

    ui.python.textContent = mlBrain.python_connected ? '🟢 Connected' : '🔴 Disconnected';
    ui.python.style.color = mlBrain.python_connected ? 'var(--status-connected)' : 'var(--status-disconnected)';

    ui.intervention.textContent = mlBrain.intervention_active ? '⚠️ Active' : '✅ Normal';
    ui.intervention.style.color = mlBrain.intervention_active ? 'var(--accent-warning)' : 'var(--status-connected)';

    if (mlBrain.last_directive) {
        try {
            let d = JSON.parse(mlBrain.last_directive);
            if (d.type === 'macro_directives' && Array.isArray(d.directives)) {
                d = d.directives[0] || {};
            }

            let summary = d.directive || 'Unknown';
            if (d.directive === 'Hold') summary = '⏸ Hold (Brake)';
            else if (d.directive === 'Idle') summary = '💤 Idle';
            else if (d.directive === 'SplitFaction') summary = `✂️ Split ${Math.round(d.percentage * 100)}% → sub ${d.new_sub_faction}`;
            else if (d.directive === 'SetZoneModifier') summary = `${d.cost_modifier < 0 ? '🧲 Attract' : '🚫 Repel'} at (${Math.round(d.x)}, ${Math.round(d.y)})`;
            else if (d.directive === 'UpdateNavigation') {
                const targetLabel = d.target?.faction_id !== undefined ? `Faction ${d.target.faction_id}` : d.target?.type || '?';
                summary = `⚔️ Attack → ${targetLabel}`;
            } else if (d.directive === 'ActivateBuff') summary = '🎯 Debuff Applied!';
            else if (d.directive === 'Retreat') summary = `🏃 Retreat → (${Math.round(d.retreat_x)}, ${Math.round(d.retreat_y)})`;

            ui.directive.textContent = summary;
        } catch {
            ui.directive.textContent = '—';
        }
    }
}

import * as S from '../../state.js';

export default {
    id: 'ml-brain',
    title: 'ML Brain Status',
    icon: '🧠',
    modes: ['training'],
    defaultExpanded: true,
    render(body) {
        body.innerHTML = `
            <div class="stat-grid">
                <div class="stat-card">
                    <div class="stat-label">Python Link</div>
                    <div class="stat-value mono" id="ml-python-status" style="font-size: var(--font-size-sm);">🟡 Waiting</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Intervention</div>
                    <div class="stat-value mono" id="ml-intervention" style="font-size: var(--font-size-sm);">—</div>
                </div>
                <div class="stat-card" style="grid-column: span 2; min-height: 52px; overflow: hidden;">
                    <div class="stat-label">Last Directive</div>
                    <div class="stat-value mono" id="ml-last-directive" style="font-size: var(--font-size-xs); line-height: 20px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">—</div>
                </div>
            </div>
        `;
        ui = {
            python: body.querySelector('#ml-python-status'),
            intervention: body.querySelector('#ml-intervention'),
            directive: body.querySelector('#ml-last-directive')
        };
    },
    update() {
        if (S.mlBrainStatus) {
            updateMlBrainPanel(S.mlBrainStatus);
        }
    }
};
