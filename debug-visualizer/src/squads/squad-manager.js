import * as S from '../state.js';
import { sendCommand } from '../websocket.js';
import { showToast } from '../components/toast.js';
import { getSelectionCentroid } from '../controls/selection.js';
import { getFactionColor } from '../config.js';

/** Auto-increment for squad naming */
let squadNameCounter = 0;
const SQUAD_NAMES = ['Alpha', 'Bravo', 'Charlie', 'Delta', 'Echo', 'Foxtrot',
                     'Golf', 'Hotel', 'India', 'Juliet', 'Kilo', 'Lima'];

function offsetColor(baseColor, offsetIndex) {
  // Provides a reliable color string for the sub-faction 
  // by rotating a hue based on the offset index
  return `hsl(${(offsetIndex * 45) % 360}, 70%, 65%)`;
}

/**
 * Create a squad from the current selection.
 * Uses SplitFaction to carve out a sub-faction from the selected entities.
 *
 * @returns {number|null} The new squad (sub-faction) ID, or null on failure
 */
export function createSquadFromSelection() {
  if (S.selectedEntities.size === 0) return null;

  // Determine the faction of selected entities (must be same faction)
  const factionIds = new Set();
  for (const id of S.selectedEntities) {
    const ent = S.entities.get(id);
    if (ent) factionIds.add(ent.faction_id);
  }
  if (factionIds.size !== 1) {
    showToast('Cannot create squad from multiple factions', 'warn');
    return null;
  }
  const sourceFaction = factionIds.values().next().value;

  // Count total entities in source faction
  let totalInFaction = 0;
  for (const ent of S.entities.values()) {
    if (ent.faction_id === sourceFaction) totalInFaction++;
  }

  // Calculate percentage
  const percentage = S.selectedEntities.size / totalInFaction;

  // Auto-assign sub-faction ID
  const newSubFaction = (sourceFaction + 1) * 100 + squadNameCounter;
  
  // Epicenter = centroid of selected entities
  const centroid = getSelectionCentroid(S.selectedEntities);

  // Send SplitFaction command
  const ok = sendCommand('split_faction', {
    source_faction: sourceFaction,
    new_sub_faction: newSubFaction,
    percentage: Math.min(percentage, 0.99), // cap at 99%
    epicenter_x: centroid.x,
    epicenter_y: centroid.y,
  });

  if (!ok) return null;

  // Register squad
  const name = SQUAD_NAMES[squadNameCounter % SQUAD_NAMES.length];
  squadNameCounter++;

  S.squads.set(newSubFaction, {
    id: newSubFaction,
    parentFactionId: sourceFaction,
    name: name,
    color: offsetColor(getFactionColor(sourceFaction), squadNameCounter),
    currentTarget: null,
    currentOrder: 'idle',
    createdTick: S.currentTick,
  });

  // Switch active selection to the new squad
  S.setActiveSquadId(newSubFaction);
  S.clearSelection();

  showToast(`${name} Squad created (${S.selectedEntities.size} units)`, 'success');
  return newSubFaction;
}

/**
 * Disband a squad by merging it back into its parent faction.
 * @param {number} squadId - Sub-faction ID to merge
 */
export function disbandSquad(squadId) {
  const squad = S.squads.get(squadId);
  if (!squad) return;

  sendCommand('merge_faction', {
    source_faction: squadId,
    target_faction: squad.parentFactionId,
  });

  S.squads.delete(squadId);
  if (S.activeSquadId === squadId) {
    S.setActiveSquadId(null);
  }
  showToast(`${squad.name} Squad disbanded`, 'success');
}

/**
 * Get live stats for a squad (reads from S.entities).
 * @param {number} squadId - Sub-faction ID
 * @returns {{ count: number, avgHp: number, centroid: { x: number, y: number } }}
 */
export function getSquadStats(squadId) {
  let count = 0;
  let totalHp = 0;
  let sumX = 0;
  let sumY = 0;

  for (const ent of S.entities.values()) {
    if (ent.faction_id === squadId) {
      count++;
      sumX += ent.x;
      sumY += ent.y;
      totalHp += ent.stats?.[0] ?? 0;
    }
  }

  return {
    count,
    avgHp: count > 0 ? totalHp / count : 0,
    centroid: count > 0 ? { x: sumX / count, y: sumY / count } : { x: 0, y: 0 }
  };
}

/**
 * Update squad's current order state (for display purposes).
 * @param {number} squadId
 * @param {string} order - 'idle' | 'move' | 'attack' | 'hold' | 'retreat'
 * @param {{ x: number, y: number } | null} target
 */
export function setSquadOrder(squadId, order, target = null) {
  const squad = S.squads.get(squadId);
  if (squad) {
    squad.currentOrder = order;
    squad.currentTarget = target;
  }
}

/**
 * Check if any tracked squads have been fully eliminated (0 entities).
 * Auto-removes them from the registry.
 */
export function pruneDeadSquads() {
  for (const [squadId, info] of S.squads) {
    let alive = 0;
    for (const ent of S.entities.values()) {
      if (ent.faction_id === squadId) { alive++; break; }
    }
    if (alive === 0) {
      S.squads.delete(squadId);
      if (S.activeSquadId === squadId) S.setActiveSquadId(null);
    }
  }
}
