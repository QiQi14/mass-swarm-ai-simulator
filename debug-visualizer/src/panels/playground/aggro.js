import * as S from '../../state.js';
import { ADAPTER_CONFIG } from '../../config.js';
import { sendCommand } from '../../websocket.js';

export default {
    id: 'aggro',
    title: 'Aggro Masks',
    icon: '⚔️',
    modes: ['playground'],
    defaultExpanded: false,
    render(body) {
        body.innerHTML = `
            <div class="stat-card" style="padding: var(--space-md);">
                <div class="stat-label" style="margin-bottom: var(--space-sm);">Faction Aggro Relationships</div>
                <div id="aggro-grid" style="display: grid; gap: var(--space-xs); font-size: var(--font-size-xs);">
                    <!-- Grid populated dynamically -->
                </div>
            </div>
            <div style="font-size: var(--font-size-2xs); color: var(--text-tertiary); margin-top: var(--space-sm);">
                Checkbox checked: Faction attacks target. Checkbox unchecked: Faction ignores target.
            </div>
        `;

        this.buildGrid = () => {
            const gridContainer = body.querySelector('#aggro-grid');
            gridContainer.innerHTML = '';
            
            const factions = Object.values(ADAPTER_CONFIG.factions).map((f, i) => ({ id: Object.keys(ADAPTER_CONFIG.factions)[i], ...f }));
            if (factions.length === 0) {
                gridContainer.innerHTML = 'No factions available.';
                return;
            }

            gridContainer.style.gridTemplateColumns = `auto ${factions.map(() => '1fr').join(' ')}`;
            
            gridContainer.appendChild(document.createElement('div')); // Empty top-left
            
            factions.forEach(f => {
                const header = document.createElement('div');
                header.style.textAlign = 'center';
                header.style.color = 'var(--text-secondary)';
                header.textContent = `Tgt ${f.id}`;
                gridContainer.appendChild(header);
            });

            factions.forEach(src => {
                const rowLabel = document.createElement('div');
                rowLabel.style.color = 'var(--text-secondary)';
                rowLabel.style.display = 'flex';
                rowLabel.style.alignItems = 'center';
                rowLabel.textContent = `Src ${src.id}`;
                gridContainer.appendChild(rowLabel);

                factions.forEach(tgt => {
                    const cell = document.createElement('div');
                    cell.style.display = 'flex';
                    cell.style.justifyContent = 'center';
                    
                    if (src.id === tgt.id) {
                         cell.innerHTML = `<span style="color: var(--text-tertiary);">-</span>`;
                    } else {
                         const cb = document.createElement('input');
                         cb.type = 'checkbox';
                         
                         // Determine current state from server or default to checked
                         const currentMask = S.aggroMasks.find(m => m.faction_id == src.id);
                         if (currentMask && currentMask.targets) {
                             cb.checked = currentMask.targets.includes(parseInt(tgt.id));
                         } else {
                             cb.checked = true; // default assumed true if nothing registered
                         }
                         
                         cb.onchange = () => {
                             // Build new targets array
                             const currentMaskLocal = S.aggroMasks.find(m => m.faction_id == src.id) || { targets: factions.filter(f=>f.id!=src.id).map(f=>parseInt(f.id)) };
                             let newTargets = [...currentMaskLocal.targets];
                             
                             if (cb.checked && !newTargets.includes(parseInt(tgt.id))) {
                                 newTargets.push(parseInt(tgt.id));
                             } else if (!cb.checked && newTargets.includes(parseInt(tgt.id))) {
                                 newTargets = newTargets.filter(t => t !== parseInt(tgt.id));
                             }
                             
                             sendCommand('set_aggro_mask', {
                                 faction_id: parseInt(src.id),
                                 targets: newTargets
                             });
                         };
                         cell.appendChild(cb);
                    }
                    gridContainer.appendChild(cell);
                });
            });
        };
        
        this.buildGrid();
    },
    update() {
         // Could refresh grid on aggroMask update if needed
    }
};
