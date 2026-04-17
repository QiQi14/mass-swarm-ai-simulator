// ═══════════════════════════════════════════════════════════════
// ENGINE SELECTOR — Auto-detect or manually choose engine backend
// ═══════════════════════════════════════════════════════════════

import { EngineMode } from './engine-interface.js';
import wsEngine from './ws-engine.js';
import wasmEngine from './wasm-engine.js';

/** Currently active engine instance */
let activeEngine = null;

/**
 * Get the currently active engine.
 * @returns {import('./engine-interface.js').SimEngine|null}
 */
export function getEngine() {
    return activeEngine;
}

/**
 * Initialize the engine with the given mode.
 *
 * @param {string} mode - 'ws', 'wasm', or 'auto'
 *   - 'ws':   Connect to native Rust binary via WebSocket
 *   - 'wasm': Load prebuilt WASM module from /wasm/
 *   - 'auto': Try WASM first, fallback to WebSocket
 * @returns {Promise<import('./engine-interface.js').SimEngine>}
 */
export async function initEngine(mode = 'auto') {
    // Disconnect any existing engine
    if (activeEngine) {
        activeEngine.disconnect();
        activeEngine = null;
    }

    if (mode === 'wasm') {
        await wasmEngine.connect();
        activeEngine = wasmEngine;
    } else if (mode === 'ws') {
        await wsEngine.connect();
        activeEngine = wsEngine;
    } else {
        // Auto: try WASM first, fallback to WS
        try {
            // Quick check: does the WASM file exist?
            const probe = await fetch('/wasm/micro_core.js', { method: 'HEAD' });
            if (probe.ok) {
                await wasmEngine.connect();
                activeEngine = wasmEngine;
                console.log('[Engine] Auto-selected: WASM');
            } else {
                throw new Error('WASM module not found');
            }
        } catch {
            console.log('[Engine] WASM not available, falling back to WebSocket');
            await wsEngine.connect();
            activeEngine = wsEngine;
        }
    }

    return activeEngine;
}

/**
 * Send a command to the active engine.
 * @param {string} cmd
 * @param {object} payload
 */
export function sendEngineCommand(cmd, payload) {
    if (activeEngine) {
        activeEngine.sendCommand(cmd, payload);
    } else {
        console.warn('[Engine] No active engine. Call initEngine() first.');
    }
}

/**
 * Get the current engine mode.
 * @returns {'ws'|'wasm'|null}
 */
export function getEngineMode() {
    return activeEngine?.type ?? null;
}

export { EngineMode };
