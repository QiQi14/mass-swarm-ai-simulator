import * as S from '../../state.js';
import { sendCommand } from '../../websocket.js';

export default {
    id: 'sim-controls',
    title: 'Simulation Controls',
    icon: '⏯',
    modes: ['playground'],
    defaultExpanded: true,
    render(body) {
        body.innerHTML = `
            <div style="display: flex; gap: var(--space-sm); align-items: center;">
                <button class="btn primary" id="sim-play-pause-btn" style="flex: 1;">
                     ${S.isPaused ? '▶ Play' : '⏸ Pause'}
                </button>
                <button class="btn outline" id="sim-step-btn">
                     Step ▾
                </button>
                <input type="number" id="sim-step-count" class="input" value="1" min="1" style="width: 60px;">
            </div>
        `;

        const playPauseBtn = body.querySelector('#sim-play-pause-btn');
        playPauseBtn.onclick = () => {
            S.setIsPaused(!S.isPaused);
            playPauseBtn.innerHTML = S.isPaused ? '▶ Play' : '⏸ Pause';
            sendCommand('toggle_sim');
        };

        const stepBtn = body.querySelector('#sim-step-btn');
        const stepCount = body.querySelector('#sim-step-count');
        stepBtn.onclick = () => {
            const count = parseInt(stepCount.value, 10);
            if (!isNaN(count) && count > 0) {
                sendCommand('step', { count });
            }
        };
    },
    update() {
        // Option to update play/pause button state if server syncs it, 
        // but for now local S.isPaused is the source of truth.
        const playPauseBtn = document.getElementById('sim-play-pause-btn');
        if (playPauseBtn) {
            playPauseBtn.innerHTML = S.isPaused ? '▶ Play' : '⏸ Pause';
        }
    }
};
