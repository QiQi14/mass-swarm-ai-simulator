/* debug-visualizer/src/panels/playground/squad-panel.js */
import * as S from '../../state.js';
import { getSquadStats, disbandSquad } from '../../squads/squad-manager.js';
import { orderMove, orderAttack, orderHold, orderRetreat } from '../../squads/order-system.js';
import { showToast } from '../../components/toast.js';

export function mountSquadPanel(container) {
  const panel = document.createElement('div');
  panel.className = 'overlay-card overlay-card--squad';
  panel.id = 'squad-panel';
  panel.style.display = 'none';

  panel.innerHTML = `
    <div class="overlay-card__header">
      <span class="overlay-card__header-dot" id="squad-dot" style="display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;"></span>
      <span id="squad-name" style="font-weight:600;">SQUAD</span>
      <span class="overlay-card__header-count" id="squad-count" style="margin-left:auto;color:var(--text-secondary);font-size:11px;">0 units</span>
    </div>
    <div class="overlay-card__body">
      <!-- HP Bar -->
      <div class="squad-hp-bar">
        <div class="squad-hp-bar__fill" id="squad-hp-fill" style="width: 100%"></div>
        <span class="squad-hp-bar__label" id="squad-hp-label" style="position: absolute; right: 4px; top: -14px; font-size: 9px; color: var(--text-secondary);">100 HP avg</span>
      </div>

      <!-- Current Order -->
      <div class="squad-order" style="display: flex; gap: 6px; margin: 8px 0; align-items: center; font-size: 11px;">
        <span class="squad-order__icon" id="squad-order-icon">•</span>
        <span class="squad-order__text" id="squad-order-text">Idle</span>
      </div>

      <!-- Action Buttons -->
      <div class="squad-actions">
        <button class="squad-btn" data-cmd="move" title="Move (Right-click)">
          → Move
        </button>
        <button class="squad-btn squad-btn--attack" data-cmd="attack" title="Attack">
          ⚔ Attack
        </button>
        <button class="squad-btn" data-cmd="hold" title="Hold (H)">
          ■ Hold
        </button>
        <button class="squad-btn" data-cmd="retreat" title="Retreat (R)">
          ← Retreat
        </button>
      </div>

      <!-- Footer -->
      <div class="squad-footer" style="margin-top: 8px;">
        <button class="squad-btn squad-btn--danger" data-cmd="disband">
          Disband Squad
        </button>
      </div>
    </div>
  `;

  container.appendChild(panel);

  // Setup event listeners
  const actionContainer = panel.querySelector('.squad-actions');
  actionContainer.addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    const cmd = btn.dataset.cmd;
    if (!S.activeSquadId) return;

    if (cmd === 'hold') {
      orderHold(S.activeSquadId);
    } else if (cmd === 'move') {
      showToast('Move Mode: Right-click on map to move', 'info');
    } else if (cmd === 'attack') {
      showToast('Attack Mode: Right-click on enemy to attack', 'info');
    } else if (cmd === 'retreat') {
      showToast('Retreat Mode: Press R and click to retreat', 'info');
    }
  });

  const footerContainer = panel.querySelector('.squad-footer');
  footerContainer.addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (!btn || btn.dataset.cmd !== 'disband') return;
    if (S.activeSquadId) {
      disbandSquad(S.activeSquadId);
    }
  });
}

function getOrderDescription(order, target) {
  switch (order) {
    case 'idle': return { icon: '•', text: 'Idle' };
    case 'move': return { icon: '→', text: target ? `Moving to (${Math.round(target.x)}, ${Math.round(target.y)})` : 'Moving' };
    case 'attack': return { icon: '⚔', text: 'Attacking' };
    case 'hold': return { icon: '■', text: 'Holding Position' };
    case 'retreat': return { icon: '←', text: 'Retreating' };
    default: return { icon: '•', text: 'Unknown' };
  }
}

export function updateSquadPanel() {
  const panel = document.getElementById('squad-panel');
  if (!panel) return;

  if (!S.activeSquadId) {
    if (panel.style.display !== 'none') panel.style.display = 'none';
    return;
  }

  const stats = getSquadStats(S.activeSquadId);
  const info = S.squads.get(S.activeSquadId);

  if (!info || !stats || stats.count === 0) {
    if (panel.style.display !== 'none') panel.style.display = 'none';
    return;
  }

  if (panel.style.display === 'none') {
    panel.style.display = 'block';
  }

  const nameEl = panel.querySelector('#squad-name');
  if (nameEl) nameEl.textContent = `${info.name} SQUAD`;

  const dotEl = panel.querySelector('#squad-dot');
  if (dotEl) dotEl.style.background = info.color || '#fff';

  const countEl = panel.querySelector('#squad-count');
  if (countEl) countEl.textContent = `${stats.count} units`;

  const hpFill = panel.querySelector('#squad-hp-fill');
  if (hpFill) {
    const pct = Math.min(100, Math.max(0, stats.avgHp));
    hpFill.style.width = `${pct}%`;
  }
  
  const hpLabel = panel.querySelector('#squad-hp-label');
  if (hpLabel) hpLabel.textContent = `${Math.round(stats.avgHp)} HP avg`;

  const orderData = getOrderDescription(info.currentOrder, info.currentTarget);
  const orderIcon = panel.querySelector('#squad-order-icon');
  if (orderIcon) {
    orderIcon.textContent = orderData.icon;
    orderIcon.style.color = info.currentOrder === 'attack' ? 'var(--accent-danger)' : 'var(--accent-primary)';
  }

  const orderText = panel.querySelector('#squad-order-text');
  if (orderText) orderText.textContent = orderData.text;
}
