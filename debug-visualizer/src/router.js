// ─── Hash-Based Mode Router ─────────────────────────────────

export const MODES = Object.freeze({
  TRAINING: 'training',
  PLAYGROUND: 'playground',
});

const DEFAULT_MODE = MODES.PLAYGROUND;
let currentMode = null;
const listeners = [];

export function getCurrentMode() {
  return currentMode;
}

export function setMode(mode) {
  if (!Object.values(MODES).includes(mode)) return;
  if (mode === currentMode) return;
  const oldMode = currentMode;
  currentMode = mode;
  window.location.hash = mode;
  listeners.forEach(cb => cb(mode, oldMode));
}

export function onModeChange(callback) {
  listeners.push(callback);
}

export function initRouter() {
  const hash = window.location.hash.slice(1);
  currentMode = Object.values(MODES).includes(hash) ? hash : DEFAULT_MODE;
  window.addEventListener('hashchange', () => {
    const newHash = window.location.hash.slice(1);
    if (Object.values(MODES).includes(newHash) && newHash !== currentMode) {
      setMode(newHash);
    }
  });
}
