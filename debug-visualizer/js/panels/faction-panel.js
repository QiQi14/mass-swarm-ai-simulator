import { ADAPTER_CONFIG } from '../config.js';
import * as S from '../state.js';
import { sendCommand } from '../websocket.js';
import { getFactionColor } from '../draw/entities.js';

export function updateAggroGrid(aggroMasks, activeFactionsIds) {
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
    const legend = document.getElementById('legend-list');
    if (!legend) return;
    legend.querySelectorAll('.legend-sub').forEach(el => el.remove());

    for (const sf of (activeSubFactions || [])) {
        const item = document.createElement('div');
        item.className = 'legend-item legend-sub';
        item.innerHTML = `
            <span class="color-swatch" style="background: ${getFactionColor(sf)};"></span>
            <span>Sub-Faction ${sf}</span>
        `;
        legend.appendChild(item);
    }

    const sflist = document.getElementById('sub-faction-list');
    if (sflist) {
        sflist.innerHTML = '';
        for (const sf of (activeSubFactions || [])) {
            const fi = document.createElement('div');
            fi.className = 'sub-faction-item';
            const parent = sf < 100 ? sf : Math.floor(sf / 100) - 1;
            fi.innerHTML = `
                <span style="color: ${getFactionColor(sf)}">Sub Faction ${sf}</span>
                <button class="btn secondary merge-btn" onclick="window.__sendCommand('merge_faction', { source_faction: ${sf}, target_faction: ${parent} })">Merge to ${parent}</button>
            `;
            sflist.appendChild(fi);
        }
    }
}

export function initFactionToggles() {
    const container = document.getElementById('faction-toggles');
    const spawnFaction = document.getElementById('spawn-faction');
    const zoneFaction = document.getElementById('zone-faction');
    const splitSourceFaction = document.getElementById('split-source-faction');
    const fogTogglesContainer = document.getElementById('fog-toggles-container');

    container.innerHTML = '';
    spawnFaction.innerHTML = '';
    fogTogglesContainer.innerHTML = '';

    const defaultStatic = new Set([1]);

    for (const [factionIdStr, config] of Object.entries(ADAPTER_CONFIG.factions)) {
        const factionId = parseInt(factionIdStr);
        let isStatic = defaultStatic.has(factionId);

        // Spawn dropdown
        const opt = document.createElement('option');
        opt.value = factionId;
        opt.textContent = config.name;
        spawnFaction.appendChild(opt);

        const zOpt = document.createElement('option');
        zOpt.value = factionId;
        zOpt.textContent = config.name;
        zoneFaction.appendChild(zOpt);

        const sOpt = document.createElement('option');
        sOpt.value = factionId;
        sOpt.textContent = config.name;
        splitSourceFaction.appendChild(sOpt);

        // Faction behavior toggle
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

        // Fog toggles
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
