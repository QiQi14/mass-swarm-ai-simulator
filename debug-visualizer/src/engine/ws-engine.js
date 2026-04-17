// ═══════════════════════════════════════════════════════════════
// WS ENGINE — WebSocket backend connecting to native Rust binary
// ═══════════════════════════════════════════════════════════════

import { connectWebSocket, sendCommand as wsSendCommand } from '../websocket.js';
import * as S from '../state.js';

/** @type {import('./engine-interface.js').SimEngine} */
const wsEngine = {
    type: 'ws',
    _connected: false,

    async connect() {
        connectWebSocket();
        this._connected = true;
        console.log('[WsEngine] Connected to native Rust binary via WebSocket');
    },

    disconnect() {
        // WebSocket module handles reconnection internally
        this._connected = false;
    },

    sendCommand(cmd, payload) {
        wsSendCommand(cmd, payload);
    },

    isConnected() {
        return this._connected;
    },

    statusLabel() {
        return this._connected ? 'WS: Connected' : 'WS: Disconnected';
    },

    /**
     * Read entity data from shared state (populated by websocket.js).
     * Returns the S.entities Map directly since WS mode populates it.
     */
    getEntityCount() {
        return S.entities.size;
    },

    getTick() {
        return S.currentTick;
    },

    getTps() {
        return S.tpsCounter;
    },
};

export default wsEngine;
