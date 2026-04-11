import { createAccordion, applyModeFilter } from '../components/accordion.js';
import { getCurrentMode } from '../router.js';

// Import Shared Panels
import telemetryPanel, { startTelemetryLoop } from './shared/telemetry.js';
import inspectorPanel, { updateInspectorPanel, deselectEntity } from './shared/inspector.js';
import viewportPanel from './shared/viewport.js';
import legendPanel, { updateAggroGrid, updateLegend, initFactionToggles } from './shared/legend.js';

// Import Training Panels
import dashboardPanel from './training/dashboard.js';
import mlBrainPanel, { updateMlBrainPanel } from './training/ml-brain.js';
import perfPanel, { updatePerfBars } from './training/perf.js';

// Import Playground Panels
import gameSetupPanel from './playground/game-setup.js';
import simControlsPanel from './playground/sim-controls.js';
import spawnPanel from './playground/spawn.js';
import terrainPanel from './playground/terrain.js';
import zonesPanel from './playground/zones.js';
import splitterPanel from './playground/splitter.js';
import aggroPanel from './playground/aggro.js';
import behaviorPanel from './playground/behavior.js';

// ─── Panel Registry ──────────────────────────────────────────

const panels = [];

/**
 * Register a panel module.
 */
export function registerPanel(panel) {
  panels.push(panel);
}

export function addPanels(newPanels) {
  newPanels.forEach(p => panels.push(p));
}

/** Build all panels into the sidebar scroll container. */
export function renderAllPanels(container) {
  container.innerHTML = '';
  for (const panel of panels) {
    const { element, body, setExpanded } = createAccordion({
      id: panel.id,
      title: panel.title,
      icon: panel.icon || '',
      expanded: panel.defaultExpanded ?? false,
    });
    element.dataset.modes = panel.modes.join(',');
    panel.render(body);
    panel._accordionRef = { element, body, setExpanded };
    container.appendChild(element);
  }
  applyModeFilter(container, getCurrentMode());
}

/** Called when mode changes — show/hide panels. */
export function onModeSwitch(container, newMode) {
  applyModeFilter(container, newMode);
}

/** Bulk update call — delegates to each panel's update(). */
export function updatePanels() {
  const mode = getCurrentMode();
  for (const panel of panels) {
    if (panel.update && panel.modes.includes(mode)) {
      panel.update();
    }
  }
}

// Register all Task 04 panels
// Order matters: typical dashboard top, then others
registerPanel(dashboardPanel);
registerPanel(mlBrainPanel);
registerPanel(telemetryPanel);
registerPanel(perfPanel);
registerPanel(viewportPanel);
registerPanel(inspectorPanel);
registerPanel(legendPanel);

// Add Task 05 Playground Panels (Game Setup must be first)
addPanels([
    gameSetupPanel,
    simControlsPanel,
    spawnPanel,
    terrainPanel,
    zonesPanel,
    splitterPanel,
    aggroPanel,
    behaviorPanel
]);


