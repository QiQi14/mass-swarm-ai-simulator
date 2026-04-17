# Feature 2: Node Types & Graph Compiler (Tasks 02, 03, 04)

## Task 02: Faction Builder Nodes

**Model Tier:** `standard`
**Execution Phase:** 1 (Depends on T01)
**Live System Impact:** `safe` — new files only

### Target Files
- `debug-visualizer/src/node-editor/nodes/faction.js` — [NEW]
- `debug-visualizer/src/node-editor/nodes/relationship.js` — [NEW] (basic version)

### Context Bindings
- `context/project/conventions.md`
- `strategy_brief.md` — Sections "Faction Node" and "Relationship Node"

### Strict Instructions

#### 1. `src/node-editor/nodes/faction.js`

Exports a `registerFactionNode(editor)` function that registers the Faction node type with Drawflow.

**Drawflow node registration pattern:**
```javascript
import { registerNodeType } from '../drawflow-setup.js';

export function registerFactionNode(editor) {
  registerNodeType('faction', {
    html: getFactionHTML,
    inputs: 0,
    outputs: 4, // units, relationship, trait, general
  });
}
```

**HTML template** for the Faction node — uses `df-*` attributes for auto-sync:

```html
<div class="node-header node-header--faction">
  <span class="node-header__icon">{factionSVG}</span>
  <span>FACTION</span>
</div>
<div class="node-body">
  <div class="node-field">
    <label>Name</label>
    <input type="text" df-name placeholder="Faction Name" class="node-input">
  </div>
  <div class="node-field">
    <label>Color</label>
    <input type="color" df-color value="#ef476f" class="node-color-picker">
  </div>
  <div class="node-field">
    <label>Spawn Count</label>
    <input type="range" df-spawnCount min="10" max="1000" step="10" value="200" class="node-slider">
    <span class="node-slider-value" data-df="spawnCount">200</span>
  </div>
  <div class="node-field node-field--row">
    <div>
      <label>X</label>
      <input type="number" df-spawnX value="400" class="node-input node-input--sm">
    </div>
    <div>
      <label>Y</label>
      <input type="number" df-spawnY value="500" class="node-input node-input--sm">
    </div>
  </div>
  <div class="node-field">
    <label>Spread</label>
    <input type="range" df-spawnSpread min="10" max="300" step="10" value="100" class="node-slider">
    <span class="node-slider-value" data-df="spawnSpread">100</span>
  </div>
</div>
```

**Auto-sync slider display values:** Listen to the Drawflow `nodeDataChanged` event to update `<span>` values.

**Faction ID assignment:** The faction node's `data.factionId` is auto-assigned on creation. Track the next available ID in a module-level counter. When a faction node is deleted, do NOT recycle the ID (avoids collision with cached rules).

**Output ports (visual labels on the right side):**
- Output 1: `units` (connects to Unit nodes)
- Output 2: `relationship` (connects to Relationship nodes)
- Output 3: `trait` (connects to Faction Trait nodes — Phase 3)
- Output 4: `general` (connects to General Brain node — Phase 3)

**Color dot:** Render a small colored circle using the `df-color` value. Update it live when the color picker changes. This dot also appears on connections originating from this node.

#### 2. `src/node-editor/nodes/relationship.js`

Basic version — registers the Relationship node type.

```html
<div class="node-header node-header--relationship">
  <span class="node-header__icon">{linkSVG}</span>
  <span>RELATIONSHIP</span>
</div>
<div class="node-body">
  <div class="node-field">
    <label>Type</label>
    <select df-relationType class="node-select">
      <option value="hostile">⚔️ Hostile</option>
      <option value="neutral">— Neutral</option>
      <option value="allied">🤝 Allied</option>
    </select>
  </div>
</div>
```

**Ports:**
- Input 1: `faction_a`
- Input 2: `faction_b`

**Validation:** Both inputs must be connected to Faction nodes. The compiler will validate this.

### Verification Strategy
```
Test_Type: manual_steps
Test_Stack: Vite dev server
Acceptance_Criteria:
  - "Faction node renders with name, color, count, position, spread fields"
  - "Changing slider updates the display value in real-time"
  - "Color picker updates the faction dot color"
  - "Relationship node renders with type dropdown"
  - "Output ports are visible and connectable"
Manual_Steps:
  - "Create a Drawflow editor, register faction node, add to canvas"
  - "Verify all df-* data syncs to editor.getNodeFromId(id).data"
```

---

## Task 03: Unit Builder Nodes

**Model Tier:** `standard`
**Execution Phase:** 1 (Depends on T01)
**Live System Impact:** `safe` — new files only

### Target Files
- `debug-visualizer/src/node-editor/nodes/unit.js` — [NEW]
- `debug-visualizer/src/node-editor/nodes/stat.js` — [NEW]
- `debug-visualizer/src/node-editor/nodes/death.js` — [NEW]

### Context Bindings
- `context/project/conventions.md`
- `strategy_brief.md` — Sections "Unit Node", "Stat Node", "Death Node"

### Strict Instructions

#### 1. `src/node-editor/nodes/unit.js`

```html
<div class="node-header node-header--unit">
  <span class="node-header__icon">{userSVG}</span>
  <span>UNIT</span>
</div>
<div class="node-body">
  <div class="node-field">
    <label>Name</label>
    <input type="text" df-unitName placeholder="Infantry" class="node-input">
  </div>
  <div class="node-field node-field--readonly">
    <label>Class ID</label>
    <span class="node-mono-value" df-classId>0</span>
  </div>
</div>
```

**Ports:**
- Inputs: `from_faction` (1), `stats` (1), `combat` (1), `death` (1)
- Outputs: `attacker` (1), `target` (1)

`classId` is auto-assigned (like factionId) and displayed as read-only.

#### 2. `src/node-editor/nodes/stat.js`

```html
<div class="node-header node-header--stat">
  <span class="node-header__icon">{barChartSVG}</span>
  <span>STAT</span>
</div>
<div class="node-body">
  <div class="node-field">
    <label>Label</label>
    <input type="text" df-label value="HP" class="node-input">
  </div>
  <div class="node-field node-field--readonly">
    <label>Index</label>
    <span class="node-mono-value" df-statIndex>0</span>
  </div>
  <div class="node-field">
    <label>Initial Value</label>
    <input type="number" df-initialValue value="100" min="0" max="10000" class="node-input">
  </div>
</div>
```

**Ports:**
- Outputs: `value` (1) — connects to Unit's `stats` input, Combat's `damage_stat` input, Death's `check_stat` input

`statIndex` is auto-assigned per Unit node (0–7 max). If 8+ Stat nodes are connected to the same Unit, the compiler emits an error.

#### 3. `src/node-editor/nodes/death.js`

```html
<div class="node-header node-header--death">
  <span class="node-header__icon">{skullSVG}</span>
  <span>DEATH</span>
</div>
<div class="node-body">
  <div class="node-field">
    <label>Condition</label>
    <select df-condition class="node-select">
      <option value="LessThanEqual">≤ Less or Equal</option>
      <option value="GreaterThanEqual">≥ Greater or Equal</option>
    </select>
  </div>
  <div class="node-field">
    <label>Threshold</label>
    <input type="number" df-threshold value="0" class="node-input">
  </div>
</div>
```

**Ports:**
- Inputs: `check_stat` (1) — from Stat node's `value` output

**Default wiring hint:** When a Stat node labeled "HP" is connected, visually indicate "Dies when HP ≤ 0" in muted text below the threshold.

### Verification Strategy
```
Test_Type: manual_steps
Test_Stack: Vite dev server
Acceptance_Criteria:
  - "Unit node renders with name and auto-assigned classId"
  - "Stat node renders with label, auto-index, and initial value"
  - "Death node renders with condition dropdown and threshold"
  - "Stat → Death connection works (output 'value' → input 'check_stat')"
  - "Stat → Unit connection works (output 'value' → input 'stats')"
Manual_Steps:
  - "Create nodes, connect Stat → Unit → Death, verify data syncs"
```

---

## Task 04: Graph Compiler

**Model Tier:** `advanced`
**Execution Phase:** 1 (Depends on T02, T03)
**Live System Impact:** `safe` — new file only

### Target Files
- `debug-visualizer/src/node-editor/compiler.js` — [NEW]

### Context Bindings
- `context/project/conventions.md`
- `context/engine/architecture.md`
- `strategy_brief.md` — Section "Graph-to-Command Compilation"
- `implementation_plan.md` — "Shared Contracts" section (Node Data Schema + Compiler Output Contract)

### Strict Instructions

#### exports

```javascript
/**
 * Compile the current node graph into WS commands.
 * @param {Drawflow} editor — The Drawflow editor instance
 * @returns {CompiledScenario} — See implementation_plan.md Shared Contracts
 */
export function compileGraph(editor) { ... }

/**
 * Execute a compiled scenario by sending WS commands.
 * @param {CompiledScenario} scenario
 * @param {(cmd: string, params: object) => boolean} sendCommand
 */
export function executeScenario(scenario, sendCommand) { ... }

/**
 * Convert existing preset JSON to Drawflow graph JSON to populate the editor.
 * @param {string} presetKey — from algorithm-test.js PRESETS
 * @returns {object} — Drawflow-compatible export JSON
 */
export function presetToGraph(presetKey) { ... }
```

#### compileGraph() algorithm

```
1. Get all nodes from editor.export().drawflow.Home.data
2. Categorize nodes by nodeType into buckets
3. Walk connections to build graph relationships:
   a. For each Faction node, find connected Unit nodes (via 'units' output)
   b. For each Unit node, find connected Stat nodes (via 'stats' input)
   c. For each Unit node, find connected Death nodes (via 'death' input)
   d. For each Unit node, find connected Combat nodes (via 'combat' input)
   e. For each Faction node, find connected Relationship nodes
   f. For each Faction node, find connected Navigation nodes
4. Validate:
   - Every Faction must have at least one Unit connected
   - Every Unit must have at least one Stat (HP) connected
   - Every Unit should have a Death node (warn if missing)
   - Stat indices must be unique per Unit (0-7 range)
5. Compile:
   a. spawns[] — one spawn_wave per faction×unit combination
   b. interaction.rules[] — from Combat nodes + connections
   c. removal.rules[] — from Death nodes
   d. navigation.rules[] — from Navigation nodes (skip if General connected)
   e. aggro[] — from Relationship nodes
6. Return { spawns, navigation, interaction, removal, aggro, brains: [], errors }
```

#### executeScenario() algorithm

Follows the 6-phase pipeline from the strategy brief:

```javascript
export function executeScenario(scenario, sendCommand) {
  if (scenario.errors.length > 0) {
    // Show errors to user, abort
    return { success: false, errors: scenario.errors };
  }

  // Phase 1: Collect (already done by compileGraph)

  // Phase 2: Clear — kill all entities for each involved faction
  const factionIds = new Set(scenario.spawns.map(s => s.faction_id));
  for (const fid of factionIds) {
    sendCommand('kill_all', { faction_id: fid });
  }

  // Phase 3: Rules
  if (scenario.navigation.rules.length > 0) {
    sendCommand('set_navigation', scenario.navigation);
  }
  if (scenario.interaction.rules.length > 0) {
    sendCommand('set_interaction', scenario.interaction);
  }
  if (scenario.removal.rules.length > 0) {
    sendCommand('set_removal', scenario.removal);
  }
  for (const aggro of scenario.aggro) {
    sendCommand('set_aggro_mask', aggro);
  }

  // Phase 4: Spawn (100ms delay after rules)
  setTimeout(() => {
    for (const spawn of scenario.spawns) {
      sendCommand('spawn_wave', spawn);
    }
  }, 100);

  // Phase 5: Brain Init — Phase 3 (General node), no-op for now
  // Phase 6: Resume — toggle sim if paused
  setTimeout(() => {
    sendCommand('toggle_sim', {});
  }, 200);

  return { success: true, errors: [] };
}
```

#### presetToGraph() — converts legacy presets to node graphs

This function receives a preset key (e.g., `'swarm_vs_defender'`), reads the preset data from `algorithm-test.js`, and generates a Drawflow-compatible JSON object that can be loaded via `editor.import(json)`.

**Node placement algorithm:** Place Faction nodes in a row at the top, Unit/Stat/Death chains below each Faction node, with Combat nodes connecting between Unit outputs.

### Verification Strategy
```
Test_Type: unit
Test_Stack: Vite + Vitest (or browser console)
Acceptance_Criteria:
  - "compileGraph on a 2-faction graph produces correct spawn_wave commands"
  - "compileGraph on empty graph returns errors array: ['No faction nodes found']"
  - "executeScenario calls sendCommand in correct order (kill → nav → interaction → removal → spawn)"
  - "presetToGraph('swarm_vs_defender') returns valid Drawflow JSON"
Suggested_Test_Commands:
  - "Import compiler.js in browser console, test with mock editor.export() data"
```
