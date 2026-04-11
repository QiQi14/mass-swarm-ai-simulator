// Import order matters — CSS first, then modules
import './styles/reset.css';
import './styles/variables.css';
import './styles/layout.css';
import './styles/panels.css';
import './styles/controls.css';
import './styles/canvas.css';
import './styles/animations.css';
import './styles/training.css';

import { initRouter, onModeChange, getCurrentMode } from './router.js';
import { renderTabs, updateTabs } from './components/tabs.js';
import { initBottomSheet } from './components/bottom-sheet.js';
import { renderAllPanels, onModeSwitch, updatePanels } from './panels/index.js';
// Import panel registrations (side-effect imports)
import './panels/shared/telemetry.js';
import './panels/shared/inspector.js';
import './panels/shared/viewport.js';
import './panels/shared/legend.js';
import './panels/training/dashboard.js';
import './panels/training/ml-brain.js';
import './panels/training/perf.js';
import './panels/playground/game-setup.js';
import './panels/playground/sim-controls.js';
import './panels/playground/spawn.js';
import './panels/playground/terrain.js';
import './panels/playground/zones.js';
import './panels/playground/splitter.js';
import './panels/playground/aggro.js';
import './panels/playground/behavior.js';

import * as S from './state.js';
import { initCanvases, resizeCanvas, drawEntities, drawFog, drawBackground, drawArenaBounds } from './draw/index.js';
import { connectWebSocket } from './websocket.js';
import { initControls } from './controls/init.js';

// ── Initialize ────────────────────────────────────────────
initRouter();

const bgCanvas = document.getElementById('canvas-bg');
const canvasEntities = document.getElementById('canvas-entities');
initCanvases(bgCanvas, canvasEntities);

renderTabs(document.getElementById('tab-bar'));
renderAllPanels(document.getElementById('panel-scroll'));

initBottomSheet();

onModeChange((newMode, oldMode) => {
  updateTabs();
  onModeSwitch(document.getElementById('panel-scroll'), newMode);
});

window.addEventListener('resize', resizeCanvas);
initControls();

// ── Render Loop ───────────────────────────────────────────
function renderFrame() {
  const ctx = canvasEntities.getContext('2d');
  ctx.clearRect(0, 0, canvasEntities.width, canvasEntities.height);
  drawEntities();
  if (S.showFog) drawFog();
  drawArenaBounds(ctx);
  updatePanels(); // NEW: per-frame panel updates
  requestAnimationFrame(renderFrame);
}

resizeCanvas();
connectWebSocket();
requestAnimationFrame(renderFrame);
