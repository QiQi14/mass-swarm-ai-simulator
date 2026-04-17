import * as S from '../state.js';
import { sendCommand } from '../websocket.js';
import { setSquadOrder } from './squad-manager.js';

/**
 * Issue a Move order to a squad (or selected entities via their faction).
 * @param {number} targetFaction - Squad sub-faction ID or parent faction ID
 * @param {number} wx - Target X world coordinate
 * @param {number} wy - Target Y world coordinate
 */
export function orderMove(targetFaction, wx, wy) {
  sendCommand('inject_directive', {
    directive: {
      directive: 'UpdateNavigation',
      follower_faction: targetFaction,
      target: { type: 'Waypoint', x: wx, y: wy },
    }
  });
  setSquadOrder(targetFaction, 'move', { x: wx, wy });
}

/**
 * Issue an Attack-Move order (navigate toward an enemy faction).
 * @param {number} targetFaction - Squad sub-faction ID
 * @param {number} enemyFactionId - Faction to attack/chase
 */
export function orderAttack(targetFaction, enemyFactionId) {
  sendCommand('inject_directive', {
    directive: {
      directive: 'UpdateNavigation',
      follower_faction: targetFaction,
      target: { type: 'Faction', faction_id: enemyFactionId },
    }
  });
  // Ensure aggro is enabled
  sendCommand('set_aggro_mask', {
    source_faction: targetFaction,
    target_faction: enemyFactionId,
    allow_combat: true,
  });
  setSquadOrder(targetFaction, 'attack', null);
}

/**
 * Issue a Hold order — stop movement, stay in place.
 * @param {number} targetFaction - Squad sub-faction ID
 */
export function orderHold(targetFaction) {
  sendCommand('inject_directive', {
    directive: {
      directive: 'Hold',
      faction_id: targetFaction,
    }
  });
  setSquadOrder(targetFaction, 'hold', null);
}

/**
 * Issue a Retreat order — move to a safe position.
 * @param {number} targetFaction - Squad sub-faction ID
 * @param {number} wx - Retreat X
 * @param {number} wy - Retreat Y
 */
export function orderRetreat(targetFaction, wx, wy) {
  sendCommand('inject_directive', {
    directive: {
      directive: 'Retreat',
      faction: targetFaction,
      retreat_x: wx,
      retreat_y: wy,
    }
  });
  setSquadOrder(targetFaction, 'retreat', { x: wx, y: wy });
}
