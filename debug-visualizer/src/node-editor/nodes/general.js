import { registerNodeType } from '../drawflow-setup.js';

const brainSVG = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z"/><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z"/></svg>`;

/**
 * Stores uploaded ONNX model Blobs keyed by node ID.
 * The compiler reads from here when mode === 'onnx'.
 */
export const uploadedModels = new Map();

export function registerGeneralNode(editor) {
  const getGeneralHTML = `
    <div class="node-header node-header--general">
      <span class="node-header__icon">${brainSVG}</span>
      <span>GENERAL</span>
    </div>
    <div class="node-body">
      <div class="node-field">
        <label>Brain Mode</label>
        <div class="node-toggle-group">
          <button class="node-toggle node-toggle--active" data-mode="rust">🔧 Rust Only</button>
          <button class="node-toggle" data-mode="onnx">🧠 ONNX Upload</button>
          <button class="node-toggle" data-mode="zmq">🐍 Python ZMQ</button>
        </div>
      </div>
      <div class="node-field node-field--onnx" style="display:none;">
        <label>Upload Model (.onnx)</label>
        <input type="file" accept=".onnx" class="node-file-input">
        <span class="node-file-name">No file selected</span>
      </div>
      <div class="node-field">
        <label>Decision Interval</label>
        <input type="range" df-decisionInterval min="10" max="60" value="30" class="node-slider">
        <span class="node-slider-value" data-df="decisionInterval">30 ticks</span>
      </div>
      <div class="node-status" id="brain-status">
        <span class="status-dot-inline status-dot-inline--wait"></span>
        <span class="node-mono-value">IDLE</span>
      </div>
    </div>
  `;

  registerNodeType('general', {
    html: getGeneralHTML,
    inputs: 1, // Connects from Faction's general port
    outputs: 0,
  });

  editor.on('nodeCreated', (id) => {
    try {
      const node = editor.getNodeFromId(id);
      if (node.name === 'general') {
        const currentData = { ...node.data };
        if (currentData.decisionInterval === undefined) currentData.decisionInterval = 30;
        if (currentData.mode === undefined) currentData.mode = 'rust';
        editor.updateNodeDataFromId(id, currentData);
        syncGeneralNodeUI(id, currentData);
        bindGeneralNodeEvents(id, editor);
      }
    } catch (e) { }
  });

  editor.on('nodeDataChanged', (id) => {
    try {
      const node = editor.getNodeFromId(id);
      if (node.name === 'general') {
        syncGeneralNodeUI(id, node.data);
      }
    } catch (e) { }
  });

  editor.on('connectionCreated', (connection) => {
    try {
      const outputNode = editor.getNodeFromId(connection.output_id);
      const inputNode = editor.getNodeFromId(connection.input_id);

      if (outputNode.name === 'faction' && inputNode.name === 'general' && connection.output_class === 'general') {
        const factionElem = document.getElementById(`node-${connection.output_id}`);
        if (factionElem) {
          factionElem.classList.add('faction-has-brain');
        }
      }
    } catch (e) { }
  });

  editor.on('connectionRemoved', (connection) => {
    try {
      const outputNode = editor.getNodeFromId(connection.output_id);
      const inputNode = editor.getNodeFromId(connection.input_id);

      if (outputNode.name === 'faction' && inputNode.name === 'general' && connection.output_class === 'general') {
        const factionElem = document.getElementById(`node-${connection.output_id}`);
        if (factionElem) {
          factionElem.classList.remove('faction-has-brain');
        }
      }
    } catch (e) { }
  });

  // Cleanup uploaded models when node is removed
  editor.on('nodeRemoved', (id) => {
    uploadedModels.delete(String(id));
  });

  function syncGeneralNodeUI(id, data) {
    const nodeElement = document.getElementById(`node-${id}`);
    if (!nodeElement) return;

    const intervalSpan = nodeElement.querySelector('.node-slider-value[data-df="decisionInterval"]');
    if (intervalSpan) intervalSpan.textContent = `${data.decisionInterval} ticks`;

    // Toggle active state
    const toggles = nodeElement.querySelectorAll('button[data-mode]');
    toggles.forEach(t => {
      if (t.dataset.mode === data.mode) {
        t.classList.add('node-toggle--active');
      } else {
        t.classList.remove('node-toggle--active');
      }
    });

    // Show/hide ONNX upload field
    const onnxField = nodeElement.querySelector('.node-field--onnx');
    if (onnxField) {
      onnxField.style.display = data.mode === 'onnx' ? '' : 'none';
    }

    // Update status
    const statusDot = nodeElement.querySelector('.status-dot-inline');
    const statusText = nodeElement.querySelector('.node-mono-value');
    if (statusDot && statusText) {
      if (data.mode === 'rust') {
        statusDot.className = 'status-dot-inline status-dot-inline--ok';
        statusText.textContent = 'RUST CORE';
      } else if (data.mode === 'zmq') {
        statusDot.className = 'status-dot-inline status-dot-inline--wait';
        statusText.textContent = 'ZMQ READY';
      } else if (data.mode === 'onnx') {
        const hasModel = uploadedModels.has(String(id));
        statusDot.className = hasModel
          ? 'status-dot-inline status-dot-inline--ok'
          : 'status-dot-inline status-dot-inline--warn';
        statusText.textContent = hasModel ? 'MODEL LOADED' : 'AWAITING UPLOAD';
      }
    }
  }

  function bindGeneralNodeEvents(id, editor) {
    const nodeElement = document.getElementById(`node-${id}`);
    if (!nodeElement) return;

    // Mode toggle buttons
    const toggles = nodeElement.querySelectorAll('button[data-mode]');
    toggles.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const val = e.currentTarget.dataset.mode;
        const currentData = { ...editor.getNodeFromId(id).data };
        currentData.mode = val;
        editor.updateNodeDataFromId(id, currentData);
        syncGeneralNodeUI(id, currentData);
      });
    });

    // File upload handler
    const fileInput = nodeElement.querySelector('.node-file-input');
    const fileNameSpan = nodeElement.querySelector('.node-file-name');
    if (fileInput) {
      fileInput.addEventListener('change', (e) => {
        e.stopPropagation();
        const file = e.target.files[0];
        if (file && file.name.endsWith('.onnx')) {
          uploadedModels.set(String(id), file);
          if (fileNameSpan) fileNameSpan.textContent = file.name;
          syncGeneralNodeUI(id, editor.getNodeFromId(id).data);
          console.log(`[Brain] ONNX model staged for node ${id}: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`);
        } else {
          if (fileNameSpan) fileNameSpan.textContent = 'Invalid file — .onnx only';
        }
      });

      // Prevent Drawflow from intercepting click on file input
      fileInput.addEventListener('mousedown', (e) => e.stopPropagation());
    }
  }
}
