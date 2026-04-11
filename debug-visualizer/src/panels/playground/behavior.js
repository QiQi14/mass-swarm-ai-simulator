import * as S from '../../state.js';
import { ADAPTER_CONFIG } from '../../config.js';
import { sendCommand, showToast } from '../../websocket.js';

export default {
    id: 'behavior',
    title: 'Faction Behavior',
    icon: '🧠',
    modes: ['playground'],
    defaultExpanded: false,
    render(body) {
        body.innerHTML = `
            <div class="stat-card" style="padding: var(--space-md);">
                <div class="stat-label" style="margin-bottom: var(--space-xs);">Select Faction</div>
                <select id="behavior-faction-select" class="input" style="width: 100%; margin-bottom: var(--space-sm);"></select>

                <div class="stat-label" style="margin-bottom: var(--space-sm);">Set Base Behavior</div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-sm);">
                    <button class="btn outline behavior-btn" data-type="idle">Idle</button>
                    <button class="btn outline behavior-btn" data-type="wander">Wander / Seek</button>
                    <button class="btn outline behavior-btn" data-type="chase_closest">Chase Closest</button>
                    <button class="btn outline behavior-btn" data-type="flee">Flee</button>
                </div>
            </div>
        `;

        const renderFactionSelect = () => {
            const select = body.querySelector('#behavior-faction-select');
            select.innerHTML = '';
            for (const [id, f] of Object.entries(ADAPTER_CONFIG.factions)) {
                const opt = document.createElement('option');
                opt.value = id;
                opt.textContent = `${f.name} (ID: ${id})`;
                select.appendChild(opt);
            }
        };

        renderFactionSelect();
        this._renderFactionSelect = renderFactionSelect;

        const btns = body.querySelectorAll('.behavior-btn');
        btns.forEach(btn => {
             btn.onclick = () => {
                  const fid = parseInt(body.querySelector('#behavior-faction-select').value);
                  if (isNaN(fid)) return;
                  
                  const type = btn.dataset.type;
                  // Map these to nav rules for simplicity, as specific WS commands for behavior modes 
                  // aren't fully spec'd. We'll use a placeholder structure or standard nav rules where possible.
                  // For a true engine, we'd send a 'set_behavior' payload.
                  
                  sendCommand('set_behavior', {
                       faction_id: fid,
                       behavior_type: type
                  });
                  
                  showToast(`Assigned ${type} behavior to Faction ${fid}`, 'info');
             };
        });
    },
    update() {
         // refresh if config updates
    }
};
