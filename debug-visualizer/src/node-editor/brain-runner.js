import * as S from '../state.js';

/**
 * ONNX Runtime is loaded lazily only when the user actually uploads a model.
 * This avoids a hard dependency on onnxruntime-web at build time.
 */
let ort = null;

async function loadOrt() {
    if (ort) return ort;
    try {
        ort = await import(/* @vite-ignore */ 'https://cdn.jsdelivr.net/npm/onnxruntime-web@1.17.3/dist/ort.min.mjs');
        return ort;
    } catch (e) {
        console.error('[Brain] Failed to load ONNX Runtime from CDN:', e);
        return null;
    }
}

/**
 * Start brain inference for a faction.
 * 
 * Modes:
 *   - 'zmq'  → The brain runs server-side via Python ZMQ (no client ONNX needed)
 *   - 'onnx' → User uploads an ONNX model file, inference runs in-browser
 *   - 'rust' → The Rust core handles all logic (no brain needed)
 * 
 * @param {Object} config - { factionId, modelPath, modelBlob, decisionInterval, mode }
 * @param {(cmd: string, params: object) => boolean} sendCommand
 * @returns {{ stop: () => void }}
 */
export function startBrainRunner(config, sendCommand) {
    // ZMQ mode: brain runs server-side via Python, nothing to do client-side
    if (config.mode === 'zmq') {
        console.log('[Brain] ZMQ mode — brain runs server-side via Python macro-brain.');
        return { stop: () => {} };
    }

    // Rust-only mode: no brain needed, factions follow node-graph rules
    if (config.mode === 'rust' || !config.mode) {
        return { stop: () => {} };
    }

    // ONNX mode: require either a Blob (from file upload) or a URL path
    const modelSource = config.modelBlob || config.modelPath;
    if (!modelSource) {
        console.warn('[Brain] ONNX mode selected but no model provided. Upload an .onnx file in the General node.');
        return { stop: () => {} };
    }

    let session = null;
    let running = true;
    let intervalId = null;

    (async () => {
        const ortModule = await loadOrt();
        if (!ortModule || !running) return;

        try {
            // If modelSource is a Blob (File upload), read as ArrayBuffer
            let sessionInput;
            if (modelSource instanceof Blob) {
                const buffer = await modelSource.arrayBuffer();
                sessionInput = new Uint8Array(buffer);
            } else {
                sessionInput = modelSource; // URL string
            }

            session = await ortModule.InferenceSession.create(sessionInput);
            if (!running) return;

            console.log(`[Brain] ONNX model loaded for faction ${config.factionId}`);

            const msPerTick = 1000 / 60;
            const intervalMs = (config.decisionInterval || 30) * msPerTick;

            intervalId = setInterval(async () => {
                if (S.isPaused || !S.mlBrainStatus || !running || !session) return;

                const obsData = S.mlBrainStatus.observation;
                if (!obsData || !obsData.length) return;

                try {
                    const floatArray = obsData instanceof Float32Array ? obsData : new Float32Array(obsData);
                    const tensor = new ortModule.Tensor('float32', floatArray, [1, floatArray.length]);
                    const inputName = session.inputNames[0];
                    const feeds = { [inputName]: tensor };

                    const results = await session.run(feeds);
                    const outputName = session.outputNames[0];
                    const actionTensor = results[outputName];

                    if (actionTensor && actionTensor.data) {
                        const actionData = actionTensor.data;
                        const actionType = Math.round(actionData[0]);
                        const params1 = Math.round(actionData[1] || 0);
                        const params2 = Math.round(actionData[2] || 0);

                        const directive = decodeAction(config.factionId, actionType, params1, params2);
                        if (directive) {
                            sendCommand('inject_directive', { directive });
                        }
                    }
                } catch (e) {
                    console.error('[Brain] Inference error:', e);
                }
            }, intervalMs);

        } catch (e) {
            console.error('[Brain] Failed to load ONNX model:', e);
        }
    })();

    return {
        stop: () => {
            running = false;
            if (intervalId) clearInterval(intervalId);
            session = null;
        }
    };
}

/**
 * Decode MultiDiscrete([8, 2500, 4]) action tensor into MacroDirective JSON.
 * Maps action indices to the v3 action space.
 */
function decodeAction(factionId, actionType, spatialCoord, modifier) {
    // Decode spatial coordinate: flat_coord -> (x, y) on 50x50 grid
    const gridW = 50;
    const gx = spatialCoord % gridW;
    const gy = Math.floor(spatialCoord / gridW);
    // Scale to world coords (assuming cell_size = map_size / grid_w)
    const cellSize = 20; // default: 1000/50

    switch (actionType) {
        case 0: // Hold
            return { Hold: { faction_id: factionId } };

        case 1: // AttackCoord
            return {
                UpdateNavigation: {
                    follower_faction: factionId,
                    target: { type: 'Waypoint', x: gx * cellSize, y: gy * cellSize }
                }
            };

        case 2: // ZoneModifier
            return {
                SetZoneModifier: {
                    faction_id: factionId,
                    x: gx * cellSize,
                    y: gy * cellSize,
                    radius: 100,
                    cost_modifier: modifier === 0 ? -50 : 200
                }
            };

        case 3: // SplitToCoord
            return {
                SplitFaction: {
                    source_faction: factionId,
                    class_filter: modifier === 0 ? null : modifier - 1,
                    percentage: 0.3,
                    epicenter: [gx * cellSize, gy * cellSize]
                }
            };

        case 4: // MergeBack
            return {
                MergeFaction: {
                    source_faction: factionId + 100,
                    target_faction: factionId
                }
            };

        case 5: // SetPlaystyle
            return {
                SetTacticalOverride: {
                    faction: factionId,
                    behavior: modifier === 3 ? null : { type: ['Aggressive', 'Passive', 'Kite'][modifier] || 'Aggressive' }
                }
            };

        case 6: // ActivateSkill
            return {
                ActivateBuff: {
                    faction_id: factionId,
                    buff_index: modifier
                }
            };

        case 7: // Retreat
            return {
                Retreat: {
                    faction_id: factionId,
                    retreat_x: gx * cellSize,
                    retreat_y: gy * cellSize
                }
            };

        default:
            return null;
    }
}
