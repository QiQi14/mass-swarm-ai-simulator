import * as S from '../../state.js';
import { ADAPTER_CONFIG } from '../../config.js';
import { sendCommand, showToast } from '../../websocket.js';
import { getCanvasEntities } from '../../draw/index.js';
// Faction toggles may need refreshing if we add/delete, but we can call our local or shared update
import { initFactionToggles } from '../shared/legend.js';

export default {
    id: 'spawn',
    title: 'Spawn Tools',
    icon: '➕',
    modes: ['playground'],
    defaultExpanded: false,
    render(body) {
        body.innerHTML = `
            <div style="margin-bottom: var(--space-md);">
                <button class="btn outline" id="spawn-mode-toggle" style="width: 100%;">
                    Enable Spawn Mode
                </button>
                <div id="spawn-hint" style="display: none; font-size: var(--font-size-2xs); color: var(--text-tertiary); text-align: center; margin-top: var(--space-xs);">
                    Click on the canvas to spawn
                </div>
            </div>

            <div class="stat-card" style="padding: var(--space-md); margin-bottom: var(--space-md);">
                <div class="stat-label" style="margin-bottom: var(--space-xs);">Faction</div>
                <div style="display: flex; gap: var(--space-xs);">
                    <select id="spawn-faction-select" class="input" style="flex: 1;"></select>
                    <button class="btn outline" id="spawn-add-faction-btn" title="Add Faction">+</button>
                    <button class="btn error" id="spawn-del-faction-btn" title="Delete Faction">×</button>
                </div>
            </div>

            <div class="stat-card" style="padding: var(--space-md);">
                <div class="stat-label" style="margin-bottom: var(--space-xs);">Amount per click</div>
                <div style="display: flex; gap: var(--space-sm); align-items: center;">
                    <input type="range" id="spawn-amount-slider" class="input" min="1" max="1000" step="1" value="50" style="flex: 1;">
                    <input type="number" id="spawn-amount-input" class="input" value="50" min="1" max="1000" style="width: 60px;">
                </div>
                
                <div class="stat-label" style="margin-top: var(--space-sm); margin-bottom: var(--space-xs);">Spread Radius</div>
                <div style="display: flex; gap: var(--space-sm); align-items: center;">
                    <input type="range" id="spawn-spread-slider" class="input" min="0" max="200" step="1" value="30" style="flex: 1;">
                    <input type="number" id="spawn-spread-input" class="input" value="30" min="0" max="200" style="width: 60px;">
                </div>
            </div>

            <!-- Add Faction Modal (Dynamic) -->
            <div id="spawn-add-faction-modal" style="display: none; position: fixed; inset: 0; z-index: 1000; align-items: center; justify-content: center; background: rgba(0,0,0,0.8);">
                <div class="stat-card" style="padding: var(--space-lg); width: 300px; max-width: 90vw;">
                    <h3 style="margin-bottom: var(--space-md); color: var(--text-primary); font-size: var(--font-size-lg);">Add Faction</h3>
                    <input type="text" id="spawn-faction-name-input" class="input" placeholder="Faction Name" style="width: 100%; margin-bottom: var(--space-md);">
                    <div style="display: flex; gap: var(--space-sm); justify-content: flex-end;">
                         <button class="btn outline" id="spawn-modal-cancel">Cancel</button>
                         <button class="btn primary" id="spawn-modal-confirm">Add</button>
                    </div>
                </div>
            </div>
        `;

        const renderFactionSelect = () => {
            const select = body.querySelector('#spawn-faction-select');
            select.innerHTML = '';
            for (const [id, f] of Object.entries(ADAPTER_CONFIG.factions)) {
                const opt = document.createElement('option');
                opt.value = id;
                opt.textContent = `${f.name} (ID: ${id})`;
                select.appendChild(opt);
            }
        };
        renderFactionSelect();
        // save the initial render function for later use
        this._renderFactionSelect = renderFactionSelect;

        // Sync inputs
        const amountSlider = body.querySelector('#spawn-amount-slider');
        const amountInput = body.querySelector('#spawn-amount-input');
        amountSlider.oninput = (e) => amountInput.value = e.target.value;
        amountInput.oninput = (e) => amountSlider.value = e.target.value;

        const spreadSlider = body.querySelector('#spawn-spread-slider');
        const spreadInput = body.querySelector('#spawn-spread-input');
        spreadSlider.oninput = (e) => spreadInput.value = e.target.value;
        spreadInput.oninput = (e) => spreadSlider.value = e.target.value;

        // Spawn Mode Toggle
        const toggleBtn = body.querySelector('#spawn-mode-toggle');
        const hint = body.querySelector('#spawn-hint');
        toggleBtn.onclick = () => {
             // Nullify other modes directly in state (cleaner state management long term)
             const wasSpawn = S.spawnMode;
             S.setSpawnMode(false); S.setZoneMode(false); S.setSplitMode(false); S.setPaintMode(false);
             
             // The global canvas class updates still need to be handled, or we rely on the main render loop
             // For now we do it directly to mimic init.js behavior
             const canvasEntities = getCanvasEntities();
             canvasEntities.classList.remove('spawn-mode', 'paint-mode');
             
             S.setSpawnMode(!wasSpawn);
             toggleBtn.classList.toggle('active', S.spawnMode);
             toggleBtn.textContent = S.spawnMode ? 'Disable Spawn Mode' : 'Enable Spawn Mode';
             hint.style.display = S.spawnMode ? 'block' : 'none';
             canvasEntities.classList.toggle('spawn-mode', S.spawnMode);
             if (S.spawnMode) showToast('Spawn mode ON', 'info');
        };

        // Add Faction Modal Logic
        const modal = body.querySelector('#spawn-add-faction-modal');
        const nameInput = body.querySelector('#spawn-faction-name-input');
        body.querySelector('#spawn-add-faction-btn').onclick = () => {
            modal.style.display = 'flex';
            nameInput.value = '';
            nameInput.focus();
        };

        body.querySelector('#spawn-modal-cancel').onclick = () => modal.style.display = 'none';

        body.querySelector('#spawn-modal-confirm').onclick = () => {
            const name = nameInput.value.trim();
            modal.style.display = 'none';
            if (!name) return;
            const id = S.bumpNextFactionId();
            const hue = (id * 137) % 360;
            ADAPTER_CONFIG.factions[id] = { name, color: `hsl(${hue}, 70%, 55%)` };
            renderFactionSelect();
            body.querySelector('#spawn-faction-select').value = id;
            initFactionToggles(); // update legend if possible
            showToast(`Added faction: ${name} (ID: ${id})`, 'success');
        };

        body.querySelector('#spawn-del-faction-btn').onclick = () => {
            const fid = parseInt(body.querySelector('#spawn-faction-select').value);
            if (isNaN(fid)) return;
            const fName = ADAPTER_CONFIG.factions[fid]?.name || `Faction ${fid}`;
            if (!confirm(`Delete faction "${fName}"? This will kill all its units.`)) return;
            sendCommand('kill_all', { faction_id: fid });
            delete ADAPTER_CONFIG.factions[fid];
            renderFactionSelect();
            initFactionToggles();
            showToast(`Deleted faction: ${fName}`, 'warn');
        };
    },
    update() {
         // Optionally refresh faction select from config if it changed externally
    }
};
