import * as S from '../../state.js';
import { ADAPTER_CONFIG } from '../../config.js';
import { showToast } from '../../websocket.js';

export default {
    id: 'zones',
    title: 'Zone Modifiers',
    icon: '◎',
    modes: ['playground'],
    defaultExpanded: false,
    render(body) {
        body.innerHTML = `
            <div style="margin-bottom: var(--space-md);">
                <button class="btn outline" id="zones-mode-toggle" style="width: 100%;">
                    Enable Place Zone
                </button>
                <div id="zones-hint" style="display: none; font-size: var(--font-size-2xs); color: var(--text-tertiary); text-align: center; margin-top: var(--space-xs);">
                    Click on the canvas to place zone
                </div>
            </div>

            <div id="zones-tools" style="display: none; flex-direction: column; gap: var(--space-md);">
                <div class="stat-card" style="padding: var(--space-md);">
                    <div class="stat-label" style="margin-bottom: var(--space-sm);">Modifier Type</div>
                    <div style="display: flex; gap: var(--space-sm); margin-bottom: var(--space-sm);">
                        <button class="btn outline zone-type-btn active" data-type="attract" style="flex: 1;">Attract</button>
                        <button class="btn outline zone-type-btn" data-type="repel" style="flex: 1;">Repel</button>
                    </div>

                    <div class="stat-label" style="margin-bottom: var(--space-xs);">Target Faction</div>
                    <select id="zones-faction-select" class="input" style="width: 100%; margin-bottom: var(--space-sm);"></select>

                    <div class="stat-label" style="margin-bottom: var(--space-xs);">Radius</div>
                    <div style="display: flex; gap: var(--space-sm); align-items: center; margin-bottom: var(--space-sm);">
                        <input type="range" id="zones-radius-slider" class="input" min="10" max="300" step="10" value="80" style="flex: 1;">
                        <input type="number" id="zones-radius-input" class="input" value="80" style="width: 60px;">
                    </div>

                    <div class="stat-label" style="margin-bottom: var(--space-xs);">Intensity</div>
                    <div style="display: flex; gap: var(--space-sm); align-items: center; margin-bottom: var(--space-sm);">
                        <input type="range" id="zones-intensity-slider" class="input" min="10" max="200" step="10" value="50" style="flex: 1;">
                        <input type="number" id="zones-intensity-input" class="input" value="50" style="width: 60px;">
                    </div>

                    <div class="stat-label" style="margin-bottom: var(--space-xs);">Duration (ticks)</div>
                    <div style="display: flex; gap: var(--space-sm); align-items: center;">
                        <input type="number" id="zones-duration-input" class="input" value="300" style="width: 100%;">
                    </div>
                </div>
            </div>
        `;

        const toggleBtn = body.querySelector('#zones-mode-toggle');
        const tools = body.querySelector('#zones-tools');
        const hint = body.querySelector('#zones-hint');
        
        toggleBtn.onclick = () => {
             const wasZone = S.zoneMode;
             S.setSpawnMode(false); S.setZoneMode(false); S.setSplitMode(false); S.setPaintMode(false);
             
             S.setZoneMode(!wasZone);
             toggleBtn.classList.toggle('active', S.zoneMode);
             toggleBtn.textContent = S.zoneMode ? 'Disable Place Zone' : 'Enable Place Zone';
             tools.style.display = S.zoneMode ? 'flex' : 'none';
             hint.style.display = S.zoneMode ? 'block' : 'none';
             if (S.zoneMode) showToast('Zone Place mode ON', 'info');
        };

        const typeBtns = body.querySelectorAll('.zone-type-btn');
        typeBtns.forEach(btn => {
            btn.onclick = () => {
                typeBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                S.setActiveZoneType(btn.dataset.type);
            };
        });

        const syncPair = (sliderId, inputId) => {
            const slider = body.querySelector(`#${sliderId}`);
            const input = body.querySelector(`#${inputId}`);
            slider.oninput = (e) => input.value = e.target.value;
            input.oninput = (e) => slider.value = e.target.value;
        };

        syncPair('zones-radius-slider', 'zones-radius-input');
        syncPair('zones-intensity-slider', 'zones-intensity-input');

        const updateFactionList = () => {
            const select = body.querySelector('#zones-faction-select');
            select.innerHTML = '<option value="-1">All Factions</option>';
            for (const [id, f] of Object.entries(ADAPTER_CONFIG.factions)) {
                const opt = document.createElement('option');
                opt.value = id;
                opt.textContent = `${f.name} (ID: ${id})`;
                select.appendChild(opt);
            }
        };

        updateFactionList();
        // Option to expose it for external calls
        this._updateFactionList = updateFactionList;
    },
    update() {
        // Can optionally update the faction select if dynamic
        if (this._updateFactionList) {
            // this._updateFactionList(); // Expensive to do every frame, best to do on mode enter if needed
        }
    }
};
