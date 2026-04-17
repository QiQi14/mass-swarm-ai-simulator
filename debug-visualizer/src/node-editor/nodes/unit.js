import { registerNodeType } from '../drawflow-setup.js';

const userSVG = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>`;

const html = `
<div class="node-header node-header--unit">
  <span class="node-header__icon">${userSVG}</span>
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
`;

let nextClassId = 0;

export function registerUnitNode(editor) {
  registerNodeType('unit', {
    html: html,
    inputs: 4, // 'from_faction', 'stats', 'combat', 'death'
    outputs: 2, // 'attacker', 'target'
  });

  if (editor && editor.on) {
    editor.on('nodeCreated', (id) => {
      const node = editor.getNodeFromId(id);
      if (node.name === 'unit') {
        node.data.classId = nextClassId++;
        node.data.unitName = node.data.unitName || 'Infantry';
        editor.updateNodeDataFromId(id, node.data);

        // Update DOM since Drawflow initializes span from empty data
        setTimeout(() => {
          const domNode = document.getElementById(`node-${id}`);
          if (domNode) {
            const span = domNode.querySelector('[df-classId]');
            if (span) span.textContent = node.data.classId;
          }
        }, 10);
      }
    });
  }
}
