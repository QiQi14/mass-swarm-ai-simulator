// ═══════════════════════════════════════════════════════════════
// ENGINE INTERFACE — Abstract simulation backend contract
// ═══════════════════════════════════════════════════════════════

/**
 * @typedef {Object} SimEngine
 * @property {'ws'|'wasm'} type - Backend type
 * @property {() => Promise<void>} connect - Initialize/connect the engine
 * @property {() => void} disconnect - Shutdown the engine
 * @property {(cmd: string, payload: object) => void} sendCommand - Send a command
 * @property {() => boolean} isConnected - Check connection state
 * @property {() => string} statusLabel - Human-readable status
 */

/**
 * Possible engine modes.
 * @enum {string}
 */
export const EngineMode = {
    /** Connect to native Rust binary via WebSocket */
    WS: 'ws',
    /** Run prebuilt WASM module in-browser */
    WASM: 'wasm',
};
