import { registerNodeType } from '../drawflow-setup.js';

const linkSVG = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>`;

export function registerRelationshipNode(editor) {
  const getRelationshipHTML = `
    <div class="node-header node-header--relationship">
      <span class="node-header__icon">${linkSVG}</span>
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
      <div class="relationship-visual" style="display:flex; justify-content:center; align-items:center; margin-top:10px; height: 24px; background: rgba(0,0,0,0.2); border-radius: 4px;">
      </div>
    </div>
  `;

  registerNodeType('relationship', {
    html: getRelationshipHTML,
    inputs: 2,
    outputs: 0,
  });

  const updateRelationshipVisual = (id) => {
    try {
      const node = editor.getNodeFromId(id);
      if (!node || node.name !== 'relationship') return;
      const nodeEl = document.getElementById(`node-${id}`);
      if (!nodeEl) return;
      const visualContainer = nodeEl.querySelector('.relationship-visual');
      if (!visualContainer) return;

      const getFactionColor = (inputName) => {
        const conns = node.inputs[inputName]?.connections || [];
        if (conns.length > 0) {
          const connectedNode = editor.getNodeFromId(conns[0].node);
          if (connectedNode && connectedNode.name === 'faction' && connectedNode.data.color) {
            return connectedNode.data.color;
          }
        }
        return null;
      };

      const colorA = getFactionColor('input_1'); // Drawflow uses input_1, input_2 by default unless mapped
      const colorB = getFactionColor('input_2');
      const relType = node.data.relationType || 'hostile';

      let icon = '⚔️';
      if (relType === 'neutral') icon = '—';
      if (relType === 'allied') icon = '🤝';

      if (colorA && colorB) {
        visualContainer.innerHTML = `
          <div style="width:12px;height:12px;border-radius:50%;background-color:${colorA}; border: 1px solid rgba(255,255,255,0.5);"></div>
          <div style="margin:0 8px; font-size:12px;">${icon}</div>
          <div style="width:12px;height:12px;border-radius:50%;background-color:${colorB}; border: 1px solid rgba(255,255,255,0.5);"></div>
        `;
      } else {
        visualContainer.innerHTML = `<span style="opacity:0.5;font-size:10px;color:var(--text-secondary)">Needs 2 connections</span>`;
      }
    } catch(e) {
      // Ignore
    }
  };

  editor.on('nodeCreated', (id) => {
    try {
      const node = editor.getNodeFromId(id);
      if (node.name === 'relationship') {
        const currentData = { ...node.data };
        currentData.nodeType = 'relationship';
        if (currentData.relationType === undefined) {
          currentData.relationType = 'hostile';
        }
        editor.updateNodeDataFromId(id, currentData);

        setTimeout(() => {
          const sel = document.getElementById(`node-${id}`)?.querySelector('.node-select');
          if (sel) {
            sel.addEventListener('change', () => {
              editor.updateNodeDataFromId(id, { ...editor.getNodeFromId(id).data, relationType: sel.value });
              updateRelationshipVisual(id);
            });
          }
          updateRelationshipVisual(id);
        }, 50);
      }
    } catch(e) {
      // handle race conditions or missing nodes gracefully
    }
  });

  editor.on('connectionCreated', (conn) => {
    const node = editor.getNodeFromId(conn.input_id);
    if (node && node.name === 'relationship') {
      updateRelationshipVisual(conn.input_id);
    }
  });

  editor.on('connectionRemoved', (conn) => {
    const node = editor.getNodeFromId(conn.input_id);
    if (node && node.name === 'relationship') {
      updateRelationshipVisual(conn.input_id);
    }
  });
}
