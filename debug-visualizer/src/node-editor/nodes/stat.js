import { registerNodeType } from '../drawflow-setup.js';

const barChartSVG = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>`;

const html = `
<div class="node-header node-header--stat">
  <span class="node-header__icon">${barChartSVG}</span>
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
`;

export function registerStatNode(editor) {
  registerNodeType('stat', {
    html: html,
    inputs: 0,
    outputs: 1, // 'value'
  });

  if (editor && editor.on) {
    editor.on('nodeCreated', (id) => {
      const node = editor.getNodeFromId(id);
      if (node.name === 'stat') {
        node.data.label = node.data.label || 'HP';
        node.data.statIndex = node.data.statIndex || 0; // The actual index is assigned by compiler logic, defaults to 0
        node.data.initialValue = node.data.initialValue !== undefined ? node.data.initialValue : 100;
        editor.updateNodeDataFromId(id, node.data);

        setTimeout(() => {
          const domNode = document.getElementById(`node-${id}`);
          if (domNode) {
            const span = domNode.querySelector('[df-statIndex]');
            if (span) span.textContent = node.data.statIndex;
          }
        }, 10);
      }
    });

    // Handle initial value slider/input display updates if we were using a slider (though it's a number input we just use df-sync)
  }
}
