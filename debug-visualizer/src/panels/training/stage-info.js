import { drawSparkline } from '../../components/sparkline.js';
import { updateFactionStats } from '../../config.js';

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
    }
  } catch (e) {
    console.warn('[stage-info] Could not load stage snapshot:', e.message);
  }
}

function getCurrentStageFromDOM() {
  const el = document.getElementById('dash-stage');
  if (!el) return 0;
  const match = el.textContent.match(/\d+/);
  return match ? parseInt(match[0], 10) : 0;
}

function showStageToast(stageIndex) {
  const stageDef = curriculum?.training?.curriculum?.[stageIndex];
  const toast = document.createElement('div');
  toast.className = 'overlay-stage-toast';
  toast.innerHTML = `
    <div style="font-size: 24px; font-weight: 700; font-family: var(--font-mono);">⬆ STAGE ${stageIndex}</div>
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

  const combatRulesHtml = curriculum.combat?.rules?.map(rule => {
    const source = curriculum.factions?.[rule.source_faction]?.name || rule.source_faction;
    const target = curriculum.factions?.[rule.target_faction]?.name || rule.target_faction;
    const effects = rule.effects?.map(e => {
        const statName = e.stat_index === 0 ? 'HP' : (e.stat_index === 1 ? 'MS' : (e.stat_index === 2 ? 'DMG' : `stat[${e.stat_index}]`));
        const deltaStr = e.delta_per_second > 0 ? `+${e.delta_per_second}` : `${e.delta_per_second}`;
        return `${statName} ${deltaStr}/s`;
    }).join(', ') || '';
    return `<tr><td>${source}</td><td>${target}</td><td>${rule.range}</td><td>${effects}</td></tr>`;
  }).join('') || '<tr><td colspan="4">No combat rules defined.</td></tr>';

  // Extract abilities rules into strings
  const abilities = curriculum.abilities;
  let abilitiesHtml = '';
  if (abilities?.skills && abilities.skills.length > 0) {
     abilitiesHtml = abilities.skills.map(sk => {
        const mods = sk.modifiers.map(m => {
          const statName = m.stat_index === 0 ? 'HP' : (m.stat_index === 1 ? 'SPD' : (m.stat_index === 2 ? 'DMG' : `S${m.stat_index}`));
          return `${statName} ${m.modifier_type} x${m.value}`;
        }).join(', ');
        return `<tr><td>${sk.name}</td><td>Buff/Debuff</td><td>Dur: ${sk.duration_ticks}t, CD: ${sk.cooldown_ticks}t</td><td>${mods}</td></tr>`;
     }).join('');
  }

  const actionsHtml = curriculum.actions?.filter(a => a.unlock_stage <= stageIndex)
    .map(a => `<span class="stage-modal__badge">${a.name.toUpperCase()}</span>`)
    .join(' ') || '';

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
        const classLabel = g.unit_class_id !== undefined ? ` [class ${g.unit_class_id}]` : '';
        return `${g.count}× HP:${g.hp}${classLabel}`;
      }).join(' · ');

      factionsHtml += `
        <div class="faction-card faction-card--${colorClass}">
           <div class="faction-card__header">${fdata.name || 'Faction ' + fid} (${roleLabel})</div>
           <div class="faction-card__stats">${groupLines}</div>
        </div>
      `;
    }
  } else {
    // Fallback to base profile factions
    factionsHtml = curriculum.factions?.map(f => {
      const colorClass = f.id === 0 ? 'red' : (f.id === 1 ? 'blue' : 'green');
      let statsParams = [];
      if (f.stats) {
        for (const [k, v] of Object.entries(f.stats)) {
           statsParams.push(`${k.toUpperCase()}: ${v}`);
        }
      }
      return `
        <div class="faction-card faction-card--${colorClass}">
           <div class="faction-card__header">${f.name} (${f.role})</div>
           <div class="faction-card__stats">${statsParams.join(' · ')}</div>
        </div>
      `;
    }).join('') || '';
  }

  const graduation = stageDef.graduation || { win_rate: 0, min_episodes: 0 };

  modal.innerHTML = `
    <div class="stage-modal__backdrop"></div>
    <div class="stage-modal__dialog">
      <button class="stage-modal__close">&times;</button>
      
      <div class="stage-modal__title-area">
        <h2>Stage ${stageIndex}: ${stageTitle}</h2>
        <p class="stage-modal__desc">${stageDesc}</p>
      </div>
      
      <div class="stage-modal__grad-box">
        <h3>Graduation Criteria</h3>
        <div class="grad-metrics">
           <div class="grad-metric"><span style="margin-right:8px;">🏆</span> Win Rate: ${Math.round(graduation.win_rate * 100)}%</div>
           <div class="grad-metric"><span style="margin-right:8px;">🎛</span> Min Episodes: ${graduation.min_episodes}</div>
        </div>
      </div>
      
      <div class="stage-modal__section">
        <h3>Combat Rules</h3>
        <table class="stage-modal__table">
          <thead><tr><th>SOURCE</th><th>TARGET</th><th>RANGE</th><th>EFFECTS</th></tr></thead>
          <tbody>
            ${combatRulesHtml}
            ${abilitiesHtml}
          </tbody>
        </table>
      </div>
      
      <div class="stage-modal__section">
        <h3>Unlocked Actions</h3>
        <div style="display:flex; gap:8px;">${actionsHtml}</div>
      </div>
      
      <div class="stage-modal__section">
        <h3>Factions</h3>
        <div class="faction-cards-grid">
           ${factionsHtml}
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
  icon: '🎯',
  modes: ['training'],
  defaultExpanded: true,
  cardBody: null,

  render(body) {
    this.cardBody = body;
    body.innerHTML = `
      <div id="stage-info-name">Loading...</div>
      <div id="stage-info-goal"></div>
      <div id="stage-info-actions"></div>
      <div style="margin-top: auto; padding-top: 12px; display: flex; justify-content: flex-end;">
        <label class="layer-pill" id="stage-info-details-btn"><span class="layer-pill-surface">Curriculum Details ▸</span></label>
      </div>
    `;
    
    body.querySelector('#stage-info-details-btn').addEventListener('click', () => {
      const stage = getCurrentStageFromDOM();
      openStageModal(stage);
    });

    this._updateCardContent(getCurrentStageFromDOM());
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

    nameEl.textContent = `Stage ${stage}: ${stageDef.description || 'Unknown'}`;
    
    if (stageDef.graduation) {
      goalEl.textContent = `Goal: ${Math.round(stageDef.graduation.win_rate * 100)}% WR · Min ${stageDef.graduation.min_episodes} episodes`;
    }

    const actionsHtml = curriculum.actions?.filter(a => a.unlock_stage <= stage)
      .map(a => `<span class="stage-modal__badge">${a.name}</span>`)
      .join(' ') || '';
    
    actionsEl.innerHTML = `Actions: ${actionsHtml}`;
  },

  update() {
    if (!curriculum) return;
    const stage = getCurrentStageFromDOM();
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
