import { ADAPTER_CONFIG } from '../config.js';
import { sendCommand, showToast } from '../websocket.js';

export function handleSpawnClick(wx, wy) {
    const faction_id = parseInt(document.getElementById('spawn-faction').value);
    if (isNaN(faction_id)) {
        showToast('Select a faction first', 'warn');
        return;
    }
    const amount = parseInt(document.getElementById('spawn-amount').value) || 50;
    const spread = parseFloat(document.getElementById('spawn-spread').value) || 30;
    const ok = sendCommand("spawn_wave", { faction_id, amount, x: wx, y: wy, spread });
    if (ok) {
        const fName = ADAPTER_CONFIG.factions[faction_id]?.name || `Faction ${faction_id}`;
        showToast(`Spawned ${amount} ${fName} units`, 'success');
    } else {
        showToast('Not connected to server', 'error');
    }
}
