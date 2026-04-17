import * as S from '../../state.js';
import { sendCommand, showToast } from '../../websocket.js';
import { getCanvasEntities, drawBackground } from '../../draw/index.js';
import { GRID_W, GRID_H } from '../../config.js';

/**
 * Build and mount the terrain paint overlay card.
 * @param {HTMLElement} container - the bottom toolbar area
 */
export function mountTerrainOverlay(container) {
    const popover = document.createElement('div');
    popover.className = 'playground-overlay-popover';
    popover.id = 'terrain-overlay-popover';
    
    popover.innerHTML = `
        <div class="overlay-card" style="width: 280px;">
            <div class="overlay-card__header">
                <div class="overlay-card__header-icon">🖌️</div>
                <div>Terrain Paint</div>
            </div>
            <div class="overlay-card__body">
                <button class="playground-node-btn" id="overlay-paint-toggle" style="width: 100%; justify-content: center; margin-bottom: 8px;">
                    Enable Paint Mode
                </button>
                
                <div id="overlay-brush-tools" style="display: none; flex-direction: column;">
                    <div style="font-family: var(--font-display); font-size: 10px; color: var(--text-tertiary); text-transform: uppercase;">Brush Type</div>
                    <div class="terrain-brush-row">
                        <button class="brush-btn-compact active" data-brush="wall">Wall</button>
                        <button class="brush-btn-compact" data-brush="mud">Mud</button>
                        <button class="brush-btn-compact" data-brush="pushable">Push</button>
                    </div>
                    <div class="terrain-brush-row">
                        <button class="brush-btn-compact" data-brush="clear" style="color: var(--accent-warning);">Clear Cell</button>
                    </div>
                    
                    <button class="playground-node-btn" id="overlay-terrain-clear" style="width: 100%; justify-content: center; margin-top: 12px; border-color: rgba(239, 71, 111, 0.4); color: var(--status-disconnected);">
                        Clear ALL Terrain
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(popover);

    const toggleBtn = popover.querySelector('#overlay-paint-toggle');
    const brushTools = popover.querySelector('#overlay-brush-tools');
    
    // Toggle Button Event
    const containerToggleBtn = document.createElement('button');
    containerToggleBtn.className = 'playground-node-btn';
    containerToggleBtn.innerHTML = `Terrain 🖌`;
    containerToggleBtn.onclick = () => {
        const isActive = popover.classList.contains('active');
        if (isActive) {
            popover.classList.remove('active');
            containerToggleBtn.classList.remove('playground-node-btn--active');
            if (S.paintMode) togglePaintMode();
        } else {
            // Close other popovers softly (ideal logic to manage state externally, simplified here)
            document.querySelectorAll('.playground-overlay-popover').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.playground-node-btn').forEach(b => b.classList.remove('playground-node-btn--active'));
            
            popover.classList.add('active');
            containerToggleBtn.classList.add('playground-node-btn--active');
        }
    };
    container.appendChild(containerToggleBtn);

    function togglePaintMode() {
        const wasPaint = S.paintMode;
        
        S.setSpawnMode(false); 
        S.setZoneMode(false); 
        S.setSplitMode(false); 
        S.setPaintMode(false);
        
        const canvasBg = document.getElementById('canvas-bg');
        const canvasEntities = getCanvasEntities();
        
        if (canvasBg) canvasBg.classList.remove('paint-mode');
        if (canvasEntities) canvasEntities.classList.remove('paint-mode');
        
        S.setPaintMode(!wasPaint);
        toggleBtn.classList.toggle('playground-node-btn--active', S.paintMode);
        toggleBtn.textContent = S.paintMode ? 'Disable Paint Mode' : 'Enable Paint Mode';
        brushTools.style.display = S.paintMode ? 'flex' : 'none';
        
        if (canvasBg) canvasBg.classList.toggle('paint-mode', S.paintMode);
        if (canvasEntities) canvasEntities.classList.toggle('paint-mode', S.paintMode);
        
        if (S.paintMode) showToast('Paint mode ON', 'info');
    }

    toggleBtn.onclick = () => togglePaintMode();

    const brushBtns = popover.querySelectorAll('.brush-btn-compact');
    brushBtns.forEach(btn => {
        btn.onclick = () => {
            brushBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            S.setActiveBrush(btn.dataset.brush);
        };
    });

    popover.querySelector('#overlay-terrain-clear').onclick = () => {
        sendCommand("clear_terrain", {});
        for (let i = 0; i < S.terrainLocal.length; i++) S.terrainLocal[i] = 100;
        drawBackground();
        showToast('Terrain cleared', 'info');
    };
}
