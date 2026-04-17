import * as S from '../state.js';

/**
 * Perform box-select: find all entities within a world-space bounding box.
 * @param {number} x1 - Start X (world coords)
 * @param {number} y1 - Start Y (world coords)
 * @param {number} x2 - End X (world coords)
 * @param {number} y2 - End Y (world coords)
 * @returns {Set<number>} Set of entity IDs within the box
 */
export function boxSelect(x1, y1, x2, y2) {
  const minX = Math.min(x1, x2), maxX = Math.max(x1, x2);
  const minY = Math.min(y1, y2), maxY = Math.max(y1, y2);
  const result = new Set();
  for (const [id, ent] of S.entities) {
    if (ent.x >= minX && ent.x <= maxX && ent.y >= minY && ent.y <= maxY) {
      result.add(id);
    }
  }
  return result;
}

/**
 * Perform faction-click: select all entities of a faction near click point.
 * Uses a radius-based proximity test.
 * @param {number} wx - Click X (world coords)
 * @param {number} wy - Click Y (world coords)
 * @param {number} radius - Selection radius (default: 100 world units)
 * @returns {{ factionId: number, entities: Set<number> } | null}
 */
export function factionClickSelect(wx, wy, radius = 100) {
  let nearestId = null, nearestDist = Infinity;
  for (const [id, ent] of S.entities) {
    const d = (ent.x - wx) ** 2 + (ent.y - wy) ** 2;
    if (d < nearestDist) { nearestDist = d; nearestId = id; }
  }
  if (!nearestId || nearestDist > radius ** 2) return null;

  const factionId = S.entities.get(nearestId).faction_id;
  const entities = new Set();
  const r2 = radius ** 2;
  for (const [id, ent] of S.entities) {
    if (ent.faction_id === factionId) {
      const d = (ent.x - wx) ** 2 + (ent.y - wy) ** 2;
      if (d < r2) entities.add(id);
    }
  }
  return { factionId, entities };
}

/**
 * Get the centroid (average position) of selected entities.
 * @param {Set<number>} entityIds
 * @returns {{ x: number, y: number }}
 */
export function getSelectionCentroid(entityIds) {
  let sumX = 0, sumY = 0;
  let count = 0;
  for (const id of entityIds) {
    const ent = S.entities.get(id);
    if (ent) {
      sumX += ent.x;
      sumY += ent.y;
      count++;
    }
  }
  if (count === 0) return { x: 0, y: 0 };
  return { x: sumX / count, y: sumY / count };
}

/**
 * Get aggregate stats for selected entities.
 * @param {Set<number>} entityIds
 * @returns {{ count: number, factionId: number | null, avgHp: number, totalHp: number }}
 */
export function getSelectionStats(entityIds) {
  let count = 0;
  let totalHp = 0;
  let factionId = null;

  for (const id of entityIds) {
    const ent = S.entities.get(id);
    if (ent) {
      count++;
      totalHp += ent.stats ? ent.stats[0] : 0;
      if (factionId === null) {
        factionId = ent.faction_id;
      }
    }
  }

  const avgHp = count > 0 ? totalHp / count : 0;
  return { count, factionId, avgHp, totalHp };
}
