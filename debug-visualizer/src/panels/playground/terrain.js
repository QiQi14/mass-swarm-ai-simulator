import * as S from '../../state.js';
import { sendCommand, showToast } from '../../websocket.js';
import { getCanvasEntities, drawBackground } from '../../draw/index.js';
import { GRID_W, GRID_H } from '../../config.js';

export default {
    id: 'terrain',
    title: 'Terrain Editor',
    icon: '⛰️',
    modes: ['playground'],
    defaultExpanded: false,
    render(body) {
        body.innerHTML = `
            <div style="margin-bottom: var(--space-md);">
                <button class="btn outline" id="terrain-paint-toggle" style="width: 100%;">
                    Enable Paint Mode
                </button>
            </div>

            <div id="terrain-brush-tools" style="display: none; flex-direction: column; gap: var(--space-md); margin-bottom: var(--space-md);">
                <div class="stat-card" style="padding: var(--space-md);">
                    <div class="stat-label" style="margin-bottom: var(--space-sm);">Brush Type</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-sm);">
                        <button class="btn outline brush-btn active" data-brush="wall">Wall</button>
                        <button class="btn outline brush-btn" data-brush="mud">Mud</button>
                        <button class="btn outline brush-btn" data-brush="pushable">Pushable</button>
                        <button class="btn outline brush-btn" data-brush="clear">Clear</button>
                    </div>
                </div>
            </div>

            <div class="stat-card" style="padding: var(--space-md);">
                <div class="stat-label" style="margin-bottom: var(--space-sm);">Scenario Actions</div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-sm);">
                    <button class="btn outline" id="terrain-save-btn">Save</button>
                    <button class="btn outline" id="terrain-load-btn">Load</button>
                    <button class="btn error" id="terrain-clear-btn" style="grid-column: 1 / -1;">Clear Terrain</button>
                </div>
                <input type="file" id="terrain-file-input" accept=".json" style="display: none;">
            </div>
        `;

        const toggleBtn = body.querySelector('#terrain-paint-toggle');
        const brushTools = body.querySelector('#terrain-brush-tools');
        
        toggleBtn.onclick = () => {
             const wasPaint = S.paintMode;
             S.setSpawnMode(false); S.setZoneMode(false); S.setSplitMode(false); S.setPaintMode(false);
             
             const canvasBg = document.getElementById('canvas-bg');
             const canvasEntities = getCanvasEntities();
             canvasBg.classList.remove('paint-mode');
             canvasEntities.classList.remove('paint-mode');
             
             S.setPaintMode(!wasPaint);
             toggleBtn.classList.toggle('active', S.paintMode);
             toggleBtn.textContent = S.paintMode ? 'Disable Paint Mode' : 'Enable Paint Mode';
             brushTools.style.display = S.paintMode ? 'flex' : 'none';
             canvasBg.classList.toggle('paint-mode', S.paintMode);
             canvasEntities.classList.toggle('paint-mode', S.paintMode);
             if (S.paintMode) showToast('Paint mode ON', 'info');
        };

        const brushBtns = body.querySelectorAll('.brush-btn');
        brushBtns.forEach(btn => {
            btn.onclick = () => {
                brushBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                S.setActiveBrush(btn.dataset.brush);
            };
        });

        body.querySelector('#terrain-clear-btn').onclick = () => {
            sendCommand("clear_terrain", {});
            for (let i = 0; i < S.terrainLocal.length; i++) S.terrainLocal[i] = 100;
            drawBackground();
            showToast('Terrain cleared', 'info');
        };

        body.querySelector('#terrain-save-btn').onclick = () => {
            sendCommand("save_scenario", {});
            showToast('Save command sent to server', 'info');
        };

        const fileInput = body.querySelector('#terrain-file-input');
        body.querySelector('#terrain-load-btn').onclick = () => fileInput.click();
        
        fileInput.onchange = (e) => {
            const file = e.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = (ev) => {
                try {
                    const data = JSON.parse(ev.target.result);
                    sendCommand("load_scenario", data);
                    if (data.terrain) {
                        if (data.terrain.hard_costs && data.terrain.soft_costs) {
                            const cellCount = GRID_W * GRID_H;
                            for (let i = 0; i < cellCount; i++) {
                                S.terrainLocal[i * 2] = data.terrain.hard_costs[i] || 100;
                                S.terrainLocal[i * 2 + 1] = data.terrain.soft_costs[i] || 100;
                            }
                        }
                        drawBackground();
                    }
                    showToast('Scenario loaded', 'success');
                } catch (err) {
                    console.error("Failed to parse scenario file", err);
                    showToast('Failed to load scenario', 'error');
                }
            };
            reader.readAsText(file);
            fileInput.value = ''; // Reset to allow loading the same file again
        };
    }
};
