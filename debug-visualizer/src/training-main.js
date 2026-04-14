import './styles/reset.css';
import './styles/variables.css';
import './styles/canvas.css';
import './styles/panels.css';
import './styles/controls.css';
import './styles/training.css';
import './styles/overlay.css';

import * as S from './state.js';
import { connectWebSocket } from './websocket.js';
import { initCanvases, resizeCanvas, drawEntities, drawFog, drawArenaBounds, worldToCanvas } from './draw/index.js';
import { initControls } from './controls/init.js';

// Training panels
import dashboardPanel from './panels/training/dashboard.js';
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
        <span>—</span>
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
    else if (group === 'bottom-row') container = dashboardSlot; // dashboard goes here
    else if (group === 'linked-row') container = linkedRow; // others go here
    else if (group === 'right-top') container = rightTop;
    else if (group === 'right-bottom') container = rightBottom;
    if (!container || !panel) continue;

    const card = document.createElement('div');
    card.className = 'overlay-card';
    card.id = `overlay-card-${id}`;

    const title = panel.title || 'Panel';
    const icon = panel.icon || '📌';

    const header = document.createElement('div');
    header.className = 'overlay-card__header';
    header.innerHTML = `<span>${icon}</span> <span>${title}</span>`;

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

  const groups = [
    {
      id: 'channel-toggles',
      header: 'Force Picture',
      toggles: [
        { id: 'toggle-ch0', label: 'F.Count', checked: false, setter: S.setShowDensityHeatmap },
        { id: 'toggle-ch1', label: 'E.Count', checked: false, setter: S.setShowEnemyDensity },
        { id: 'toggle-ch2', label: 'F.ECP', checked: false, setter: S.setShowFriendlyEcp },
        { id: 'toggle-ch3', label: 'E.ECP', checked: false, setter: S.setShowThreatDensity },
      ]
    },
    {
      id: 'map-toggles',
      header: 'Environment',
      toggles: [
        { id: 'toggle-grid', label: 'Grid', checked: true, setter: S.setShowGrid },
        { id: 'toggle-bounds', label: 'Bounds', checked: true, setter: S.setShowArenaBounds },
        { id: 'toggle-flow', label: 'Flow', checked: false, setter: S.setShowFlowField },
        { id: 'toggle-vel', label: 'Velocity', checked: false, setter: S.setShowVelocity },
        { id: 'toggle-zones', label: 'Zones', checked: true, setter: S.setShowZoneModifiers },
      ]
    }
  ];

  for (const g of groups) {
    const card = document.createElement('div');
    card.className = 'overlay-card layer-toggle-card';
    card.id = `overlay-card-${g.id}`;
    
    let pills = '';
    for (const t of g.toggles) {
      pills += `
        <label class="layer-pill">
          <input type="checkbox" id="${t.id}" ${t.checked ? 'checked' : ''}>
          <div class="layer-pill-surface">${t.label}</div>
        </label>
      `;
    }
    
    card.innerHTML = `
      <div class="overlay-card__header"><span>👁</span> <span>${g.header}</span></div>
      <div class="overlay-card__body layer-toggle-pills">${pills}</div>
    `;
    
    stack.appendChild(card);
    
    for (const t of g.toggles) {
      card.querySelector(`#${t.id}`).addEventListener('change', (e) => t.setter(e.target.checked));
    }
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
    btn.innerHTML = '<span>□</span>';
  }
  
  btn.addEventListener('click', () => {
    const isMinimized = root.classList.contains('overlay--minimized');
    if (isMinimized) {
      root.classList.replace('overlay--minimized', 'overlay--expanded');
      btn.innerHTML = '<span>—</span>';
      localStorage.setItem('overlay-minimized', 'false');
    } else {
      root.classList.replace('overlay--expanded', 'overlay--minimized');
      btn.innerHTML = '<span>□</span>';
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
    statusContainer.className = 'mobile-status-container';
    
    statusContainer.innerHTML = `
      <div class="mobile-status-card overlay-card">
        <div class="overlay-card__header"><span>📊</span> <span>Training Status</span></div>
        <div class="overlay-card__body">
          <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
            <span id="mobile-body-stage" style="font-weight:600;">Stage ?</span>
            <span id="mobile-body-conn">🟢</span>
          </div>
          <div style="display:flex; gap:16px; font-family:var(--font-mono); font-size:var(--font-size-sm); margin-bottom:8px;">
            <span id="mobile-body-ep">Ep: 0</span>
            <span id="mobile-body-wr">WR: 0%</span>
          </div>
          <div id="mobile-body-goal" style="font-family:var(--font-mono); font-size:var(--font-size-xs); color:var(--text-secondary);">Goal: ?%</div>
        </div>
      </div>
    `;

    const layerContainer = document.createElement('div');
    layerContainer.className = 'mobile-layer-container overlay-card';
    layerContainer.innerHTML = `<div class="overlay-card__header"><span>👁</span> <span>Viewport Layers</span></div><div class="overlay-card__body"></div>`;
    
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

  const stageEl = document.getElementById('dash-stage');
  const epEl = document.getElementById('dash-ep');
  const wrEl = document.getElementById('dash-wr');
  const dotEl = document.getElementById('status-dot');

  const stageStr = stageEl ? stageEl.textContent : 'Stage ?';
  const epStr = epEl ? epEl.textContent : '0';
  const wrStr = wrEl ? wrEl.textContent : '0%';
  
  let connStr = '🔴 Offline';
  if (dotEl && dotEl.classList.contains('connected')) {
      connStr = '🟢 Connected';
  }

  strip.innerHTML = `
    <span class="mini-strip__stage">${stageStr}</span>
    <span class="mini-strip__metric">EP ${epStr}</span>
    <span class="mini-strip__metric">${wrStr}</span>
    <span class="mini-strip__conn">${connStr}</span>
  `;
}

function updateMobilePeek() {
  const stageEl = document.getElementById('dash-stage');
  const epEl = document.getElementById('dash-ep');
  const wrEl = document.getElementById('dash-wr');
  const dotEl = document.getElementById('status-dot');
  
  const stageStr = stageEl ? stageEl.textContent : 'Stage ?';
  const epStr = epEl ? epEl.textContent : '0';
  const wrStr = wrEl ? wrEl.textContent : '0%';
  
  const mobileStage = document.getElementById('mobile-stage');
  const mobileEp = document.getElementById('mobile-ep');
  const mobileWr = document.getElementById('mobile-wr');

  if (mobileStage) mobileStage.textContent = stageStr;
  if (mobileEp) mobileEp.textContent = `EP ${epStr}`;
  if (mobileWr) mobileWr.textContent = wrStr;

  // Also update expanded body parts
  const bodyStage = document.getElementById('mobile-body-stage');
  const bodyEp = document.getElementById('mobile-body-ep');
  const bodyWr = document.getElementById('mobile-body-wr');
  const bodyConn = document.getElementById('mobile-body-conn');

  if (bodyStage) bodyStage.textContent = stageStr;
  if (bodyEp) bodyEp.textContent = `Ep: ${epStr}`;
  if (bodyWr) bodyWr.textContent = `WR: ${wrStr}`;
  if (bodyConn) {
    bodyConn.textContent = (dotEl && dotEl.classList.contains('connected')) ? '🟢 Connected' : '🔴 Offline';
  }
}

function updateTopbarStage() {
  const stageEl = document.getElementById('dash-stage');
  const topbarStage = document.getElementById('topbar-stage');
  if (stageEl && topbarStage) {
    topbarStage.textContent = stageEl.textContent;
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

// 5. Connect and render
window.addEventListener('resize', resizeCanvas);
resizeCanvas();
connectWebSocket();
requestAnimationFrame(renderFrame);
