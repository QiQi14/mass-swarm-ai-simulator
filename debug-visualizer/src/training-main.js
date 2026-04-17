// NOTE: This file exceeds 300 lines but is not split because it is a
// bootstrap orchestration file — all items are tightly coupled init
// sequences and DOM wiring that must run in a deterministic order.
import './styles/reset.css';
import './styles/variables.css';
import './styles/canvas.css';
import './styles/panels.css';
import './styles/controls.css';
import './styles/training.css';
import './styles/overlay.css';
import './styles/animations.css';
import { icon } from './components/icons.js';

import * as S from './state.js';
import { connectWebSocket } from './websocket.js';
import { initCanvases, resizeCanvas, drawEntities, drawFog, drawArenaBounds, worldToCanvas } from './draw/index.js';
import { initControls } from './controls/init.js';

// Training panels
import dashboardPanel, { latestStatus } from './panels/training/dashboard.js';
import mlBrainPanel from './panels/training/ml-brain.js';
import perfPanel from './panels/training/perf.js';
import stageInfoPanel, { loadCurriculum } from './panels/training/stage-info.js';

// Shared panels (needed for training mode)
import telemetryPanel from './panels/shared/telemetry.js';
import viewportPanel from './panels/shared/viewport.js';

// Legend must be imported for websocket.js side-effect coupling
import './panels/shared/legend.js';
import inspectorPanel from './panels/shared/inspector.js';

// Legend must be imported for websocket.js side-effect coupling
import './panels/shared/legend.js';

// Panel layout mapping
const PANEL_LAYOUT = {
  'dashboard':   { group: 'bottom-row',   panel: dashboardPanel },
  'ml-brain':    { group: 'linked-row',   panel: mlBrainPanel },
  'stage-info':  { group: 'linked-row',   panel: stageInfoPanel },
  'inspector':   { group: 'right-top',    panel: inspectorPanel },
  'telemetry':   { group: 'right-bottom', panel: telemetryPanel },
  'perf':        { group: 'right-bottom', panel: perfPanel },
};

function buildTopBar() {
  const topBar = document.getElementById('overlay-top-bar');
  if (!topBar) return;
  topBar.innerHTML = `
    <div class="overlay-top-bar__left">
      <div class="status-indicator" id="connection-badge">
        <div class="status-dot" id="status-dot"></div>
        <span id="status-text">Connecting…</span>
      </div>
      <span class="overlay-top-bar__title" style="margin-left: 16px;">S W A R M <span style="color:var(--accent-primary)">C O N T R O L</span></span>
      <span class="stage-badge" id="topbar-stage">Stage ?</span>
    </div>
    <div class="overlay-top-bar__actions">
      <button class="overlay-btn" id="overlay-minimize-btn" title="Minimize dashboard">
        ${icon('minus', 16)}
      </button>
    </div>
  `;
}

function renderOverlayCards() {
  const leftTop = document.getElementById('overlay-left-top');
  const bottomRow = document.getElementById('overlay-bottom-row');
  
  const dashboardSlot = document.createElement('div');
  const linkedRow = document.createElement('div');
  linkedRow.className = 'overlay-linked-row';

  // Vertical stack wrapper for ML Brain + Stage Info cards
  const brainInfoStack = document.createElement('div');
  brainInfoStack.className = 'overlay-brain-info-stack';
  linkedRow.appendChild(brainInfoStack);
  
  if (bottomRow) {
    bottomRow.appendChild(dashboardSlot);
    bottomRow.appendChild(linkedRow);
  }

  const rightTop = document.getElementById('overlay-right-top');
  const rightBottom = document.getElementById('overlay-right-bottom');

  for (const [id, config] of Object.entries(PANEL_LAYOUT)) {
    const { group, panel } = config;
    let container;
    if (group === 'left-top') container = leftTop;
    else if (group === 'bottom-row') container = dashboardSlot;
    else if (group === 'linked-row') container = brainInfoStack; // stacks vertically inside linkedRow
    else if (group === 'right-top') container = rightTop;
    else if (group === 'right-bottom') container = rightBottom;
    if (!container || !panel) continue;

    const card = document.createElement('div');
    card.className = 'overlay-card';
    card.id = `overlay-card-${id}`;

    const title = panel.title || 'Panel';
    const iconHtml = panel.icon || icon('layers');

    const header = document.createElement('div');
    header.className = 'overlay-card__header';
    header.innerHTML = `<span class="overlay-card__header-icon">${iconHtml}</span> <span>${title}</span>`;

    const body = document.createElement('div');
    body.className = 'overlay-card__body';

    if (panel.render) {
      panel.render(body);
    }

    panel._overlayRef = { element: card, body };

    card.appendChild(header);
    card.appendChild(body);
    container.appendChild(card);
  }
}

// Layers bar components in bottom row
function buildLayersBar() {
  const bottomRow = document.getElementById('overlay-bottom-row');
  if (!bottomRow) return;
  
  const linkedRow = bottomRow.querySelector('.overlay-linked-row');
  if (!linkedRow) return;

  const stack = document.createElement('div');
  stack.className = 'layer-toggles-stack';
  linkedRow.appendChild(stack);

  // ── All 8 observation channels organized by semantic block ──
  // Data availability is detected dynamically from live state
  const channelBlocks = [
    {
      block: 'Force',
      icon: '🟦',
      channels: [
        { id: 'toggle-ch0', ch: 0, label: 'Own Density',    desc: 'Friendly head count',    color: 'hsl(120,80%,55%)', setter: S.setShowDensityHeatmap, hasData: () => !!S.densityHeatmap && !!S.densityHeatmap[0] },
        { id: 'toggle-ch1', ch: 1, label: 'Enemy Density',  desc: 'Enemy head count',       color: 'hsl(0,80%,55%)',   setter: S.setShowEnemyDensity,   hasData: () => !!S.densityHeatmap && Object.keys(S.densityHeatmap).some(k => k !== '0') },
        { id: 'toggle-ch2', ch: 2, label: 'Own ECP',        desc: 'Friendly combat power',  color: 'hsl(180,80%,50%)', setter: S.setShowFriendlyEcp,    hasData: () => !!S.ecpDensityMaps && !!S.ecpDensityMaps[0] },
        { id: 'toggle-ch3', ch: 3, label: 'Enemy ECP',      desc: 'Enemy threat density',   color: 'hsl(280,70%,60%)', setter: S.setShowThreatDensity,   hasData: () => !!S.ecpDensityMaps && Object.keys(S.ecpDensityMaps).some(k => k !== '0') },
      ]
    },
    {
      block: 'Environment',
      icon: '🟩',
      channels: [
        { id: 'toggle-ch4', ch: 4, label: 'Terrain Cost',   desc: 'Walls + zone mods',      color: 'hsl(40,80%,55%)',  setter: S.setShowTerrainCost,    hasData: () => S.terrainLocal && S.terrainLocal.some(v => v !== 100) },
        { id: 'toggle-ch5', ch: 5, label: 'Fog Awareness',  desc: '3-level intel state',    color: 'hsl(220,60%,55%)', setter: S.setShowFogAwareness,   hasData: () => !!(S.fogExplored || S.fogVisible) },
      ]
    },
    {
      block: 'Tactical',
      icon: '🟨',
      channels: [
        { id: 'toggle-ch6', ch: 6, label: 'Interact Layer', desc: 'Interactable terrain',    color: 'hsl(50,70%,55%)',  setter: () => {}, hasData: () => false },
        { id: 'toggle-ch7', ch: 7, label: 'Objective Sig.',  desc: 'System objective',       color: 'hsl(35,70%,55%)',  setter: () => {}, hasData: () => false },
      ]
    }
  ];

  // Force Picture card — all 8 channels with collapsible header
  const forceCard = document.createElement('div');
  forceCard.className = 'overlay-card layer-toggle-card';
  forceCard.id = 'overlay-card-channel-toggles';

  let channelsHtml = '';
  for (const blk of channelBlocks) {
    channelsHtml += `<div class="channel-block"><span class="channel-block__label">${blk.icon} ${blk.block}</span>`;
    for (const t of blk.channels) {
      channelsHtml += `
        <label class="channel-row" id="row-${t.id}" title="${t.desc}">
          <input type="checkbox" id="${t.id}">
          <span class="channel-dot" style="background:${t.color};box-shadow:0 0 6px ${t.color}"></span>
          <span class="channel-tag">ch${t.ch}</span>
          <span class="channel-name">${t.label}</span>
        </label>
      `;
    }
    channelsHtml += `</div>`;
  }

  forceCard.innerHTML = `
    <div class="overlay-card__header channel-card__header">
      <span class="overlay-card__header-icon">${icon('radio')}</span>
      <span>Observation Channels</span>
      <button class="channel-collapse-btn" id="channel-collapse-btn" title="Collapse to active only">${icon('chevron-left', 11)}</button>
    </div>
    <div class="channel-active-strip" id="channel-active-strip" style="display:none;"></div>
    <div class="overlay-card__body channel-grid" id="channel-full-grid">${channelsHtml}</div>
  `;
  stack.appendChild(forceCard);

  // Collapse state
  let channelCollapsed = false;
  const collapseBtn = forceCard.querySelector('#channel-collapse-btn');
  const activeStrip = forceCard.querySelector('#channel-active-strip');
  const fullGrid = forceCard.querySelector('#channel-full-grid');

  collapseBtn.addEventListener('click', () => {
    channelCollapsed = !channelCollapsed;
    collapseBtn.innerHTML = channelCollapsed ? icon('chevron-right', 11) : icon('chevron-left', 11);
    collapseBtn.title = channelCollapsed ? 'Expand all channels' : 'Collapse to active only';
    fullGrid.style.display = channelCollapsed ? 'none' : '';
    activeStrip.style.display = channelCollapsed ? 'flex' : 'none';
    refreshActiveStrip();
  });

  function refreshActiveStrip() {
    if (!channelCollapsed) return;
    const active = allChannels.filter(t => {
      const input = document.getElementById(t.id);
      return input?.checked;
    });
    if (active.length === 0) {
      activeStrip.innerHTML = `<span class="channel-strip-none">No active channels</span>`;
    } else {
      const countBadge = `<span class="channel-strip-count">${active.length} active</span>`;
      const dots = active.map(t =>
        `<span class="channel-strip-dot" style="background:${t.color};box-shadow:0 0 5px ${t.color}" title="ch${t.ch}: ${t.label}"></span>`
      ).join('');
      activeStrip.innerHTML = countBadge + dots;
    }
  }

  // Wire event listeners for all channels
  const allChannels = channelBlocks.flatMap(b => b.channels);
  for (const t of allChannels) {
    const input = forceCard.querySelector(`#${t.id}`);
    
    // Restore preserved state from localStorage
    const savedState = localStorage.getItem(`obs-layer-${t.id}`);
    if (savedState === 'true') {
      input.checked = true;
      t.setter(true);
    }
    
    input.addEventListener('change', (e) => {
      const isChecked = e.target.checked;
      localStorage.setItem(`obs-layer-${t.id}`, isChecked);
      t.setter(isChecked);
      refreshActiveStrip();
    });
  }

  // Dynamically update disabled state based on live data availability.
  // BUG NOTE: Do NOT uncheck active toggles here — hasData() briefly returns
  // false at every episode reset boundary before new data arrives. Doing so
  // causes active channels to flicker to inactive on every reset. Instead, only
  // block NEW activations via the --disabled CSS class (pointer-events:none).
  // The change event handler already guards: if (!t.hasData()) e.target.checked=false.
  window._updateChannelAvailability = function() {
    for (const t of allChannels) {
      const row = document.getElementById(`row-${t.id}`);
      if (!row) continue;
      const available = t.hasData();
      if (available) {
        row.classList.remove('channel-row--disabled');
        row.title = t.desc;
      } else {
        row.classList.add('channel-row--disabled');
        row.title = `${t.desc} (no data yet)`;
      }
    }
    refreshActiveStrip(); // always keep strip in sync
  };

  // Environment overlays card — non-channel toggles
  const envToggles = [
    { id: 'toggle-grid', label: 'Grid', checked: true, setter: S.setShowGrid },
    { id: 'toggle-bounds', label: 'Bounds', checked: true, setter: S.setShowArenaBounds },
    { id: 'toggle-flow', label: 'Flow', checked: false, setter: S.setShowFlowField },
    { id: 'toggle-vel', label: 'Velocity', checked: false, setter: S.setShowVelocity },
    { id: 'toggle-zones', label: 'Zones', checked: true, setter: S.setShowZoneModifiers },
  ];

  const envCard = document.createElement('div');
  envCard.className = 'overlay-card layer-toggle-card';
  envCard.id = 'overlay-card-map-toggles';

  let envPills = '';
  for (const t of envToggles) {
    envPills += `
      <label class="layer-pill">
        <input type="checkbox" id="${t.id}" ${t.checked ? 'checked' : ''}>
        <div class="layer-pill-surface">${t.label}</div>
      </label>
    `;
  }

  envCard.innerHTML = `
    <div class="overlay-card__header"><span class="overlay-card__header-icon">${icon('eye')}</span> <span>Overlays</span></div>
    <div class="overlay-card__body layer-toggle-pills">${envPills}</div>
  `;
  stack.appendChild(envCard);

  for (const t of envToggles) {
    const input = envCard.querySelector(`#${t.id}`);
    
    // Restore preserved state from localStorage
    const savedState = localStorage.getItem(`env-layer-${t.id}`);
    if (savedState !== null) {
      const isChecked = savedState === 'true';
      input.checked = isChecked;
      t.setter(isChecked);
    }
    
    input.addEventListener('change', (e) => {
      const isChecked = e.target.checked;
      localStorage.setItem(`env-layer-${t.id}`, isChecked);
      t.setter(isChecked);
    });
  }
}

function initOverlayToggle() {
  const root = document.getElementById('overlay-root');
  const btn = document.getElementById('overlay-minimize-btn');
  if (!root || !btn) return;
  
  // Restore persisted state
  const stored = localStorage.getItem('overlay-minimized');
  if (stored === 'true') {
    root.classList.replace('overlay--expanded', 'overlay--minimized');
    btn.innerHTML = icon('square', 16);
  }

  btn.addEventListener('click', () => {
    const isMinimized = root.classList.contains('overlay--minimized');
    if (isMinimized) {
      root.classList.replace('overlay--minimized', 'overlay--expanded');
      btn.innerHTML = icon('minus', 16);
      localStorage.setItem('overlay-minimized', 'false');
    } else {
      root.classList.replace('overlay--expanded', 'overlay--minimized');
      btn.innerHTML = icon('square', 16);
      localStorage.setItem('overlay-minimized', 'true');
    }
  });
}

function initMobileSheet() {
  const sheet = document.getElementById('training-sheet');
  if (!sheet) return;

  const peek = document.getElementById('training-sheet-peek');
  if (peek) {
    peek.innerHTML = `
      <span class="mini-strip__stage" id="mobile-stage">Stage ?</span>
      <span class="mini-strip__metric" id="mobile-ep">EP 0</span>
      <span class="mini-strip__metric" id="mobile-wr">0%</span>
    `;
  }

  const body = document.getElementById('training-sheet-body');
  if (body) {
    const statusContainer = document.createElement('div');
    statusContainer.className = 'mobile-status-card overlay-card';
    
    const header = document.createElement('div');
    header.className = 'overlay-card__header';
    header.innerHTML = `<span class="overlay-card__header-icon">${icon('chart-line')}</span> <span>Training Dashboard</span>`;
    
    const innerBody = document.createElement('div');
    innerBody.className = 'overlay-card__body';
    
    statusContainer.appendChild(header);
    statusContainer.appendChild(innerBody);
    
    dashboardPanel.render(innerBody);

    const layerContainer = document.createElement('div');
    layerContainer.className = 'mobile-layer-container overlay-card';
    layerContainer.innerHTML = `<div class="overlay-card__header"><span class="overlay-card__header-icon">${icon('eye')}</span> <span>Viewport Layers</span></div><div class="overlay-card__body"></div>`;
    
    viewportPanel.render(layerContainer.querySelector('.overlay-card__body'));

    body.appendChild(statusContainer);
    body.appendChild(layerContainer);
  }

  let touchStartY = 0;
  const handle = sheet.querySelector('.training-sheet__handle');
  if (!handle) return;

  handle.addEventListener('touchstart', (e) => {
    touchStartY = e.changedTouches[0].screenY;
  }, { passive: true });

  handle.addEventListener('touchend', (e) => {
    const delta = e.changedTouches[0].screenY - touchStartY;
    if (delta < -50) sheet.classList.add('training-sheet--expanded');
    else if (delta > 50) sheet.classList.remove('training-sheet--expanded');
  }, { passive: true });

  handle.addEventListener('click', () => {
    sheet.classList.toggle('training-sheet--expanded');
  });
}

function updateMiniStrip() {
  const strip = document.getElementById('overlay-mini-strip');
  if (!strip) return;

  const ep = latestStatus.episode ?? 0;
  const wr = latestStatus.winRatePct ?? 0;
  const streak = latestStatus.gradStreak ?? 0;
  const reward = latestStatus.avgReward;
  const rewardStr = reward !== null ? reward.toFixed(1) : '—';

  strip.innerHTML = `
    <span class="mini-strip__metric">EP ${ep}</span>
    <span class="mini-strip__metric">WR ${wr}%</span>
    <span class="mini-strip__metric">Streak ${streak}</span>
    <span class="mini-strip__metric">Reward ${rewardStr}</span>
  `;
}

function updateMobilePeek() {
  const mobileStage = document.getElementById('mobile-stage');
  const mobileEp = document.getElementById('mobile-ep');
  const mobileWr = document.getElementById('mobile-wr');

  const ep = latestStatus.episode ?? 0;
  const wr = latestStatus.winRatePct ?? 0;
  const reward = latestStatus.avgReward;
  const rewardStr = reward !== null ? reward.toFixed(1) : '—';

  if (mobileStage) mobileStage.textContent = `EP ${ep}`;
  if (mobileEp) mobileEp.textContent = `WR ${wr}%`;
  if (mobileWr) mobileWr.textContent = `R ${rewardStr}`;
}

function updateTopbarStage() {
  const topbarStage = document.getElementById('topbar-stage');
  if (topbarStage) {
    const stage = latestStatus.stage;
    topbarStage.textContent = stage !== null ? `Stage ${stage}` : 'Stage ?';
  }
}

function updateOverlayPanels() {
  // Update each panel that has an update() method
  for (const { panel } of Object.values(PANEL_LAYOUT)) {
    if (panel && panel.update) panel.update();
  }
  
  // Conditionally show inspector and float it near the selected entity
  const inspCard = document.getElementById('overlay-card-inspector');
  if (inspCard) {
    if (S.selectedEntityId === null) {
      inspCard.style.display = 'none';
    } else {
      inspCard.style.display = 'block';
      const ent = S.entities.get(S.selectedEntityId);
      if (ent && worldToCanvas) {
        let [cx, cy] = worldToCanvas(ent.x, ent.y);
        
        // Offset to right. Keep it within screen bounds
        let leftPx = cx + 40;
        let topPx = Math.max(20, cy - 80);
        
        if (leftPx + 280 > window.innerWidth) leftPx = cx - 300; // flip left if cutoff
        if (topPx + 300 > window.innerHeight) topPx = window.innerHeight - 320;
        
        inspCard.style.position = 'fixed';
        inspCard.style.left = leftPx + 'px';
        inspCard.style.top = topPx + 'px';
        inspCard.style.right = 'auto';
        inspCard.style.bottom = 'auto';
        inspCard.style.zIndex = '2000';
      }
    }
  }

  // Update mini-strip
  updateMiniStrip();
  // Update mobile peek bar
  updateMobilePeek();
  // Update topbar stage badge
  updateTopbarStage();
  // Update channel data availability
  if (window._updateChannelAvailability) window._updateChannelAvailability();
}

function renderFrame() {
  const canvasEntities = document.getElementById('canvas-entities');
  if (canvasEntities) {
      const ctx = canvasEntities.getContext('2d');
      ctx.clearRect(0, 0, canvasEntities.width, canvasEntities.height);
      drawEntities();
      if (S.showFog) drawFog();
      drawArenaBounds(ctx);
  }
  updateOverlayPanels();
  requestAnimationFrame(renderFrame);
}

// 1. Canvas init
const bgCanvas = document.getElementById('canvas-bg');
const canvasEntities = document.getElementById('canvas-entities');
if (bgCanvas && canvasEntities) {
    initCanvases(bgCanvas, canvasEntities);
}

// 2. Load curriculum data
loadCurriculum();

// 3. Build overlay UI
buildTopBar();
renderOverlayCards();
buildLayersBar();
initOverlayToggle();
initMobileSheet();

// 4. Canvas controls
initControls();

// 5. Dot grid cursor highlight — tracks mouse position for CSS mask
// Disabled when cursor is inside the arena bounds to avoid overlapping entities
const canvasArea = document.querySelector('.canvas-area');
if (canvasArea) {
  let rafPending = false;
  const OFF = '-300px';
  canvasArea.addEventListener('mousemove', (e) => {
    if (rafPending) return;
    rafPending = true;
    requestAnimationFrame(() => {
      const rect = canvasArea.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;

      // Check if cursor is inside the arena bounding box (screen coords)
      const b = S.arenaBounds;
      if (b && b.width > 0) {
        const [ax1, ay1] = worldToCanvas(b.x, b.y);
        const [ax2, ay2] = worldToCanvas(b.x + b.width, b.y + b.height);
        if (mx >= ax1 && mx <= ax2 && my >= ay1 && my <= ay2) {
          // Inside arena — hide dots so they don't overlap entities/grid
          canvasArea.style.setProperty('--mouse-x', OFF);
          canvasArea.style.setProperty('--mouse-y', OFF);
          rafPending = false;
          return;
        }
      }

      canvasArea.style.setProperty('--mouse-x', `${mx}px`);
      canvasArea.style.setProperty('--mouse-y', `${my}px`);
      rafPending = false;
    });
  });
  canvasArea.addEventListener('mouseleave', () => {
    canvasArea.style.setProperty('--mouse-x', OFF);
    canvasArea.style.setProperty('--mouse-y', OFF);
  });
}


// 6. Connect and render
window.addEventListener('resize', resizeCanvas);
resizeCanvas();
connectWebSocket();
requestAnimationFrame(renderFrame);
