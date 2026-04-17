import { registerNodeType } from '../drawflow-setup.js';

const factionSVG = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>`;

let nextFactionId = 0;

export function registerFactionNode(editor) {
  const getFactionHTML = `
    <div class="node-header node-header--faction">
      <span class="node-header__icon">${factionSVG}</span>
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
  `;

  registerNodeType('faction', {
    html: getFactionHTML,
    inputs: 0,
    outputs: 4, // units, relationship, trait, general
  });

  // Handle data auto-assignment and defaults
  editor.on('nodeCreated', (id) => {
    try {
      const node = editor.getNodeFromId(id);
      if (node.name === 'faction') {
        const currentData = { ...node.data };
        currentData.nodeType = 'faction';
        // Only assign ID if not already given (preserves behavior if imported)
        if (currentData.factionId === undefined) {
          currentData.factionId = nextFactionId++;
        } else {
          // ensure nextFactionId stays ahead of imported IDs
          nextFactionId = Math.max(nextFactionId, currentData.factionId + 1);
        }

        if (currentData.name === undefined) currentData.name = 'Alpha';
        if (currentData.color === undefined) currentData.color = '#ef476f';
        if (currentData.spawnCount === undefined) currentData.spawnCount = 200;
        if (currentData.spawnX === undefined) currentData.spawnX = 400;
        if (currentData.spawnY === undefined) currentData.spawnY = 500;
        if (currentData.spawnSpread === undefined) currentData.spawnSpread = 100;

        editor.updateNodeDataFromId(id, currentData);

        // Initial UI sync
        syncFactionNodeUI(id, currentData);
      }
    } catch (e) {
      // Node might not be found in some edge cases
    }
  });

  editor.on('nodeDataChanged', (id) => {
    try {
      const node = editor.getNodeFromId(id);
      if (node.name === 'faction') {
        syncFactionNodeUI(id, node.data);
      }
    } catch (e) { }
  });

  function syncFactionNodeUI(id, data) {
    const nodeElement = document.getElementById(`node-${id}`);
    if (nodeElement) {
      // Update color representation on ports
      const outputs = nodeElement.querySelectorAll('.output');
      outputs.forEach(output => {
        output.style.backgroundColor = data.color || '#ef476f';
      });
      // Ensure border color of the node matches faction flavor
      nodeElement.style.borderLeft = `4px solid ${data.color || '#ef476f'}`;

      // Update slider texts
      const spawnCountSpan = nodeElement.querySelector('.node-slider-value[data-df="spawnCount"]');
      if (spawnCountSpan) spawnCountSpan.textContent = data.spawnCount;

      const spawnSpreadSpan = nodeElement.querySelector('.node-slider-value[data-df="spawnSpread"]');
      if (spawnSpreadSpan) spawnSpreadSpan.textContent = data.spawnSpread;
    }
  }
}
