import * as S from '../../state.js';
import { sendCommand, showToast } from '../../websocket.js';

/**
 * Build and mount the sim controls overlay card.
 * @param {HTMLElement} container - the bottom toolbar area
 */
export function mountSimControlsOverlay(container) {
    const popover = document.createElement('div');
    popover.className = 'playground-overlay-popover';
    popover.id = 'sim-controls-popover';

    // TPS config map
    const speedMap = {
        '1': 10,
        '2': 20,
        '5': 50,
        '10': 100
    };

    popover.innerHTML = `
        <div class="overlay-card" style="width: 260px;">
            <div class="overlay-card__header">
                <div class="overlay-card__header-icon">⚙️</div>
                <div>Sim Controls</div>
            </div>
            <div class="overlay-card__body">
                <div class="sim-controls-row">
                    <button class="sim-btn-compact sim-btn-compact--play" id="overlay-sim-play" title="Play">▶</button>
                    <button class="sim-btn-compact sim-btn-compact--pause" id="overlay-sim-pause" title="Pause">⏸</button>
                    <button class="sim-btn-compact" id="overlay-sim-step" title="Step">⏭</button>
                </div>
                
                <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 12px; margin-top: 12px;">
                    <div style="font-family: var(--font-display); font-size: 10px; color: var(--text-tertiary); text-transform: uppercase; flex: 1;">Speed</div>
                    <select class="sim-select-compact" id="overlay-sim-speed">
                        <option value="1">1x</option>
                        <option value="2">2x</option>
                        <option value="5">5x</option>
                        <option value="10">10x</option>
                    </select>
                </div>

                <div style="font-family: var(--font-mono); font-size: 10px; color: var(--text-tertiary); text-align: center; margin-bottom: 8px;">
                    Tick: <span id="overlay-tick-display">0</span>
                </div>
                
                <button class="playground-node-btn" id="overlay-sim-reset" style="width: 100%; justify-content: center; border-color: rgba(255, 255, 255, 0.1);">
                    Reset Engine
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(popover);

    // Toggle Button Event
    const containerToggleBtn = document.createElement('button');
    containerToggleBtn.className = 'playground-node-btn';
    containerToggleBtn.innerHTML = `Sim Controls ⏯`;
    containerToggleBtn.onclick = () => {
        const isActive = popover.classList.contains('active');
        if (isActive) {
            popover.classList.remove('active');
            containerToggleBtn.classList.remove('playground-node-btn--active');
        } else {
            document.querySelectorAll('.playground-overlay-popover').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.playground-node-btn').forEach(b => b.classList.remove('playground-node-btn--active'));

            popover.classList.add('active');
            containerToggleBtn.classList.add('playground-node-btn--active');
        }
    };
    container.appendChild(containerToggleBtn);

    // Control logic
    popover.querySelector('#overlay-sim-play').onclick = () => {
        sendCommand("resume_sim", {});
        showToast('Simulation Resumed', 'info');
    };

    popover.querySelector('#overlay-sim-pause').onclick = () => {
        sendCommand("pause_sim", {});
        showToast('Simulation Paused', 'info');
    };

    popover.querySelector('#overlay-sim-step').onclick = () => {
        sendCommand("step_sim", { ticks: 10 });
        showToast('Next Step', 'info');
    };

    popover.querySelector('#overlay-sim-speed').onchange = (e) => {
        const mult = e.target.value;
        const targetTps = speedMap[mult] || 10;
        sendCommand("set_tps", { tps: targetTps });
        showToast(`Speed set to ${mult}x (${targetTps} TPS)`, 'info');
    };

    popover.querySelector('#overlay-sim-reset').onclick = () => {
        sendCommand("reset_sim", {});
        showToast('Engine Reset', 'warn');
    };

    // Update tick display periodically
    setInterval(() => {
        const tickSpan = popover.querySelector('#overlay-tick-display');
        if (tickSpan) {
            tickSpan.textContent = S.globalTick !== undefined ? S.globalTick : 0;
        }
    }, 250);
}
