import * as S from '../state.js';
import { sendCommand, showToast } from '../websocket.js';

export function handleZoneClick(wx, wy) {
    const faction_id = parseInt(document.getElementById('zone-faction').value);
    if (isNaN(faction_id)) {
        showToast('Select a faction first', 'warn');
        return;
    }
    const ok = sendCommand("place_zone_modifier", {
        target_faction: faction_id,
        x: wx,
        y: wy,
        radius: parseFloat(document.getElementById('zone-radius').value) || 100,
        cost_modifier: (S.activeZoneType === 'attract' ? -1 : 1) * (parseFloat(document.getElementById('zone-intensity').value) || 50),
        duration_ticks: parseInt(document.getElementById('zone-duration').value) || 300,
    });
    if (ok) showToast('Placed zone modifier', 'success');
}
