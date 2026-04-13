// ─── Tab Bar Component ───────────────────────────────────────
import { MODES, getCurrentMode, setMode } from '../router.js';

const TAB_CONFIG = [
  { mode: MODES.TRAINING, label: '📊 Training', icon: '📊' },
  { mode: MODES.PLAYGROUND, label: '🎮 Playground', icon: '🎮' },
];

export function renderTabs(container) {
  container.innerHTML = '';
  TAB_CONFIG.forEach(tab => {
    const btn = document.createElement('button');
    btn.className = 'tab-btn';
    btn.dataset.mode = tab.mode;
    btn.textContent = tab.label;
    btn.id = `tab-${tab.mode}`;
    if (getCurrentMode() === tab.mode) btn.classList.add('active');
    btn.onclick = () => setMode(tab.mode);
    container.appendChild(btn);
  });
  // Animated underline indicator
  const indicator = document.createElement('div');
  indicator.className = 'tab-indicator';
  indicator.id = 'tab-indicator';
  container.appendChild(indicator);
  updateIndicator();
}

export function updateTabs() {
  const mode = getCurrentMode();
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.mode === mode);
  });
  updateIndicator();
}

function updateIndicator() {
  const active = document.querySelector('.tab-btn.active');
  const indicator = document.getElementById('tab-indicator');
  if (active && indicator) {
    indicator.style.left = `${active.offsetLeft}px`;
    indicator.style.width = `${active.offsetWidth}px`;
  }
}
