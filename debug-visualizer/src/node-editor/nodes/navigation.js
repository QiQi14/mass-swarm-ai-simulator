import { registerNodeType } from '../drawflow-setup.js';

const compassSVG = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>`;

export function registerNavigationNode(editor) {
  const getHTML = `
    <div class="node-header node-header--navigation">
      <span class="node-header__icon">${compassSVG}</span>
      <span>NAVIGATE</span>
    </div>
    <div class="node-body">
      <div class="node-hint">Connect follower faction and target</div>
    </div>
  `;

  registerNodeType('navigation', {
    html: getHTML,
    inputs: 3, // follower, target_faction, waypoint
    outputs: 0,
  });

  editor.on('nodeCreated', (id) => {
    try {
      const node = editor.getNodeFromId(id);
      if (node.name === 'navigation') {
        const currentData = { ...node.data };
        currentData.nodeType = 'navigation';
        editor.updateNodeDataFromId(id, currentData);
      }
    } catch (e) {}
  });
}
