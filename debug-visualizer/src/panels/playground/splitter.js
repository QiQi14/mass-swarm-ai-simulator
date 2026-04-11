import * as S from '../../state.js';
import { ADAPTER_CONFIG } from '../../config.js';
import { showToast } from '../../websocket.js';
import { getCanvasEntities } from '../../draw/index.js';

export default {
    id: 'splitter',
    title: 'Faction Splitter',
    icon: '➗',
    modes: ['playground'],
    defaultExpanded: false,
    render(body) {
        body.innerHTML = `
            <div style="margin-bottom: var(--space-md);">
                <button class="btn outline" id="split-mode-toggle" style="width: 100%;">
                    Enable Split Mode
                </button>
                <div id="split-hint" style="display: none; font-size: var(--font-size-2xs); color: var(--text-tertiary); text-align: center; margin-top: var(--space-xs);">
                    Click on the canvas to set split epicenter
                </div>
            </div>

            <div id="split-tools" style="display: none; flex-direction: column; gap: var(--space-md);">
                <div class="stat-card" style="padding: var(--space-md);">
                    <div class="stat-label" style="margin-bottom: var(--space-xs);">Source Faction</div>
                    <select id="split-faction" class="input" style="width: 100%; margin-bottom: var(--space-sm);"></select>

                    <div class="stat-label" style="margin-bottom: var(--space-xs);">Split Percentage</div>
                    <div style="display: flex; gap: var(--space-sm); align-items: center;">
                        <input type="range" id="split-pct-slider" class="input" min="10" max="90" step="10" value="50" style="flex: 1;">
                        <input type="number" id="split-pct-input" class="input" value="50" style="width: 60px;">
                    </div>
                </div>
                
                <div class="stat-card" style="padding: var(--space-md);">
                     <div class="stat-label">Active Sub-Factions</div>
                     <div id="split-active-subfactions" style="margin-top: var(--space-sm); font-size: var(--font-size-xs); color: var(--text-secondary);">
                        None
                     </div>
                </div>
            </div>
        `;

        const toggleBtn = body.querySelector('#split-mode-toggle');
        const tools = body.querySelector('#split-tools');
        const hint = body.querySelector('#split-hint');
        
        toggleBtn.onclick = () => {
             const wasSplit = S.splitMode;
             S.setSpawnMode(false); S.setZoneMode(false); S.setSplitMode(false); S.setPaintMode(false);
             
             const canvasEntities = getCanvasEntities();
             canvasEntities.classList.remove('spawn-mode');
             
             S.setSplitMode(!wasSplit);
             toggleBtn.classList.toggle('active', S.splitMode);
             toggleBtn.textContent = S.splitMode ? 'Disable Split Mode' : 'Enable Split Mode';
             tools.style.display = S.splitMode ? 'flex' : 'none';
             hint.style.display = S.splitMode ? 'block' : 'none';
             canvasEntities.classList.toggle('spawn-mode', S.splitMode); // using spawn-mode crosshair for now
             if (S.splitMode) showToast('Split mode ON', 'info');
        };

        const syncPair = (sliderId, inputId) => {
            const slider = body.querySelector(`#${sliderId}`);
            const input = body.querySelector(`#${inputId}`);
            slider.oninput = (e) => input.value = e.target.value;
            input.oninput = (e) => slider.value = e.target.value;
        };

        syncPair('split-pct-slider', 'split-pct-input');

        const updateFactionList = () => {
            const select = body.querySelector('#split-faction');
            select.innerHTML = '';
            for (const [id, f] of Object.entries(ADAPTER_CONFIG.factions)) {
                const opt = document.createElement('option');
                opt.value = id;
                opt.textContent = `${f.name} (ID: ${id})`;
                select.appendChild(opt);
            }
        };

        updateFactionList();
    },
    update() {
        const listDiv = document.getElementById('split-active-subfactions');
        if (listDiv && S.activeSubFactions) {
             if (S.activeSubFactions.length === 0) {
                 listDiv.innerHTML = 'None';
             } else {
                 listDiv.innerHTML = S.activeSubFactions.map(sf => {
                     return `<div style="margin-bottom: 2px;">Faction ${sf.parent} ➜ Sub ${sf.sub} (Radius: ${sf.radius})</div>`;
                 }).join('');
             }
        }
    }
};
