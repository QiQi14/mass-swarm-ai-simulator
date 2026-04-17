# Feature 4: Tactical Canvas — Squad Control (Tasks 12–16)

> [!NOTE]
> **All tasks in this feature are 100% frontend JavaScript + CSS.** No Rust micro-core changes are needed. Squad commands leverage the existing engine directives via the `inject_directive` WS command, which deserializes any `MacroDirective` variant.

## Design Rationale

At 10K entities, individual unit selection is impractical. Instead, the player operates at the **squad level**, where a squad maps directly to the engine's **sub-faction** concept:

1. **Selection** → Player box-drags or faction-clicks to highlight a group of entities
2. **Squad Creation** → The selection is carved into a sub-faction via `SplitFaction` (epicenter = centroid of selection, percentage = % of source faction selected)
3. **Orders** → Right-click sends `inject_directive` with `UpdateNavigation`, `Hold`, or `Retreat`
4. **Squad Dissolution** → `MergeFaction` merges the sub-faction back into its parent

### Engine Directive Mapping

| Player Action | WS Command | MacroDirective |
|---------------|-----------|----------------|
| Right-click on map (Move) | `inject_directive` | `UpdateNavigation { follower_faction: squadId, target: Waypoint { x, y } }` |
| Right-click on enemy (Attack-Move) | `inject_directive` | `UpdateNavigation { follower_faction: squadId, target: Faction { faction_id: enemyId } }` |
| Hold button | `inject_directive` | `Hold { faction_id: squadId }` |
| Retreat button + click | `inject_directive` | `Retreat { faction: squadId, retreat_x, retreat_y }` |
| Create Squad | `split_faction` | Splits source faction near epicenter |
| Disband Squad | `merge_faction` | Merges sub-faction back to parent |
| Toggle aggro | `set_aggro_mask` | Enable/disable combat vs specific factions |

### Client-Side Entity Data

`S.entities` (Map<id, { x, y, dx, dy, faction_id, stats }>) is updated every tick by `ws_sync_system`. This gives us:
- **Position** for spatial selection (box-select hit test)
- **faction_id** for grouping (know which faction/sub-faction an entity belongs to)
- **stats[0]** (HP) for aggregate health display

No server round-trip is needed for selection queries — all data is local.

---

## Task 12: Selection System

**Model Tier:** `standard`
**Execution Phase:** 4 (Depends on T07)
**Live System Impact:** `additive` — new module + state extensions

### Target Files
- `debug-visualizer/src/controls/selection.js` — [NEW]
- `debug-visualizer/src/state.js` — MODIFY (add selection state)

### Context Bindings
- `context/project/conventions.md`
- `skills/frontend-ux-ui`

### Strict Instructions

#### 1. Extend `state.js` — Add selection state

```javascript
// ── Selection State ──
export let selectionMode = false;
export function setSelectionMode(v) { selectionMode = v; }

// Current selection: set of entity IDs
export let selectedEntities = new Set();
export function setSelectedEntities(v) { selectedEntities = v; }
export function clearSelection() { selectedEntities = new Set(); }

// Box-select in progress
export let selectionBoxStart = null;  // { wx, wy } world coords
export function setSelectionBoxStart(v) { selectionBoxStart = v; }
export let selectionBoxEnd = null;    // { wx, wy } world coords
export function setSelectionBoxEnd(v) { selectionBoxEnd = v; }
export let isBoxSelecting = false;
export function setIsBoxSelecting(v) { isBoxSelecting = v; }

// Selected squad (active after squad created from selection)
export let activeSquadId = null;  // sub-faction ID
export function setActiveSquadId(v) { activeSquadId = v; }
```

#### 2. Create `selection.js`

```javascript
/**
 * Perform box-select: find all entities within a world-space bounding box.
 * @param {number} x1 - Start X (world coords)
 * @param {number} y1 - Start Y (world coords)
 * @param {number} x2 - End X (world coords)
 * @param {number} y2 - End Y (world coords)
 * @returns {Set<number>} Set of entity IDs within the box
 */
export function boxSelect(x1, y1, x2, y2) { ... }

/**
 * Perform faction-click: select all entities of a faction near click point.
 * Uses a radius-based proximity test.
 * @param {number} wx - Click X (world coords)
 * @param {number} wy - Click Y (world coords)
 * @param {number} radius - Selection radius (default: 100 world units)
 * @returns {{ factionId: number, entities: Set<number> }}
 */
export function factionClickSelect(wx, wy, radius = 100) { ... }

/**
 * Get the centroid (average position) of selected entities.
 * @param {Set<number>} entityIds
 * @returns {{ x: number, y: number }}
 */
export function getSelectionCentroid(entityIds) { ... }

/**
 * Get aggregate stats for selected entities.
 * @param {Set<number>} entityIds
 * @returns {{ count: number, factionId: number, avgHp: number, totalHp: number }}
 */
export function getSelectionStats(entityIds) { ... }
```

**Box-select algorithm** (client-side, no WS round-trip):
```javascript
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
```

**Faction-click select** — when clicking without dragging, find the nearest entity, then select ALL entities of the same faction within a radius:
```javascript
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
```

#### 3. Integrate into `controls/init.js`

> [!IMPORTANT]
> The selection system runs in **Command Mode** — a new interaction mode alongside the existing spawn/paint/split/zone modes. Command Mode is the **default mode** in the new playground. The existing `handleSelectClick` (single entity) is replaced by squad-level selection.

**Command Mode activation:** When no other mode is active and user is on the canvas:
- **Left-click-drag** → box-select
- **Left-click (no drag)** → faction-click-select
- **Right-click** → issue order (handled by T14)
- **Escape** → clear selection

**Box-select interaction flow:**
```
mousedown (left, no mode active):
  → Start box selection (record world-space start)
  
mousemove (while box-selecting):
  → Update box end position
  → Preview: highlight entities in box
  
mouseup:
  → If box is > 5px: run boxSelect(start, end) → setSelectedEntities()
  → If box is < 5px: run factionClickSelect(wx, wy) → setSelectedEntities()
```

### Verification Strategy
```
Test_Type: manual_steps
Test_Stack: Vite dev server
Acceptance_Criteria:
  - "Left-click-drag draws a selection box on the canvas"
  - "Releasing the box highlights selected entities (glow ring)"
  - "Left-click on a cluster selects nearby entities of the same faction"
  - "Escape clears selection"
  - "Selection persists across simulation ticks (entities update position but stay selected)"
  - "Box-select performance: <5ms for 10K entities"
Manual_Steps:
  - "Spawn 200 units → box-drag over half → verify ~100 selected"
  - "Click on a faction cluster → verify all nearby same-faction entities selected"
  - "Press Escape → verify selection cleared"
```

---

## Task 13: Squad Manager

**Model Tier:** `advanced`
**Execution Phase:** 4 (Depends on T12)
**Live System Impact:** `additive` — new module

### Target Files
- `debug-visualizer/src/squads/squad-manager.js` — [NEW]
- `debug-visualizer/src/state.js` — MODIFY (add squad registry)

### Context Bindings
- `context/project/conventions.md`
- `context/engine/navigation.md` — §7b Unit Type Registry, sub-factions
- `context/engine/combat.md` — §2 Combat System (interaction rule duplication on split)

### Strict Instructions

#### 1. Extend `state.js` — Squad registry

```javascript
// ── Squad Registry ──
// Map<squadId (sub-faction ID), SquadInfo>
export const squads = new Map();

/**
 * @typedef {Object} SquadInfo
 * @property {number} id - Sub-faction ID
 * @property {number} parentFactionId - Original faction before split
 * @property {string} name - User-visible name (e.g., "Alpha Squad")
 * @property {string} color - CSS color string (derived from parent + offset)
 * @property {{ x: number, y: number } | null} currentTarget - Active navigation target
 * @property {string} currentOrder - 'idle' | 'move' | 'attack' | 'hold' | 'retreat'
 * @property {number} createdTick - Tick when squad was created
 */
```

#### 2. Create `squad-manager.js`

```javascript
import * as S from '../state.js';
import { sendCommand } from '../websocket.js';

/** Auto-increment for squad naming */
let squadNameCounter = 0;
const SQUAD_NAMES = ['Alpha', 'Bravo', 'Charlie', 'Delta', 'Echo', 'Foxtrot',
                     'Golf', 'Hotel', 'India', 'Juliet', 'Kilo', 'Lima'];

/**
 * Create a squad from the current selection.
 * Uses SplitFaction to carve out a sub-faction from the selected entities.
 *
 * @returns {number|null} The new squad (sub-faction) ID, or null on failure
 */
export function createSquadFromSelection() { ... }

/**
 * Disband a squad by merging it back into its parent faction.
 * @param {number} squadId - Sub-faction ID to merge
 */
export function disbandSquad(squadId) { ... }

/**
 * Get live stats for a squad (reads from S.entities).
 * @param {number} squadId - Sub-faction ID
 * @returns {{ count: number, avgHp: number, centroid: { x: number, y: number } }}
 */
export function getSquadStats(squadId) { ... }

/**
 * Update squad's current order state (for display purposes).
 * @param {number} squadId
 * @param {string} order - 'idle' | 'move' | 'attack' | 'hold' | 'retreat'
 * @param {{ x: number, y: number } | null} target
 */
export function setSquadOrder(squadId, order, target = null) { ... }

/**
 * Check if any tracked squads have been fully eliminated (0 entities).
 * Auto-removes them from the registry.
 */
export function pruneDeadSquads() { ... }
```

**createSquadFromSelection() algorithm:**
```javascript
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
```

**disbandSquad() algorithm:**
```javascript
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
```

**pruneDeadSquads()** — call from render loop every 60 frames:
```javascript
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
```

### Verification Strategy
```
Test_Type: manual_steps
Test_Stack: Vite dev server
Acceptance_Criteria:
  - "Box-select entities → 'Create Squad' button appears → click → squad created"
  - "Squad appears in registry with auto-name (Alpha, Bravo, ...)"
  - "Squad entities have different sub-faction ID in S.entities after next tick sync"
  - "Disband squad → entities merge back to parent faction"
  - "Dead squads auto-pruned after all entities eliminated"
Manual_Steps:
  - "Spawn 200 faction 0 → box-select 50 → create squad → verify SplitFaction sent"
  - "Verify sub-faction appears in S.activeSubFactions after next WS tick"
  - "Click Disband → verify MergeFaction sent → entities return to faction 0"
```

---

## Task 14: Order System

**Model Tier:** `standard`
**Execution Phase:** 4 (Depends on T13)
**Live System Impact:** `additive`

### Target Files
- `debug-visualizer/src/squads/order-system.js` — [NEW]
- `debug-visualizer/src/controls/init.js` — MODIFY (add right-click handler)

### Context Bindings
- `context/project/conventions.md`
- `context/engine/navigation.md`

### Strict Instructions

#### 1. Create `order-system.js`

```javascript
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
  setSquadOrder(targetFaction, 'move', { x: wx, y: wy });
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
```

#### 2. Extend `controls/init.js` — Right-click handler

> [!IMPORTANT]
> Right-click is **only active when a squad is selected** (`S.activeSquadId !== null`). Without a selected squad, right-click does nothing (or shows a browser context menu on non-canvas elements).

```javascript
canvasEntities.addEventListener('contextmenu', (e) => {
  e.preventDefault();
  if (!S.activeSquadId) return;

  const rect = canvasEntities.getBoundingClientRect();
  const [wx, wy] = canvasToWorld(e.clientX - rect.left, e.clientY - rect.top);

  // Check if right-clicked on an enemy entity
  let nearestEnemy = null;
  let nearestDist = Infinity;
  for (const [id, ent] of S.entities) {
    if (ent.faction_id === S.activeSquadId) continue;  // skip own squad
    const squad = S.squads.get(S.activeSquadId);
    if (squad && ent.faction_id === squad.parentFactionId) continue;  // skip allies
    const d = (ent.x - wx) ** 2 + (ent.y - wy) ** 2;
    if (d < nearestDist) { nearestDist = d; nearestEnemy = ent; }
  }

  if (nearestEnemy && nearestDist < 2500) {  // 50px radius
    // Attack-move toward enemy faction
    orderAttack(S.activeSquadId, nearestEnemy.faction_id);
    showToast(`Attacking faction ${nearestEnemy.faction_id}`, 'success');
  } else {
    // Move to waypoint
    orderMove(S.activeSquadId, wx, wy);
  }
});
```

**Keyboard shortcuts** (when a squad is selected):
- `H` → Hold
- `R` + click → Retreat mode (next click sets retreat point)
- `Delete` → Disband squad
- `Escape` → Deselect squad

### Verification Strategy
```
Test_Type: manual_steps
Test_Stack: Vite dev server
Acceptance_Criteria:
  - "Right-click on empty map sends UpdateNavigation (Waypoint)"
  - "Right-click on enemy sends UpdateNavigation (Faction) + SetAggroMask"
  - "H key sends Hold directive"
  - "Squad entities actually move to waypoint (visible on canvas)"
  - "Order arrow appears on canvas (see T15)"
Manual_Steps:
  - "Create squad → right-click on map corner → verify entities navigate there"
  - "Create squad → right-click on enemy cluster → verify attack-move"
  - "Press H → verify entities stop moving"
```

---

## Task 15: Tactical Canvas Overlay

**Model Tier:** `standard`
**Execution Phase:** 4 (Depends on T13)
**Live System Impact:** `additive`

### Target Files
- `debug-visualizer/src/draw/tactical-overlay.js` — [NEW]
- `debug-visualizer/src/draw/entities.js` — MODIFY (integrate tactical overlay call)
- `debug-visualizer/src/styles/tactical.css` — [NEW]

### Context Bindings
- `context/project/conventions.md`
- `skills/frontend-ux-ui`

### Strict Instructions

#### 1. Create `tactical-overlay.js`

Renders tactical UI elements on the entity canvas layer. Called from the render loop, AFTER entity drawing.

```javascript
/**
 * Draw all tactical overlays on the entity canvas.
 * @param {CanvasRenderingContext2D} ctx
 * @param {number} cullLeft/Right/Top/Bottom - Culling bounds
 */
export function drawTacticalOverlay(ctx, cullLeft, cullRight, cullTop, cullBottom) {
  drawSelectionBox(ctx);
  drawSelectedEntityHighlights(ctx);
  drawSquadBanners(ctx);
  drawOrderArrows(ctx);
  drawRallyPoints(ctx);
}
```

**Selection Box** — rubber-band rectangle during box-select:
```javascript
function drawSelectionBox(ctx) {
  if (!S.isBoxSelecting || !S.selectionBoxStart || !S.selectionBoxEnd) return;
  const [sx, sy] = worldToCanvas(S.selectionBoxStart.wx, S.selectionBoxStart.wy);
  const [ex, ey] = worldToCanvas(S.selectionBoxEnd.wx, S.selectionBoxEnd.wy);

  ctx.strokeStyle = 'rgba(6, 214, 160, 0.8)';  // accent-primary
  ctx.lineWidth = 1.5;
  ctx.setLineDash([4, 4]);
  ctx.strokeRect(sx, sy, ex - sx, ey - sy);
  ctx.setLineDash([]);

  ctx.fillStyle = 'rgba(6, 214, 160, 0.08)';
  ctx.fillRect(sx, sy, ex - sx, ey - sy);
}
```

**Selected Entity Highlights** — glow ring on selected entities (lighter weight than per-entity selection):
```javascript
function drawSelectedEntityHighlights(ctx) {
  if (S.selectedEntities.size === 0 && !S.activeSquadId) return;

  const targetSet = S.activeSquadId
    ? getSquadEntityIds(S.activeSquadId)  // highlight all squad members
    : S.selectedEntities;

  ctx.strokeStyle = 'rgba(6, 214, 160, 0.6)';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  for (const id of targetSet) {
    const ent = S.entities.get(id);
    if (!ent) continue;
    const [cx, cy] = worldToCanvas(ent.x, ent.y);
    ctx.moveTo(cx + (radius + 3), cy);
    ctx.arc(cx, cy, radius + 3, 0, Math.PI * 2);
  }
  ctx.stroke();
}
```

> [!WARNING]
> **Performance.** For 10K entities, drawing individual highlight rings per entity is expensive. Use two optimization strategies:
> 1. **Culling** — only draw highlights for on-screen entities
> 2. **Batch path** — use a single `beginPath()` + `stroke()` for all highlights (already shown above)
> 3. **At >500 selected:** Switch to a convex hull outline instead of per-entity rings

**Squad Banners** — floating label at squad centroid:
```javascript
function drawSquadBanners(ctx) {
  for (const [squadId, info] of S.squads) {
    const stats = getSquadStats(squadId);
    if (stats.count === 0) continue;

    const [cx, cy] = worldToCanvas(stats.centroid.x, stats.centroid.y);

    // Banner background (glassmorphic pill)
    const text = `${info.name} (${stats.count})`;
    const metrics = ctx.measureText(text);
    const pw = metrics.width + 16;
    const ph = 22;

    ctx.fillStyle = 'rgba(6, 10, 16, 0.7)';
    roundRect(ctx, cx - pw / 2, cy - 30 - ph, pw, ph, 6);
    ctx.fill();

    // Border
    ctx.strokeStyle = info.color || 'rgba(255,255,255,0.2)';
    ctx.lineWidth = 1;
    roundRect(ctx, cx - pw / 2, cy - 30 - ph, pw, ph, 6);
    ctx.stroke();

    // Text
    ctx.fillStyle = '#e8ecf0';
    ctx.font = '11px "IBM Plex Mono"';
    ctx.textAlign = 'center';
    ctx.fillText(text, cx, cy - 30 - 6);

    // Order icon
    const orderIcon = { idle: '•', move: '→', attack: '⚔', hold: '■', retreat: '←' };
    ctx.fillStyle = info.currentOrder === 'attack' ? '#ef476f' : '#06d6a0';
    ctx.fillText(orderIcon[info.currentOrder] || '•', cx + pw / 2 + 8, cy - 30 - 6);
  }
}
```

**Order Arrows** — line from squad centroid to target:
```javascript
function drawOrderArrows(ctx) {
  for (const [squadId, info] of S.squads) {
    if (!info.currentTarget) continue;
    const stats = getSquadStats(squadId);
    if (stats.count === 0) continue;

    const [sx, sy] = worldToCanvas(stats.centroid.x, stats.centroid.y);
    const [tx, ty] = worldToCanvas(info.currentTarget.x, info.currentTarget.y);

    // Pulsing dashed line
    const pulse = 0.4 + 0.3 * Math.sin(Date.now() / 400);
    ctx.strokeStyle = info.currentOrder === 'attack'
      ? `rgba(239, 71, 111, ${pulse})`
      : `rgba(6, 214, 160, ${pulse})`;
    ctx.lineWidth = 2;
    ctx.setLineDash([8, 4]);
    ctx.beginPath();
    ctx.moveTo(sx, sy);
    ctx.lineTo(tx, ty);
    ctx.stroke();
    ctx.setLineDash([]);

    // Target marker (diamond)
    drawDiamond(ctx, tx, ty, 8);
  }
}
```

**Rally Points** — marker at waypoint targets:
```javascript
function drawRallyPoints(ctx) {
  for (const [squadId, info] of S.squads) {
    if (info.currentOrder !== 'move' || !info.currentTarget) continue;
    const [tx, ty] = worldToCanvas(info.currentTarget.x, info.currentTarget.y);

    // Animated concentric circles
    const t = (Date.now() % 2000) / 2000;
    const maxR = 20;
    ctx.strokeStyle = `rgba(6, 214, 160, ${1 - t})`;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(tx, ty, t * maxR, 0, Math.PI * 2);
    ctx.stroke();
  }
}
```

#### 2. Integrate into `entities.js`

After the existing `drawHealthBars()` and `drawDeathAnimations()` calls, add:
```javascript
import { drawTacticalOverlay } from './tactical-overlay.js';
// ... at end of drawEntities():
drawTacticalOverlay(ctx, cullLeft, cullRight, cullTop, cullBottom);
```

#### 3. Create `tactical.css`

Minimal CSS for any HTML-overlay tactical elements (mostly canvas-drawn, but tooltips/menus may use DOM):

```css
.tactical-context-menu {
  position: fixed;
  z-index: 2000;
  background: rgba(6, 10, 16, 0.92);
  backdrop-filter: blur(12px) saturate(1.8);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 4px 0;
  min-width: 140px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

.tactical-context-menu__item {
  padding: 8px 16px;
  color: var(--text-primary);
  font: 500 12px var(--font-display);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background 0.15s;
}

.tactical-context-menu__item:hover {
  background: rgba(255, 255, 255, 0.06);
}

.tactical-context-menu__item--danger {
  color: var(--accent-danger);
}
```

### Verification Strategy
```
Test_Type: manual_steps
Acceptance_Criteria:
  - "Green selection box appears during drag"
  - "Selected entities show green highlight rings"
  - "Squad banners float above squad centroids"
  - "Order arrows pulse from squad to waypoint"
  - "Rally point animation plays at move targets"
  - "Performance: no FPS drop with 5 squads and 10K entities"
```

---

## Task 16: Squad Control Panel

**Model Tier:** `standard`
**Execution Phase:** 4 (Depends on T13, T10)
**Live System Impact:** `additive`

### Target Files
- `debug-visualizer/src/panels/playground/squad-panel.js` — [NEW]
- `debug-visualizer/src/styles/playground-overlay.css` — MODIFY (extend)

### Context Bindings
- `context/project/conventions.md`
- `skills/frontend-ux-ui`

### Strict Instructions

#### 1. Create `squad-panel.js`

An overlay card that appears when a squad is active (`S.activeSquadId != null`). Mounted in the right cluster area.

```javascript
/**
 * Build and mount the squad control panel.
 * @param {HTMLElement} container - Right-side overlay cluster
 */
export function mountSquadPanel(container) { ... }

/**
 * Update the squad panel with live data (called from render loop).
 */
export function updateSquadPanel() { ... }
```

**Panel DOM Structure:**
```html
<div class="overlay-card overlay-card--squad" id="squad-panel">
  <div class="overlay-card__header">
    <span class="overlay-card__header-dot" style="background: {squadColor}"></span>
    <span>{squadName} SQUAD</span>
    <span class="overlay-card__header-count">{count} units</span>
  </div>
  <div class="overlay-card__body">
    <!-- HP Bar -->
    <div class="squad-hp-bar">
      <div class="squad-hp-bar__fill" style="width: {avgHpPct}%"></div>
      <span class="squad-hp-bar__label">{avgHp} HP avg</span>
    </div>

    <!-- Current Order -->
    <div class="squad-order">
      <span class="squad-order__icon">{orderIcon}</span>
      <span class="squad-order__text">{orderDescription}</span>
    </div>

    <!-- Action Buttons -->
    <div class="squad-actions">
      <button class="squad-btn" data-cmd="move" title="Move (Right-click)">
        {compassSVG} Move
      </button>
      <button class="squad-btn squad-btn--attack" data-cmd="attack" title="Attack">
        {swordsSVG} Attack
      </button>
      <button class="squad-btn" data-cmd="hold" title="Hold (H)">
        {shieldSVG} Hold
      </button>
      <button class="squad-btn" data-cmd="retreat" title="Retreat (R)">
        {arrowLeftSVG} Retreat
      </button>
    </div>

    <!-- Footer -->
    <div class="squad-footer">
      <button class="squad-btn squad-btn--danger" data-cmd="disband">
        Disband Squad
      </button>
    </div>
  </div>
</div>
```

**Live Update** (called every frame from render loop):
```javascript
export function updateSquadPanel() {
  if (!S.activeSquadId) {
    hide squad panel;
    return;
  }
  const stats = getSquadStats(S.activeSquadId);
  const info = S.squads.get(S.activeSquadId);
  if (!info || stats.count === 0) {
    // Squad eliminated
    hide squad panel;
    return;
  }

  // Update count, HP bar, order text
  countEl.textContent = `${stats.count} units`;
  hpFill.style.width = `${(stats.avgHp / 100) * 100}%`;
  orderText.textContent = getOrderDescription(info.currentOrder, info.currentTarget);
}
```

**Action button handlers:**
- **Move** → activates "Move Mode" (next left-click on map sends orderMove)
- **Attack** → activates "Attack Mode" (next left-click on enemy sends orderAttack)
- **Hold** → immediate: calls orderHold
- **Retreat** → activates "Retreat Mode" (next left-click on map sends orderRetreat)
- **Disband** → immediate: calls disbandSquad

#### 2. Styling

Extend `playground-overlay.css`:
```css
.squad-hp-bar {
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  overflow: hidden;
  position: relative;
  margin: 8px 0;
}

.squad-hp-bar__fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
  border-radius: 3px;
  transition: width 0.3s ease;
}

.squad-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  margin-top: 8px;
}

.squad-btn {
  padding: 6px 10px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-primary);
  border-radius: 6px;
  font: 500 11px var(--font-display);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  justify-content: center;
  transition: var(--transition-base);
}

.squad-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: var(--border-emphasis);
}

.squad-btn--attack {
  border-color: rgba(239, 71, 111, 0.3);
}

.squad-btn--danger {
  color: var(--accent-danger);
  border-color: rgba(239, 71, 111, 0.2);
  grid-column: 1 / -1;  /* full width */
}
```

### Verification Strategy
```
Test_Type: manual_steps
Acceptance_Criteria:
  - "Squad panel appears when squad is selected"
  - "Panel shows live unit count and average HP"
  - "Action buttons send correct WS commands"
  - "Disband merges squad back"
  - "Panel hides when squad eliminated or deselected"
  - "Stylingmatches glassmorphic overlay-card pattern"
Manual_Steps:
  - "Create squad → verify panel appears with Alpha Squad info"
  - "Click Move → click map → verify entities navigate"
  - "Press Hold → verify order indicator changes"
  - "Click Disband → verify panel hides and entities merge back"
```
