# Task B2: Debug Visualizer — Algorithm Test Panel

**Task_ID:** task_b2_debug_test_panel
**Execution_Phase:** 1
**Model_Tier:** standard

## Target_Files
- `debug-visualizer/js/controls/algorithm-test.js` [NEW]
- `debug-visualizer/index.html`

## Dependencies
- None (panel sends WS commands — B1 adds the Rust handlers, but the JS panel can be built first)

## Context_Bindings
- context/architecture
- context/conventions
- context/ipc-protocol

## Strict_Instructions

### Overview

Create an "Algorithm Test" panel in the debug visualizer with two sections:
1. **Preset Loader** — Dropdown + "Load" button to load complete game scenarios
2. **Manual Controls** — Individual forms for navigation/interaction/removal rules

The panel sends WS commands to the Rust micro-core. The commands are:
- `set_navigation` — sets NavigationRuleSet
- `set_interaction` — sets InteractionRuleSet
- `set_removal` — sets RemovalRuleSet
- `spawn_wave` — existing command, spawns entities

### Step 1: Create `algorithm-test.js`

Create `debug-visualizer/js/controls/algorithm-test.js` with these exports:

```javascript
import { sendCommand } from '../websocket.js';

// ── Presets ─────────────────────────────────────────────────────────

/**
 * Load a complete game preset (rules + spawns, NO terrain).
 * Terrain stays in the Terrain Paint panel for independent control.
 */
const PRESETS = {
    'swarm_vs_defender': {
        label: 'Swarm vs Defender',
        description: '2 factions, bidirectional chase, proximity damage, removal at stat[0] ≤ 0',
        navigation: [
            { follower_faction: 0, target: { type: 'Faction', faction_id: 1 } },
            { follower_faction: 1, target: { type: 'Faction', faction_id: 0 } },
        ],
        interaction: [
            { source_faction: 0, target_faction: 1, range: 15.0, effects: [{ stat_index: 0, delta_per_second: -10.0 }] },
            { source_faction: 1, target_faction: 0, range: 15.0, effects: [{ stat_index: 0, delta_per_second: -20.0 }] },
        ],
        removal: [
            { stat_index: 0, threshold: 0.0, condition: 'LessThanEqual' },
        ],
        spawns: [
            { faction_id: 0, count: 500, x: 200, y: 500, spread: 150, stats: [{ index: 0, value: 100.0 }] },
            { faction_id: 1, count: 100, x: 800, y: 500, spread: 100, stats: [{ index: 0, value: 100.0 }] },
        ],
    },
    'three_faction_melee': {
        label: '3-Faction Melee',
        description: '3 factions in a free-for-all triangle',
        navigation: [
            { follower_faction: 0, target: { type: 'Faction', faction_id: 1 } },
            { follower_faction: 1, target: { type: 'Faction', faction_id: 2 } },
            { follower_faction: 2, target: { type: 'Faction', faction_id: 0 } },
        ],
        interaction: [
            { source_faction: 0, target_faction: 1, range: 15.0, effects: [{ stat_index: 0, delta_per_second: -15.0 }] },
            { source_faction: 1, target_faction: 2, range: 15.0, effects: [{ stat_index: 0, delta_per_second: -15.0 }] },
            { source_faction: 2, target_faction: 0, range: 15.0, effects: [{ stat_index: 0, delta_per_second: -15.0 }] },
        ],
        removal: [
            { stat_index: 0, threshold: 0.0, condition: 'LessThanEqual' },
        ],
        spawns: [
            { faction_id: 0, count: 300, x: 200, y: 200, spread: 100, stats: [{ index: 0, value: 100.0 }] },
            { faction_id: 1, count: 300, x: 800, y: 200, spread: 100, stats: [{ index: 0, value: 100.0 }] },
            { faction_id: 2, count: 300, x: 500, y: 800, spread: 100, stats: [{ index: 0, value: 100.0 }] },
        ],
    },
    'waypoint_navigation': {
        label: 'Waypoint Navigation',
        description: '1 faction navigating to a static waypoint — tests pathfinding only',
        navigation: [
            { follower_faction: 0, target: { type: 'Waypoint', x: 800.0, y: 800.0 } },
        ],
        interaction: [],
        removal: [],
        spawns: [
            { faction_id: 0, count: 500, x: 200, y: 200, spread: 100, stats: [{ index: 0, value: 100.0 }] },
        ],
    },
};

/**
 * Apply a preset: send all rule commands, then spawn entities.
 */
export function applyPreset(presetKey) {
    const preset = PRESETS[presetKey];
    if (!preset) return;

    // 1. Kill all existing entities first
    sendCommand('kill_all', { faction_id: 0 });
    sendCommand('kill_all', { faction_id: 1 });
    sendCommand('kill_all', { faction_id: 2 });

    // 2. Set rules
    sendCommand('set_navigation', { rules: preset.navigation });
    sendCommand('set_interaction', { rules: preset.interaction });
    sendCommand('set_removal', { rules: preset.removal });

    // 3. Spawn entities (with small delay to let rules apply)
    setTimeout(() => {
        for (const spawn of preset.spawns) {
            sendCommand('spawn_wave', spawn);
        }
    }, 100);
}

// ── Manual Controls ─────────────────────────────────────────────────

export function sendNavRule(followerFaction, targetType, targetValue) {
    const target = targetType === 'Faction'
        ? { type: 'Faction', faction_id: parseInt(targetValue) }
        : { type: 'Waypoint', x: parseFloat(targetValue.split(',')[0]), y: parseFloat(targetValue.split(',')[1]) };

    sendCommand('set_navigation', {
        rules: [{ follower_faction: parseInt(followerFaction), target }]
    });
}

export function sendInteractionRule(sourceFaction, targetFaction, range, statIndex, delta) {
    sendCommand('set_interaction', {
        rules: [{
            source_faction: parseInt(sourceFaction),
            target_faction: parseInt(targetFaction),
            range: parseFloat(range),
            effects: [{ stat_index: parseInt(statIndex), delta_per_second: parseFloat(delta) }]
        }]
    });
}

export function sendRemovalRule(statIndex, threshold, condition) {
    sendCommand('set_removal', {
        rules: [{
            stat_index: parseInt(statIndex),
            threshold: parseFloat(threshold),
            condition: condition
        }]
    });
}

export function getPresetKeys() {
    return Object.keys(PRESETS);
}

export function getPreset(key) {
    return PRESETS[key];
}
```

### Step 2: Add HTML panel in `index.html`

Add a new collapsible panel section in `index.html` BEFORE the terrain paint panel. Add it after the existing control panels. The panel should include:

1. **Preset section:**
   - A `<select id="preset-select">` dropdown populated with preset keys
   - A "Load Preset" button that calls `applyPreset()`
   - A `<p>` showing the preset description

2. **Manual section (collapsed by default):**
   - Navigation rule form: follower faction (number), target type (dropdown: Faction/Waypoint), target value (text)
   - Interaction rule form: source/target faction (numbers), range (number), stat index (number), delta (number)
   - Removal rule form: stat index (number), threshold (number), condition (dropdown: LessThanEqual/GreaterThanEqual)

Use the existing panel CSS styles from the debug visualizer (`.control-panel`, `.panel-header`, etc).

Each form has an "Apply" button.

### Step 3: Wire up in `main.js`

Import and wire up the preset loader and manual controls:

```javascript
import { applyPreset, getPresetKeys, getPreset, sendNavRule, sendInteractionRule, sendRemovalRule } from './controls/algorithm-test.js';
```

Add initialization code to set up event listeners on the panel elements.

### Step 4: Verify

Open the debug visualizer in a browser and verify:
- Preset dropdown shows all presets
- Selecting a preset shows its description
- "Load Preset" button sends commands (check browser DevTools → Network → WS frames)
- Manual controls accept input and send commands

## Verification_Strategy
  Test_Type: manual_steps
  Acceptance_Criteria:
    - "Algorithm Test panel renders in the debug visualizer"
    - "Preset dropdown lists all presets (Swarm vs Defender, 3-Faction Melee, Waypoint Navigation)"
    - "Selecting a preset shows its description"
    - "Load Preset button sends kill_all, set_navigation, set_interaction, set_removal, spawn_wave commands via WS"
    - "Manual controls accept input and send corresponding WS commands"
    - "Terrain is NOT included in presets — terrain paint panel remains independent"
  Manual_Steps:
    - "Open debug-visualizer/index.html in browser"
    - "Verify Algorithm Test panel exists and is visible"
    - "Select 'Swarm vs Defender' preset → click Load → verify WS frames in DevTools"
    - "Use manual navigation form → verify WS command sent"
