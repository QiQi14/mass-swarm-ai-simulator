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
    wall:     { hard: 65535, soft: 0,   color: '#1a1a2e',  label: 'Wall' },
    mud:      { hard: 200,   soft: 30,  color: '#8b6914',  label: 'Mud' },
    pushable: { hard: 125,   soft: 50,  color: '#d4790e',  label: 'Pushable' },
    clear:    { hard: 100,   soft: 100, color: null,        label: 'Clear' },
};

export const ADAPTER_CONFIG = {
    factions: {
        0: { name: "Swarm",    color: "#ff3b30" },
        1: { name: "Defender", color: "#0a84ff" },
    },
    stats: {
        0: { name: "Health", display: "bar", color_low: "#ff3b30", color_high: "#30d158" },
    },
};

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
