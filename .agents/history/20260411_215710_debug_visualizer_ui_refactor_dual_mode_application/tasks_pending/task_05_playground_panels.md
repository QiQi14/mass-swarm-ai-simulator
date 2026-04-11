# Task 05: Playground Mode Panels

## Task_ID
task_05_playground_panels

## Execution_Phase
Phase 3 (Depends on T03)

## Model_Tier
`advanced`

## Target_Files
- `debug-visualizer/src/panels/playground/game-setup.js` — **NEW** (wizard panel)
- `debug-visualizer/src/panels/playground/sim-controls.js` — **NEW**
- `debug-visualizer/src/panels/playground/spawn.js` — **NEW**
- `debug-visualizer/src/panels/playground/terrain.js` — **NEW**
- `debug-visualizer/src/panels/playground/zones.js` — **NEW**
- `debug-visualizer/src/panels/playground/splitter.js` — **NEW**
- `debug-visualizer/src/panels/playground/aggro.js` — **NEW**
- `debug-visualizer/src/panels/playground/behavior.js` — **NEW**

## Dependencies
T03 (app shell, accordion component), T04 (panel registry `addPanels()` must exist)

## Context_Bindings
- `context/conventions` (JS naming, DOM IDs)
- `context/engine-mechanics` (zone modifiers, terrain, aggro masks, interaction rules)
- `context/ipc-protocol` (WS command payloads for spawn, rules, terrain)
- `skills/frontend-ux-ui` (design aesthetic — wizard UX, visual cards, control panels)

## Strict_Instructions
See `implementation_plan_feature_2.md` → Task 05 for exhaustive instructions.

**MOST IMPORTANT: The Game Setup panel.**

**UX Principle: Max 3 Steps.** Users are lazy. Things must be straightforward and easy.

Two paths:
1. **Quick Presets** — Grid of clickable preset cards. One click → entities spawn + rules applied.
2. **Custom Game** — 3-step wizard:
   - Step 1: Choose Factions (visual cards, color swatches, count sliders)
   - Step 2: Set Combat Rules (who fights whom checkboxes, damage/range as Light/Normal/Heavy)
   - Step 3: Launch (map size cards, summary recap, big Start button)
   - Advanced toggle reveals raw rule forms for power users.

Also: Sim Controls, Spawn, Terrain, Zones, Splitter, Aggro, Behavior panels.

Game Setup MUST be the FIRST panel registered (appears at top of sidebar).

---

### ⚠️ CRITICAL: Event Binding Reality (Post-T03 Adjustment)

**`controls/init.js` is DEAD CODE during T04-T05 phase.** The old monolithic `initControls()` (420 lines) references DOM IDs like `#spawn-mode-btn`, `#zone-mode-btn`, etc. that no longer exist in the rewritten `index.html`. It is wrapped in a `try/catch` in `main.js` and will silently fail.

**This means: your panels CANNOT rely on `controls/init.js` for event binding.** All event handlers must be self-contained.

### Self-Contained Panel Pattern

Each panel's `render(bodyElement)` function must:
1. Create its DOM elements inside `bodyElement`
2. Bind all click, change, input events **directly on the elements it creates**
3. Import `sendCommand` from `../../websocket.js` for WS commands
4. Import state setters from `../../state.js` for mode toggles

Example for `sim-controls.js`:
```javascript
import { registerPanel } from '../index.js';  // uses addPanels or registerPanel from T04
import * as S from '../../state.js';
import { sendCommand } from '../../websocket.js';

registerPanel({
  id: 'sim-controls',
  title: 'Simulation',
  icon: '⏯',
  modes: ['playground'],
  defaultExpanded: true,
  render(body) {
    body.innerHTML = `...`;  // Create buttons
    body.querySelector('#play-pause-btn').onclick = () => {
      S.setIsPaused(!S.isPaused);
      sendCommand('toggle_sim');
      // Update button text
    };
  },
});
```

### Preset Logic

The existing `controls/algorithm-test.js` contains:
- `applyPreset(key)` — Applies a preset config (spawns entities + sets rules)
- `getPresetKeys()` — Returns list of preset IDs
- `getPreset(key)` — Returns preset object `{ label, description, ... }`
- `sendNavRule()`, `sendInteractionRule()`, `sendRemovalRule()` — Individual rule senders

**Import these from `../../controls/algorithm-test.js`** for both the Quick Presets path and the Advanced toggle.

### DOM ID Uniqueness
Each panel must use IDs prefixed with its panel name to avoid collisions:
- `game-setup-*` for Game Setup panel elements
- `sim-ctrl-*` for Sim Controls
- `spawn-*` for Spawn panel
- etc.

Do NOT reuse legacy IDs like `spawn-mode-btn` — those will collide with dead references in `controls/init.js`.

## Verification_Strategy
```yaml
Test_Type: manual_steps
Test_Stack: Browser
Acceptance_Criteria:
  - "In Playground Mode: Game Setup is first panel, auto-expanded"
  - "Quick Presets: clicking a preset card spawns entities and applies rules"
  - "Custom Game: 3-step wizard navigates forward/backward correctly"
  - "Custom Game Step 1: can add/remove factions, adjust counts"
  - "Custom Game Step 2: combat grid shows, damage/range selectors work"
  - "Custom Game Step 3: Start Simulation sends correct WS commands"
  - "Advanced toggle reveals manual rule forms"
  - "Training-only panels (Dashboard, ML Brain) NOT visible"
  - "All other playground panels render correctly"
  - "No console errors from event binding (events are self-contained, not relying on controls/init.js)"
Manual_Steps:
  - "Switch to Playground mode → verify Game Setup at top"
  - "Click a Quick Preset card → entities appear on canvas"
  - "Walk through Custom Game wizard: 2 factions, Normal damage, Medium map → Launch"
  - "Expand Advanced toggle → verify manual rule forms appear"
  - "Expand Spawn panel → verify faction selector, sliders render"
  - "Check console — no errors about missing DOM elements"
```

## Live_System_Impact
`safe`
