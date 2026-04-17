// ═══════════════════════════════════════════════════════════════
// WASM ENGINE — In-browser simulation via prebuilt WebAssembly
// ═══════════════════════════════════════════════════════════════

import * as S from '../state.js';

let wasm = null;
let tickLoop = null;

/** @type {import('./engine-interface.js').SimEngine} */
const wasmEngine = {
    type: 'wasm',
    _connected: false,

    /**
     * Load and initialize the WASM module.
     * Looks for the wasm file at /wasm/micro_core.js (wasm-bindgen output).
     */
    async connect() {
        try {
            // Dynamic import with variable path to prevent Vite from bundling
            // The WASM files live in public/wasm/ and are served as static assets
            const wasmPath = '/wasm/micro_core.js';
            const wasmModule = await import(/* @vite-ignore */ wasmPath);
            await wasmModule.default(); // Initialize the wasm module
            wasm = wasmModule;

            // Initialize the simulation engine (1000x1000 world)
            wasm.wasm_init(1000.0, 1000.0);
            this._connected = true;

            // Start a tick loop — advance simulation each frame
            this._startTickLoop();

            console.log('[WasmEngine] WASM module loaded and simulation initialized');
        } catch (e) {
            console.error('[WasmEngine] Failed to load WASM module:', e);
            throw e;
        }
    },

    disconnect() {
        if (tickLoop) {
            cancelAnimationFrame(tickLoop);
            tickLoop = null;
        }
        this._connected = false;
        wasm = null;
    },

    /**
     * Translate WebSocket-style commands to WASM function calls.
     * This maps the existing command protocol so compiler.js works unchanged.
     */
    sendCommand(cmd, payload) {
        if (!wasm) return;

        switch (cmd) {
            case 'spawn_wave':
                wasm.wasm_spawn(
                    payload.faction_id ?? 0,
                    payload.amount ?? 100,
                    payload.x ?? 500,
                    payload.y ?? 500,
                    payload.spread ?? 100,
                    JSON.stringify(payload.stats?.map(s => s.value) ?? [100.0])
                );
                break;

            case 'set_navigation':
                wasm.wasm_set_navigation(JSON.stringify(payload.rules ?? []));
                break;

            case 'set_interaction':
                wasm.wasm_set_interaction(JSON.stringify(payload.rules ?? []));
                break;

            case 'set_removal':
                wasm.wasm_set_removal(JSON.stringify(payload.rules ?? []));
                break;

            case 'kill_all':
                wasm.wasm_kill_all(payload.faction_id ?? 4294967295);
                break;

            case 'toggle_sim':
                wasm.wasm_toggle_pause();
                break;

            case 'step_sim':
                wasm.wasm_tick(payload.ticks ?? 1);
                break;

            default:
                console.warn(`[WasmEngine] Unhandled command: ${cmd}`);
        }
    },

    isConnected() {
        return this._connected;
    },

    statusLabel() {
        return this._connected ? 'WASM: Running' : 'WASM: Not loaded';
    },

    getEntityCount() {
        return wasm ? wasm.wasm_entity_count() : 0;
    },

    getTick() {
        return wasm ? Number(wasm.wasm_get_tick()) : 0;
    },

    getTps() {
        // WASM ticks at requestAnimationFrame rate
        return 60;
    },

    /**
     * Sync WASM entity data into the shared S.entities Map so the
     * existing render pipeline (drawEntities) works without changes.
     */
    _syncEntitiesToState() {
        if (!wasm) return;

        const buf = wasm.wasm_get_entities();
        const stride = 6;
        const count = buf.length / stride;

        // Clear existing and rebuild
        S.entities.clear();
        for (let i = 0; i < count; i++) {
            const off = i * stride;
            S.entities.set(i, {
                x: buf[off],
                y: buf[off + 1],
                faction_id: buf[off + 2],
                stats: [buf[off + 3]],
                dx: buf[off + 4],
                dy: buf[off + 5],
            });
        }
    },

    /**
     * Internal tick loop — ticks WASM and syncs entities to state each frame.
     */
    _startTickLoop() {
        const loop = () => {
            if (!this._connected) return;
            // Advance sim by 1 tick per frame
            wasm.wasm_tick(1);
            this._syncEntitiesToState();
            tickLoop = requestAnimationFrame(loop);
        };
        tickLoop = requestAnimationFrame(loop);
    },
};

export default wasmEngine;
