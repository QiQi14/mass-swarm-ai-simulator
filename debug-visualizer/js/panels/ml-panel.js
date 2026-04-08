export function updateMlBrainPanel(mlBrain) {
    if (!mlBrain) return;

    const pythonEl = document.getElementById('ml-python-status');
    const interventionEl = document.getElementById('ml-intervention');
    const directiveEl = document.getElementById('ml-last-directive');

    if (pythonEl) {
        pythonEl.textContent = mlBrain.python_connected ? '🟢 Connected' : '🔴 Disconnected';
        pythonEl.style.color = mlBrain.python_connected ? '#22c55e' : '#ef4444';
    }

    if (interventionEl) {
        interventionEl.textContent = mlBrain.intervention_active ? '⚠️ Active' : '✅ Normal';
        interventionEl.style.color = mlBrain.intervention_active ? '#f59e0b' : '#22c55e';
    }

    if (directiveEl && mlBrain.last_directive) {
        try {
            let d = JSON.parse(mlBrain.last_directive);
            if (d.type === 'macro_directives' && Array.isArray(d.directives)) {
                // Find the brain's directive (first in the batch)
                // Bot directives follow after the brain's directive(s)
                d = d.directives[0] || {};
            }

            let summary = d.directive || 'Unknown';
            if (d.directive === 'Hold') {
                summary = '⏸ Hold (Brake)';
            } else if (d.directive === 'Idle') {
                summary = '💤 Idle';
            } else if (d.directive === 'SplitFaction') {
                summary = `✂️ Split ${Math.round(d.percentage * 100)}% → sub ${d.new_sub_faction}`;
            } else if (d.directive === 'SetZoneModifier') {
                summary = `${d.cost_modifier < 0 ? '🧲 Attract' : '🚫 Repel'} at (${Math.round(d.x)}, ${Math.round(d.y)})`;
            } else if (d.directive === 'UpdateNavigation') {
                const targetLabel = d.target?.faction_id !== undefined
                    ? `Faction ${d.target.faction_id}`
                    : d.target?.type || '?';
                summary = `⚔️ Attack → ${targetLabel}`;
            } else if (d.directive === 'ActivateBuff') {
                summary = '🎯 Debuff Applied!';
            } else if (d.directive === 'Retreat') {
                summary = `🏃 Retreat → (${Math.round(d.retreat_x)}, ${Math.round(d.retreat_y)})`;
            }
            directiveEl.textContent = summary;
        } catch {
            directiveEl.textContent = '—';
        }
    }
}
