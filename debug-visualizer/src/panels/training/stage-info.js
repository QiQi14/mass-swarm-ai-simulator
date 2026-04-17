import { drawSparkline } from '../../components/sparkline.js';
import { updateFactionStats, GRID_W, GRID_H } from '../../config.js';
import { icon } from '../../components/icons.js';
import * as S from '../../state.js';
import { drawBackground } from '../../draw/index.js';

let curriculum = null;
let stageSnapshot = null;

export async function loadCurriculum() {
  try {
    const resp = await fetch('/logs/run_latest/profile_snapshot.json', { cache: 'no-store' });
    if (resp.ok) {
      curriculum = await resp.json();
    } else {
      // Fallback for dev mode
      const devResp = await fetch('/@fs' + window.location.pathname.replace('/debug-visualizer/training.html', '') + '/macro-brain/profiles/tactical_curriculum.json', { cache: 'no-store' });
      if (devResp.ok) curriculum = await devResp.json();
    }
  } catch (e) {
    console.warn('[stage-info] Could not load curriculum:', e.message);
  }
  // Load stage snapshot with actual per-stage spawn stats
  await loadStageSnapshot();
}

async function loadStageSnapshot() {
  try {
    const resp = await fetch('/logs/run_latest/stage_snapshot.json', { cache: 'no-store' });
    if (resp.ok) {
      stageSnapshot = await resp.json();
      // Push correct HP values to ADAPTER_CONFIG so the inspector uses them
      updateFactionStats(stageSnapshot);

      // Populate terrain from snapshot (fallback when Rust WS doesn't send terrain_sync)
      if (stageSnapshot.terrain) {
        const t = stageSnapshot.terrain;
        const srcW = t.width;
        const srcH = t.height;

        S.setTerrainGridW(srcW);
        S.setTerrainGridH(srcH);
        if (t.cell_size) S.setTerrainCellSize(t.cell_size);

        // Clear and repopulate
        for (let i = 0; i < S.terrainLocal.length; i++) S.terrainLocal[i] = 100;
        const maxY = Math.min(srcH, GRID_H);
        const maxX = Math.min(srcW, GRID_W);
        for (let y = 0; y < maxY; y++) {
          for (let x = 0; x < maxX; x++) {
            const srcIdx = y * srcW + x;
            const dstIdx = (y * GRID_W + x) * 2;
            S.terrainLocal[dstIdx] = t.hard_costs[srcIdx];
            S.terrainLocal[dstIdx + 1] = t.soft_costs ? t.soft_costs[srcIdx] : 100;
          }
        }
        drawBackground();
      }
    }
  } catch (e) {
    console.warn('[stage-info] Could not load stage snapshot:', e.message);
  }
}

import { latestStatus } from './dashboard.js';

function getCurrentStage() {
  return latestStatus.stage ?? 0;
}

function showStageToast(stageIndex) {
  const stageDef = curriculum?.training?.curriculum?.[stageIndex];
  const toast = document.createElement('div');
  toast.className = 'overlay-stage-toast';
  toast.innerHTML = `
    <div style="font-size: 24px; font-weight: 700; font-family: var(--font-mono); letter-spacing: 0.15em;">STAGE ${stageIndex}</div>
    <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">${stageDef?.description || ''}</div>
  `;
  document.body.appendChild(toast);
  toast.addEventListener('animationend', () => toast.remove());
}

function openStageModal(stageIndex) {
  if (!curriculum) return;
  const stageDef = curriculum.training?.curriculum?.[stageIndex];
  if (!stageDef) return;

  const modal = document.createElement('div');
  modal.className = 'stage-modal stage-modal--open';
  modal.id = 'stage-detail-modal';

  // Split description based on convention "Target Selection: read density, pick..."
  const descParts = (stageDef.description || 'Unknown').split(':');
  const stageTitle = descParts[0].trim();
  const stageDesc = descParts.length > 1 ? descParts.slice(1).join(':').trim() : '';

  // Use stageSnapshot for faction cards when available (shows actual per-stage HP/count)
  let factionsHtml = '';
  if (stageSnapshot && stageSnapshot.factions) {
    const trapFid = stageSnapshot.trap_faction;
    const targetFid = stageSnapshot.target_faction;
    const colorMap = { 0: 'red', 1: 'blue', 2: 'green' };
    for (const [fidStr, fdata] of Object.entries(stageSnapshot.factions)) {
      const fid = parseInt(fidStr, 10);
      const colorClass = colorMap[fid] || 'blue';
      let roleLabel = fdata.role || '';
      if (fid === trapFid && fid !== targetFid) roleLabel = 'trap';
      else if (fid === targetFid && fid !== trapFid) roleLabel = 'target';

      const groupLines = fdata.groups.map(g => {
        const classLabel = g.unit_class_id !== undefined ? ` [cls ${g.unit_class_id}]` : '';
        return `${g.count}× HP:${g.hp}${classLabel}`;
      }).join(' · ');

      factionsHtml += `
        <div class="faction-card faction-card--${colorClass}">
           <div class="faction-card__header">${fdata.name || 'Faction ' + fid} <span style="font-size:9px;color:var(--text-tertiary);font-weight:400;text-transform:uppercase;">${roleLabel ? '(' + roleLabel + ')' : ''}</span></div>
           <div class="faction-card__stats">${groupLines}</div>
        </div>
      `;
    }
  } else {
    factionsHtml = curriculum.factions?.map(f => {
      const colorClass = f.id === 0 ? 'red' : (f.id === 1 ? 'blue' : 'green');
      let statsParams = [];
      if (f.stats) {
        for (const [k, v] of Object.entries(f.stats)) { statsParams.push(`${k.toUpperCase()}: ${v}`); }
      }
      return `
        <div class="faction-card faction-card--${colorClass}">
           <div class="faction-card__header">${f.name} <span style="font-size:9px;color:var(--text-tertiary);font-weight:400;">(${f.role})</span></div>
           <div class="faction-card__stats">${statsParams.join(' · ')}</div>
        </div>
      `;
    }).join('') || '';
  }

  const graduation = stageDef.graduation || { win_rate: 0, min_episodes: 0 };


  // Separate combat rules and ability buffs
  const combatOnlyHtml = curriculum.combat?.rules?.map(rule => {
    const source = curriculum.factions?.[rule.source_faction]?.name || `F${rule.source_faction}`;
    const target = curriculum.factions?.[rule.target_faction]?.name || `F${rule.target_faction}`;
    const effects = rule.effects?.map(e => {
      const statName = e.stat_index === 0 ? 'HP' : (e.stat_index === 1 ? 'MS' : (e.stat_index === 2 ? 'DMG' : `S${e.stat_index}`));
      const deltaStr = e.delta_per_second > 0 ? `+${e.delta_per_second}` : `${e.delta_per_second}`;
      return `${statName} ${deltaStr}/s`;
    }).join(', ') || '';
    const mitText = rule.mitigation ? ` (mit: ${rule.mitigation.flat ?? ''}${rule.mitigation.percent ? ' ' + Math.round(rule.mitigation.percent * 100) + '%' : ''})` : '';
    return `<tr><td>${source}</td><td>${target}</td><td>${rule.range}</td><td>${effects}${mitText}</td></tr>`;
  }).join('') || '<tr><td colspan="4" style="color:var(--text-tertiary)">None defined</td></tr>';

  const abilities = curriculum.abilities;
  const buffsHtml = abilities?.skills?.length > 0
    ? abilities.skills.map(sk => {
        const mods = sk.modifiers.map(m => {
          const sn = m.stat_index === 0 ? 'HP' : (m.stat_index === 1 ? 'SPD' : (m.stat_index === 2 ? 'DMG' : `S${m.stat_index}`));
          return `${sn} ×${m.value}`;
        }).join(', ');
        return `<tr><td>${sk.name}</td><td>${sk.duration_ticks}t</td><td>${sk.cooldown_ticks}t</td><td>${mods}</td></tr>`;
      }).join('')
    : '<tr><td colspan="4" style="color:var(--text-tertiary)">No buff skills</td></tr>';

  const actionsHtml = curriculum.actions?.filter(a => a.unlock_stage <= stageIndex)
    .map(a => `<span class="action-chip"><span class="action-chip__icon">${icon('zap', 10)}</span>${a.name.toUpperCase()}</span>`)
    .join('') || '<span style="color:var(--text-tertiary); font-size:11px;">None unlocked</span>';

  modal.innerHTML = `
    <div class="stage-modal__backdrop"></div>
    <div class="stage-modal__dialog">
      <button class="stage-modal__close">&times;</button>

      <div class="stage-modal__title-area">
        <h2>Stage ${stageIndex}: ${stageTitle}</h2>
        ${stageDesc ? `<p class="stage-modal__desc">${stageDesc}</p>` : ''}
      </div>

      <div class="stage-modal__body-grid">

        <!-- LEFT: rules tables -->
        <!-- LEFT: grad + rules + buffs + actions -->
        <div class="stage-modal__left">
          <div class="stage-modal__section">
            <h3 class="stage-modal__section-title">Graduation Criteria</h3>
            <div style="display:flex; flex-wrap:wrap; gap:16px; align-items:center; padding: 4px 0;">
              <div style="display:flex;align-items:center;gap:6px;">
                <span style="color:var(--accent-warning);display:flex;">${icon('trophy', 13)}</span>
                <div>
                  <div style="font-size:9px;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:.06em;">Win Rate</div>
                  <div style="font-family:var(--font-mono);font-size:16px;font-weight:700;color:var(--text-primary);">${Math.round(graduation.win_rate * 100)}%</div>
                </div>
              </div>
              <div style="display:flex;align-items:center;gap:6px;">
                <span style="color:var(--accent-warning);display:flex;">${icon('layers', 13)}</span>
                <div>
                  <div style="font-size:9px;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:.06em;">Min Episodes</div>
                  <div style="font-family:var(--font-mono);font-size:16px;font-weight:700;color:var(--text-primary);">${graduation.min_episodes}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="stage-modal__section">
            <h3 class="stage-modal__section-title">Combat Rules</h3>
            <table class="stage-modal__table">
              <thead><tr><th>SRC</th><th>TGT</th><th>RNG</th><th>EFFECTS</th></tr></thead>
              <tbody>${combatOnlyHtml}</tbody>
            </table>
          </div>

          <div class="stage-modal__section">
            <h3 class="stage-modal__section-title">Buff Skills</h3>
            <table class="stage-modal__table">
              <thead><tr><th>SKILL</th><th>DUR</th><th>CD</th><th>MODIFIERS</th></tr></thead>
              <tbody>${buffsHtml}</tbody>
            </table>
          </div>

          <div class="stage-modal__section">
            <h3 class="stage-modal__section-title">Unlocked Actions</h3>
            <div style="display:flex;flex-wrap:wrap;gap:5px;">${actionsHtml}</div>
          </div>
        </div>

        <!-- RIGHT: factions only — full column for future stat expansion -->
        <div class="stage-modal__right">
          <div class="stage-modal__section">
            <h3 class="stage-modal__section-title">Factions</h3>
            <div class="faction-cards-grid">${factionsHtml}</div>
          </div>
        </div>

      </div>
    </div>
  `;




  document.body.appendChild(modal);

  const closeBtn = modal.querySelector('.stage-modal__close');
  const backdrop = modal.querySelector('.stage-modal__backdrop');

  const closeModal = () => {
    modal.remove();
    document.removeEventListener('keydown', handleKeydown);
  };

  const handleKeydown = (e) => {
    if (e.key === 'Escape') closeModal();
  };

  closeBtn.addEventListener('click', closeModal);
  backdrop.addEventListener('click', closeModal);
  document.addEventListener('keydown', handleKeydown);
}

let lastRenderedStage = -1;

export default {
  id: 'stage-info',
  title: 'Stage Info',
  icon: icon('target'),
  modes: ['training'],
  defaultExpanded: true,
  cardBody: null,

  render(body) {
    this.cardBody = body;
    body.innerHTML = `
      <div id="stage-info-name" style="font-size: var(--font-size-sm); font-weight: 600; color: var(--text-primary); margin-bottom: 3px;"></div>
      <div id="stage-info-goal" style="font-size: var(--font-size-xs); color: var(--text-secondary); margin-bottom: 6px;"></div>
      <div id="stage-info-actions" style="display:flex; flex-wrap:wrap; gap:5px; margin-bottom:8px;"></div>
      <button class="stage-details-btn" id="stage-info-details-btn">
        ${icon('layers', 12)}
        <span>Curriculum Details</span>
        ${icon('chevron-right', 11)}
      </button>
    `;


    body.querySelector('#stage-info-details-btn').addEventListener('click', () => {
      const stage = getCurrentStage();
      openStageModal(stage);
    });

    this._updateCardContent(getCurrentStage());
  },

  _updateCardContent(stage) {
    if (!this.cardBody) return;

    const nameEl = this.cardBody.querySelector('#stage-info-name');
    const goalEl = this.cardBody.querySelector('#stage-info-goal');
    const actionsEl = this.cardBody.querySelector('#stage-info-actions');

    if (!curriculum) {
      nameEl.textContent = 'Curriculum data unavailable';
      goalEl.textContent = '';
      actionsEl.innerHTML = '';
      return;
    }

    const stageDef = curriculum.training?.curriculum?.[stage];
    if (!stageDef) {
      nameEl.textContent = `Stage ${stage}: Unknown`;
      goalEl.textContent = '';
      actionsEl.innerHTML = '';
      return;
    }

    // Split title from desc
    const descParts = (stageDef.description || 'Unknown').split(':');
    nameEl.textContent = `Stage ${stage}: ${descParts[0].trim()}`;

    if (stageDef.graduation) {
      goalEl.textContent = `Goal: ${Math.round(stageDef.graduation.win_rate * 100)}% WR · Min ${stageDef.graduation.min_episodes} episodes`;
    }

    const actionsHtml = curriculum.actions?.filter(a => a.unlock_stage <= stage)
      .map(a => `<span class="action-chip"><span class="action-chip__icon">${icon('zap', 10)}</span>${a.name.toUpperCase()}</span>`)
      .join('') || '';

    actionsEl.innerHTML = actionsHtml;
  },

  update() {
    if (!curriculum) return;
    const stage = getCurrentStage();
    if (stage !== lastRenderedStage) {
      this._updateCardContent(stage);
      if (lastRenderedStage >= 0 && stage > lastRenderedStage) {
        showStageToast(stage);
      }
      lastRenderedStage = stage;
      // Re-fetch stage snapshot when stage changes (graduation happened)
      loadStageSnapshot();
    }
  }
};
