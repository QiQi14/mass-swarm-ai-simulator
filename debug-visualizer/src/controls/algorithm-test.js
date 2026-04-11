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
            { faction_id: 0, count: 500, x: 400, y: 500, spread: 150, stats: [{ index: 0, value: 100.0 }] },
            { faction_id: 1, count: 100, x: 600, y: 500, spread: 100, stats: [{ index: 0, value: 100.0 }] },
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
            { faction_id: 0, count: 300, x: 400, y: 400, spread: 100, stats: [{ index: 0, value: 100.0 }] },
            { faction_id: 1, count: 300, x: 600, y: 400, spread: 100, stats: [{ index: 0, value: 100.0 }] },
            { faction_id: 2, count: 300, x: 500, y: 600, spread: 100, stats: [{ index: 0, value: 100.0 }] },
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
