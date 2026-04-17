import Drawflow from 'drawflow';
import 'drawflow/dist/drawflow.min.css';

const nodeRegistry = new Map();

/**
 * Initialize a Drawflow editor within the given container.
 * @param {HTMLElement} container
 * @returns {{ editor: Drawflow, destroy: () => void }}
 */
export function createEditor(container) {
    const editor = new Drawflow(container);
    editor.reroute = true;
    editor.reroute_fix_curvature = true;
    editor.force_first_input = false;
    editor.zoom_min = 0.3;
    editor.zoom_max = 2.0;

    editor.start();

    return { 
        editor, 
        destroy: () => {
            container.innerHTML = '';
        } 
    };
}

/**
 * Register all custom node types with the editor.
 * Must be called AFTER all node modules have called registerNodeType().
 * @param {Drawflow} editor
 */
export function registerAllNodes(editor) {
    for (const [typeName, config] of nodeRegistry.entries()) {
        // Vanilla JS mode: register HTML string as a named component
        editor.registerNode(typeName, document.createElement('div'));
    }
}

/**
 * Node registration hook — other node modules call this to self-register.
 */
export function registerNodeType(typeName, { html, inputs, outputs }) {
    nodeRegistry.set(typeName, { html, inputs: inputs || 0, outputs: outputs || 0 });
}

/**
 * Get the HTML template for a registered node type.
 * @param {string} typeName
 * @returns {string} HTML template string
 */
export function getNodeHTML(typeName) {
    const config = nodeRegistry.get(typeName);
    return config ? config.html : `<div>${typeName}</div>`;
}

/**
 * Get the input/output counts for a registered node type.
 * @param {string} typeName
 * @returns {{ inputs: number, outputs: number }}
 */
export function getNodePorts(typeName) {
    const config = nodeRegistry.get(typeName);
    return config ? { inputs: config.inputs, outputs: config.outputs } : { inputs: 1, outputs: 1 };
}
