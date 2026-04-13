import { ADAPTER_CONFIG } from '../../config.js';
import * as S from '../../state.js';
import { sendCommand } from '../../websocket.js';
import { getFactionColor } from '../../draw/entities.js';

let ui = null;

export function updateAggroGrid(aggroMasks, activeFactionsIds) {
    // Keep global lookup for cross-panel dependencies
    const container = document.getElementById('aggro-mask-grid');
    if (!container) return;
    container.innerHTML = '';

    for (const mask of aggroMasks) {
        const cell = document.createElement('div');
        cell.className = `aggro-cell ${mask.allow_combat ? 'combat-on' : 'combat-off'}`;
        cell.innerHTML = `
            <span class="aggro-label">${mask.source_faction}→${mask.target_faction}</span>
            <span class="aggro-icon">${mask.allow_combat ? '⚔️' : '🛡️'}</span>
        `;
        cell.onclick = () => sendCommand('set_aggro_mask', {
            source_faction: mask.source_faction,
            target_faction: mask.target_faction,
            allow_combat: !mask.allow_combat,
        });
        container.appendChild(cell);
    }
}

export function updateLegend(activeSubFactions) {
    if (!ui) return;
    ui.legendList.querySelectorAll('.legend-sub').forEach(el => el.remove());

    for (const sf of (activeSubFactions || [])) {
        const item = document.createElement('div');
        item.className = 'legend-item legend-sub';
        item.innerHTML = `
            <span class="color-swatch" style="background: ${getFactionColor(sf)};"></span>
            <span>Sub-Faction ${sf}</span>
        `;
        ui.legendList.appendChild(item);
    }

    if (ui.sfList) {
        ui.sfList.innerHTML = '';
        for (const sf of (activeSubFactions || [])) {
            const fi = document.createElement('div');
            fi.className = 'sub-faction-item';
            const parent = sf < 100 ? sf : Math.floor(sf / 100) - 1;
            fi.innerHTML = `
                <span style="color: ${getFactionColor(sf)}">Sub Faction ${sf}</span>
                <button class="btn secondary merge-btn" onclick="window.__sendCommand('merge_faction', { source_faction: ${sf}, target_faction: ${parent} })">Merge to ${parent}</button>
            `;
            ui.sfList.appendChild(fi);
        }
    }
}

export function initFactionToggles() {
    // Global lookups preserved due to cross-panel playground UI boundaries
    const container = document.getElementById('faction-toggles');
    const spawnFaction = document.getElementById('spawn-faction');
    const zoneFaction = document.getElementById('zone-faction');
    const splitSourceFaction = document.getElementById('split-source-faction');
    const fogTogglesContainer = document.getElementById('fog-toggles-container');

    if (container) container.innerHTML = '';
    if (spawnFaction) spawnFaction.innerHTML = '';
    if (fogTogglesContainer) fogTogglesContainer.innerHTML = '';
    if (splitSourceFaction) splitSourceFaction.innerHTML = ''; 

    const defaultStatic = new Set([1]);

    for (const [factionIdStr, config] of Object.entries(ADAPTER_CONFIG.factions)) {
        const factionId = parseInt(factionIdStr);
        let isStatic = defaultStatic.has(factionId);

        if (spawnFaction) {
            const opt = document.createElement('option');
            opt.value = factionId;
            opt.textContent = config.name;
            spawnFaction.appendChild(opt);
        }

        if (zoneFaction) {
            const zOpt = document.createElement('option');
            zOpt.value = factionId;
            zOpt.textContent = config.name;
            zoneFaction.appendChild(zOpt);
        }

        if (splitSourceFaction) {
            const sOpt = document.createElement('option');
            sOpt.value = factionId;
            sOpt.textContent = config.name;
            splitSourceFaction.appendChild(sOpt);
        }

        if (container) {
            const btn = document.createElement('button');
            btn.className = 'faction-toggle-btn';
            btn.innerHTML = `
                <span>${config.name}</span>
                <span class="faction-mode-badge ${isStatic ? 'static' : 'brain'}">${isStatic ? 'Static' : 'Brain'}</span>
            `;
            btn.style.borderLeftColor = config.color;
            btn.style.borderLeftWidth = '3px';

            btn.addEventListener('click', () => {
                isStatic = !isStatic;
                const badge = btn.querySelector('.faction-mode-badge');
                badge.textContent = isStatic ? 'Static' : 'Brain';
                badge.className = `faction-mode-badge ${isStatic ? 'static' : 'brain'}`;
                sendCommand('set_faction_mode', { faction_id: factionId, mode: isStatic ? 'static' : 'brain' });
            });
            container.appendChild(btn);
        }

        if (fogTogglesContainer) {
            const fogLabel = document.createElement('label');
            fogLabel.className = 'toggle-control';
            fogLabel.innerHTML = `
                <input type="checkbox" id="toggle-fog-${factionId}" name="fog-group" value="${factionId}">
                <span class="control-indicator" style="border-color:${config.color}"></span>
                <span class="control-label">${config.name} Fog</span>
            `;
            const cb = fogLabel.querySelector('input');
            cb.addEventListener('change', (e) => {
                if (e.target.checked) {
                    const allFog = fogTogglesContainer.querySelectorAll('input');
                    for (const other of allFog) {
                        if (other !== e.target) other.checked = false;
                    }
                    S.setShowFog(true);
                    sendCommand("set_fog_faction", { faction_id: factionId });
                } else {
                    let anyChecked = false;
                    const allFog = fogTogglesContainer.querySelectorAll('input');
                    for (const other of allFog) {
                        if (other.checked) anyChecked = true;
                    }
                    if (!anyChecked) {
                        S.setShowFog(false);
                        S.setFogVisible(null);
                        S.setFogExplored(null);
                        sendCommand("set_fog_faction", {});
                    }
                }
            });
            fogTogglesContainer.appendChild(fogLabel);
        }
    }
}

export default {
    id: 'legend',
    title: 'Faction Legend',
    icon: '🏳️',
    modes: ['training', 'playground'],
    defaultExpanded: false,
    render(body) {
        body.innerHTML = `
            <div class="legend-container"></div>
            <div class="sub-faction-container" style="margin-top: 10px; opacity: 0.7; font-size: var(--font-size-xs);"></div>
        `;
        ui = {
            legendList: body.querySelector('.legend-container'),
            sfList: body.querySelector('.sub-faction-container')
        };
        
        for (const [factionIdStr, config] of Object.entries(ADAPTER_CONFIG.factions)) {
            const item = document.createElement('div');
            item.className = 'legend-item';
            item.style.display = 'flex';
            item.style.alignItems = 'center';
            item.style.gap = '8px';
            item.style.marginBottom = '4px';
            item.innerHTML = `
                <span class="color-swatch" style="display:inline-block; width:12px; height:12px; border-radius:2px; background: ${config.color};"></span>
                <span>${config.name}</span>
            `;
            ui.legendList.appendChild(item);
        }
    }
};
