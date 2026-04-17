import { registerNodeType } from '../drawflow-setup.js';

const skullSVG = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="9" cy="12" r="1"></circle><circle cx="15" cy="12" r="1"></circle><path d="M8 20v2h8v-2"></path><path d="m12.5 17-.5-1-.5 1h1z"></path><path d="M16 20a2 2 0 0 0 1.56-3.25 8 8 0 1 0-11.12 0A2 2 0 0 0 8 20"></path></svg>`;

const html = `
<div class="node-header node-header--death">
  <span class="node-header__icon">${skullSVG}</span>
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
  <div class="node-hint" style="font-size: 0.8em; color: #888; margin-top: 8px; text-align: center;"></div>
</div>
`;

export function registerDeathNode(editor) {
  registerNodeType('death', {
    html: html,
    inputs: 1, // 'check_stat'
    outputs: 0,
  });

  if (editor && editor.on) {
    editor.on('nodeCreated', (id) => {
      const node = editor.getNodeFromId(id);
      if (node.name === 'death') {
        node.data.condition = node.data.condition || 'LessThanEqual';
        node.data.threshold = node.data.threshold !== undefined ? node.data.threshold : 0;
        editor.updateNodeDataFromId(id, node.data);
      }
    });

    // Default wiring hint
    editor.on('connectionCreated', (info) => {
      // info: { output_id, input_id, output_class, input_class }
      if (info.input_class === 'input_1') {
        const inputNode = editor.getNodeFromId(info.input_id);
        if (inputNode.name === 'death') {
          const outputNode = editor.getNodeFromId(info.output_id);
          if (outputNode.name === 'stat') {
            const domNode = document.getElementById(`node-${info.input_id}`);
            if (domNode) {
              const hintElement = domNode.querySelector('.node-hint');
              if (hintElement) {
                const operator = inputNode.data.condition === 'LessThanEqual' ? '≤' : '≥';
                hintElement.textContent = `Dies when ${outputNode.data.label || 'Stat'} ${operator} ${inputNode.data.threshold}`;
              }
            }
          }
        }
      }
    });
  }
}
