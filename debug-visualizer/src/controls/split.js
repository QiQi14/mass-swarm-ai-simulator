import * as S from '../state.js';
import { sendCommand, showToast } from '../websocket.js';
import { deselectEntity, updateInspectorPanel } from '../panels/shared/inspector.js';

export function handleSplitClick(wx, wy) {
    const source_faction = parseInt(document.getElementById('split-source-faction').value);
    if (isNaN(source_faction)) {
        showToast('Select a source faction', 'warn');
        return;
    }
    let new_sub_faction = (source_faction + 1) * 100;
    while (S.activeSubFactions && S.activeSubFactions.includes(new_sub_faction)) new_sub_faction++;

    const ok = sendCommand("split_faction", {
        source_faction,
        new_sub_faction,
        percentage: (parseFloat(document.getElementById('split-pct').value) || 30) / 100.0,
        epicenter_x: wx,
        epicenter_y: wy,
    });
    if (ok) {
        showToast(`Split command sent (epicenter: ${Math.round(wx)}, ${Math.round(wy)})`, 'success');
        document.getElementById('split-mode-btn').click();
    }
}

export function handleSelectClick(wx, wy) {
    let bestDist = Infinity;
    let bestId = null;
    for (const [id, ent] of S.entities) {
        const dx = ent.x - wx, dy = ent.y - wy;
        const dist = dx * dx + dy * dy;
        if (dist < bestDist) {
            bestDist = dist;
            bestId = id;
        }
    }

    if (bestId !== null && bestDist < 100) {
        S.setSelectedEntityId(bestId);
        updateInspectorPanel();
        // Accordion auto-expands via _inspectorAccordionRef in inspector.js
    } else {
        deselectEntity();
    }
}
