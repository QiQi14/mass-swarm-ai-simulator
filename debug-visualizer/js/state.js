// ─── Shared Mutable State ───────────────────────────────────────────
// All modules import from this single source of truth.

import { GRID_W, GRID_H } from './config.js';

export const entities = new Map();  // Map<id, { x, y, dx, dy, faction_id, stats }>
export const flowFieldCache = new Map(); // Map<factionId, { gridW, gridH, cellSize, vectors }>
export const deathAnimations = [];

export let selectedEntityId = null;
export function setSelectedEntityId(id) { selectedEntityId = id; }

export let paintMode = false;
export function setPaintMode(v) { paintMode = v; }

export let spawnMode = false;
export function setSpawnMode(v) { spawnMode = v; }

export let zoneMode = false;
export function setZoneMode(v) { zoneMode = v; }

export let splitMode = false;
export function setSplitMode(v) { splitMode = v; }

export let activeBrush = 'wall';
export function setActiveBrush(v) { activeBrush = v; }

export let activeZoneType = 'attract';
export function setActiveZoneType(v) { activeZoneType = v; }

export let nextFactionId = 2; // 0 and 1 already exist
export function bumpNextFactionId() { return nextFactionId++; }

export const terrainLocal = new Uint16Array(GRID_W * GRID_H * 2);
for (let i = 0; i < terrainLocal.length; i++) terrainLocal[i] = 100;

export let fogVisible = null;
export function setFogVisible(v) { fogVisible = v; }

export let fogExplored = null;
export function setFogExplored(v) { fogExplored = v; }

export let activeFogFaction = null;
export function setActiveFogFaction(v) { activeFogFaction = v; }

export let currentTick = 0;
export function setCurrentTick(v) { currentTick = v; }

export let ws = null;
export function setWs(v) { ws = v; }

export let isPaused = false;
export function setIsPaused(v) { isPaused = v; }

// View transform (pan/zoom)
export let viewX = 500;
export function setViewX(v) { viewX = v; }

export let viewY = 500;
export function setViewY(v) { viewY = v; }

export let viewScale = 1.0;
export function setViewScale(v) { viewScale = v; }

// Layer visibility — initialized from DOM in main.js
export let showGrid = true;
export function setShowGrid(v) { showGrid = v; }

export let showSpatialGrid = false;
export function setShowSpatialGrid(v) { showSpatialGrid = v; }

export let showFlowField = false;
export function setShowFlowField(v) { showFlowField = v; }

export let showVelocity = false;
export function setShowVelocity(v) { showVelocity = v; }

export let showDensityHeatmap = false;
export function setShowDensityHeatmap(v) { showDensityHeatmap = v; }

export let showZoneModifiers = true;
export function setShowZoneModifiers(v) { showZoneModifiers = v; }

export let showOverrideMarkers = false;
export function setShowOverrideMarkers(v) { showOverrideMarkers = v; }

export let showFog = false;
export function setShowFog(v) { showFog = v; }

// Phase 3 state
export let zoneModifiers = null;
export function setZoneModifiers(v) { zoneModifiers = v; }

export let activeSubFactions = [];
export function setActiveSubFactions(v) { activeSubFactions = v; }

export let aggroMasks = [];
export function setAggroMasks(v) { aggroMasks = v; }

export let densityHeatmap = null;
export function setDensityHeatmap(v) { densityHeatmap = v; }

export let mlBrainStatus = null;
export function setMlBrainStatus(v) { mlBrainStatus = v; }

// Telemetry
export let tpsCounter = 0;
export function setTpsCounter(v) { tpsCounter = v; }
export function addTpsCounter(v) { tpsCounter += v; }

export let currentTps = 0;
export function setCurrentTps(v) { currentTps = v; }

export let currentFps = 0;
export function setCurrentFps(v) { currentFps = v; }

// Mouse tracking
export let mouseWorldX = null;
export function setMouseWorldX(v) { mouseWorldX = v; }

export let mouseWorldY = null;
export function setMouseWorldY(v) { mouseWorldY = v; }

// Drag state
export let isDragging = false;
export function setIsDragging(v) { isDragging = v; }

export let hasDragged = false;
export function setHasDragged(v) { hasDragged = v; }

export let isPainting = false;
export function setIsPainting(v) { isPainting = v; }

export let paintCellsBatch = [];
export function resetPaintCellsBatch() { paintCellsBatch = []; }
export function pushPaintCell(cell) { paintCellsBatch.push(cell); }

// Arena bounds overlay — shows the active coordinate mask area
export let showArenaBounds = true;
export function setShowArenaBounds(v) { showArenaBounds = v; }

// Active arena dimensions in world units (updated per curriculum stage)
export let arenaBounds = { x: 0, y: 0, width: 400, height: 400 };
export function setArenaBounds(bounds) { arenaBounds = { ...arenaBounds, ...bounds }; }

