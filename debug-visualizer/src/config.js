// ─── Constants & Configuration ──────────────────────────────────────

export const WS_URL = `ws://${window.location.hostname}:8080`;
export const WORLD_WIDTH = 1000.0;
export const WORLD_HEIGHT = 1000.0;
export const GRID_DIVISIONS = 100;
export const ENTITY_RADIUS = 3;
export const RECONNECT_INTERVAL_MS = 2000;
export const VELOCITY_VECTOR_SCALE = 15;
export const GRID_W = 50;
export const GRID_H = 50;
export const TERRAIN_CELL_SIZE = 20;

export const BRUSH_MAP = {
    wall: { hard: 65535, soft: 0, color: '#ffffff', label: 'Wall' },
    mud: { hard: 200, soft: 30, color: '#8b6914', label: 'Mud' },
    pushable: { hard: 125, soft: 50, color: '#d4790e', label: 'Pushable' },
    clear: { hard: 100, soft: 100, color: null, label: 'Clear' },
};

export const ADAPTER_CONFIG = {
    factions: {
        0: { name: "Brain", color: "#ff3b30", stats: { hp: 100 } },
        1: { name: "EnemyA", color: "#0a84ff", stats: { hp: 100 } },
        2: { name: "EnemyB", color: "#34c759", stats: { hp: 100 } },
    },
};

/**
 * Update faction stats from stage_snapshot.json data.
 * Called when the training stage changes so the inspector HP bars
 * reflect the actual per-stage HP values instead of profile defaults.
 */
export function updateFactionStats(stageSnapshot) {
    if (!stageSnapshot?.factions) return;
    for (const [fidStr, fdata] of Object.entries(stageSnapshot.factions)) {
        const fid = parseInt(fidStr, 10);
        if (!ADAPTER_CONFIG.factions[fid]) {
            ADAPTER_CONFIG.factions[fid] = { name: fdata.name || `Faction ${fid}`, color: getFactionColor(fid), stats: {} };
        }
        ADAPTER_CONFIG.factions[fid].stats.hp = fdata.max_hp || 100;
        if (fdata.name) ADAPTER_CONFIG.factions[fid].name = fdata.name;
    }
}

/**
 * Get a consistent color for any faction ID.
 * Known factions use ADAPTER_CONFIG, dynamic ones get generated hues.
 */
export function getFactionColor(factionId) {
    if (ADAPTER_CONFIG.factions[factionId]) return ADAPTER_CONFIG.factions[factionId].color;
    // Dynamic color for sub-factions / unknown factions
    const hues = [120, 45, 280, 180, 330, 60, 160, 300];
    return `hsl(${hues[factionId % hues.length]}, 70%, 55%)`;
}

/**
 * Get a display name for any faction ID.
 */
export function getFactionName(factionId) {
    return ADAPTER_CONFIG.factions[factionId]?.name || `Faction ${factionId}`;
}

export const COLOR_BG = "#0f1115";
export const COLOR_GRID = "rgba(255, 255, 255, 0.05)";
export const COLOR_GRID_MAJOR = "rgba(255, 255, 255, 0.15)";
export const COLOR_VELOCITY = "rgba(255, 255, 255, 0.5)";
export const COLOR_FOG = "rgba(0, 0, 0, 0.6)";

export const PERF_SYSTEMS = [
    { key: 'spatial_us', label: 'Spatial Grid' },
    { key: 'flow_field_us', label: 'Flow Field' },
    { key: 'interaction_us', label: 'Interaction' },
    { key: 'removal_us', label: 'Removal' },
    { key: 'movement_us', label: 'Movement' },
    { key: 'ws_sync_us', label: 'WS Sync' },
];
