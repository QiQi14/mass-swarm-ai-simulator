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
            const d = JSON.parse(mlBrain.last_directive);
            let summary = d.directive || 'Hold';
            if (d.directive === 'SplitFaction') {
                summary = `Split ${Math.round(d.percentage * 100)}% to ${d.new_sub_faction}`;
            } else if (d.directive === 'SetZoneModifier') {
                summary = `${d.cost_modifier < 0 ? 'Attract' : 'Repel'} at (${Math.round(d.x)}, ${Math.round(d.y)})`;
            } else if (d.directive === 'UpdateNavigation') {
                summary = `Nav ${d.follower_faction} to ${d.target.type}`;
            }
            directiveEl.textContent = summary;
        } catch {
            directiveEl.textContent = '—';
        }
    }
}
