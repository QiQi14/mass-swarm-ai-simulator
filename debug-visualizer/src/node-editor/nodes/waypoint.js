import { registerNodeType } from '../drawflow-setup.js';

const mapPinSVG = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>`;

export function registerWaypointNode(editor) {
  const getHTML = `
    <div class="node-header node-header--waypoint">
      <span class="node-header__icon">${mapPinSVG}</span>
      <span>WAYPOINT</span>
    </div>
    <div class="node-body">
      <div class="node-field node-field--row">
        <div>
          <label>X</label>
          <input type="number" df-x value="500" class="node-input node-input--sm">
        </div>
        <div>
          <label>Y</label>
          <input type="number" df-y value="500" class="node-input node-input--sm">
        </div>
      </div>
    </div>
  `;

  registerNodeType('waypoint', {
    html: getHTML,
    inputs: 0,
    outputs: 1, // position
  });

  editor.on('nodeCreated', (id) => {
    try {
      const node = editor.getNodeFromId(id);
      if (node.name === 'waypoint') {
        const currentData = { ...node.data };
        currentData.nodeType = 'waypoint';
        if (currentData.x === undefined) currentData.x = 500;
        if (currentData.y === undefined) currentData.y = 500;
        editor.updateNodeDataFromId(id, currentData);
      }
    } catch (e) {}
  });
}
