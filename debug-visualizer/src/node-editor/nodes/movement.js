import { registerNodeType } from '../drawflow-setup.js';

const moveSVG = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="5 9 2 12 5 15"/><polyline points="9 5 12 2 15 5"/><polyline points="19 9 22 12 19 15"/><polyline points="9 19 12 22 15 19"/><line x1="2" x2="22" y1="12" y2="12"/><line x1="12" x2="12" y1="2" y2="22"/></svg>`;

export function registerMovementNode(editor) {
  const getHTML = `
    <div class="node-header node-header--movement">
      <span class="node-header__icon">${moveSVG}</span>
      <span>MOVEMENT</span>
    </div>
    <div class="node-body">
      <div class="node-field">
        <label>Speed</label>
        <div class="node-preset-btns">
          <button class="node-preset-btn" data-preset="slow">🐢 Slow</button>
          <button class="node-preset-btn node-preset-btn--active" data-preset="normal">Normal</button>
          <button class="node-preset-btn" data-preset="fast">⚡ Fast</button>
        </div>
      </div>
      <div class="node-field">
        <label>Max Speed</label>
        <input type="number" df-maxSpeed value="100" class="node-input">
      </div>
      <div class="node-field">
        <label>Engagement Range</label>
        <input type="number" df-engagementRange value="15" class="node-input">
      </div>
    </div>
  `;

  registerNodeType('movement', {
    html: getHTML,
    inputs: 1, // unit
    outputs: 0,
  });

  editor.on('nodeCreated', (id) => {
    try {
      const node = editor.getNodeFromId(id);
      if (node.name === 'movement') {
        const currentData = { ...node.data };
        currentData.nodeType = 'movement';
        if (currentData.speedPreset === undefined) currentData.speedPreset = 'normal';
        if (currentData.maxSpeed === undefined) currentData.maxSpeed = 100;
        if (currentData.engagementRange === undefined) currentData.engagementRange = 15;
        if (currentData.steeringFactor === undefined) currentData.steeringFactor = 1.0;
        if (currentData.separationRadius === undefined) currentData.separationRadius = 10;
        editor.updateNodeDataFromId(id, currentData);
        syncMovementUI(id, currentData);
      }
    } catch (e) {}
  });

  editor.on('nodeDataChanged', (id) => {
    try {
      const node = editor.getNodeFromId(id);
      if (node.name === 'movement') {
        syncMovementUI(id, node.data);
      }
    } catch (e) {}
  });

  document.addEventListener('click', (e) => {
    if (e.target.matches('.node-preset-btn') && e.target.closest('.node-header--movement ~ .node-body')) {
      const btn = e.target;
      const nodeElement = btn.closest('.drawflow-node');
      if (!nodeElement) return;
      const id = nodeElement.id.replace('node-', '');
      const preset = btn.dataset.preset;
      
      const node = editor.getNodeFromId(id);
      const newData = { ...node.data, speedPreset: preset };
      
      if (preset === 'slow') {
          newData.maxSpeed = 50;
      } else if (preset === 'normal') {
          newData.maxSpeed = 100;
      } else if (preset === 'fast') {
          newData.maxSpeed = 150;
      }
      
      editor.updateNodeDataFromId(id, newData);
      
      const maxSpeedInput = nodeElement.querySelector('input[df-maxSpeed]');
      if (maxSpeedInput) maxSpeedInput.value = newData.maxSpeed;
      
      syncMovementUI(id, newData);
    }
  });

  function syncMovementUI(id, data) {
    const nodeElement = document.getElementById(`node-${id}`);
    if (nodeElement) {
        nodeElement.querySelectorAll('.node-preset-btn').forEach(b => {
             if (b.dataset.preset === data.speedPreset) {
                 b.classList.add('node-preset-btn--active');
             } else {
                 b.classList.remove('node-preset-btn--active');
             }
        });
    }
  }
}
