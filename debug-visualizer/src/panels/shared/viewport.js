import * as S from '../../state.js';

export default {
    id: 'viewport',
    title: 'Viewport Layers',
    icon: '👁️',
    modes: ['training', 'playground'],
    defaultExpanded: false,
    render(body) {
        body.innerHTML = `
            <div class="layer-group">
                <div class="layer-group-title">Grid Overlays</div>
                <div class="form-group">
                    <label class="toggle-control"><input type="checkbox" id="toggle-grid" checked> <span class="control-indicator"></span><span class="control-label">Coordinate Grid</span></label>
                    <label class="toggle-control"><input type="checkbox" id="toggle-spatial"> <span class="control-indicator"></span><span class="control-label">Spatial Hash Grid</span></label>
                    <label class="toggle-control"><input type="checkbox" id="toggle-bounds" checked> <span class="control-indicator"></span><span class="control-label">Arena Bounds</span></label>
                </div>
            </div>

            <div class="layer-group">
                <div class="layer-group-title">Entity Overlays</div>
                <div class="form-group">
                    <label class="toggle-control"><input type="checkbox" id="toggle-vel"> <span class="control-indicator"></span><span class="control-label">Velocity Vectors</span></label>
                    <label class="toggle-control"><input type="checkbox" id="toggle-flow"> <span class="control-indicator"></span><span class="control-label">Flow Field Arrows</span></label>
                    <label class="toggle-control"><input type="checkbox" id="toggle-overrides"> <span class="control-indicator"></span><span class="control-label">Override Markers</span></label>
                </div>
            </div>

            <div class="layer-group">
                <div class="layer-group-title">🟦 Force Picture (ch0-3)</div>
                <div class="form-group">
                    <label class="toggle-control"><input type="checkbox" id="toggle-ch0"> <span class="control-indicator"></span><span class="control-label">Ch0 — Friendly Count</span></label>
                    <label class="toggle-control"><input type="checkbox" id="toggle-ch1"> <span class="control-indicator"></span><span class="control-label">Ch1 — Enemy Count</span></label>
                    <label class="toggle-control"><input type="checkbox" id="toggle-ch2"> <span class="control-indicator"></span><span class="control-label">Ch2 — Friendly ECP</span></label>
                    <label class="toggle-control"><input type="checkbox" id="toggle-ch3"> <span class="control-indicator"></span><span class="control-label">Ch3 — Enemy ECP</span></label>
                </div>
            </div>

            <div class="layer-group">
                <div class="layer-group-title">🟩 Environment (ch4-5)</div>
                <div class="form-group">
                    <label class="toggle-control"><input type="checkbox" id="toggle-ch4"> <span class="control-indicator"></span><span class="control-label">Ch4 — Terrain Cost</span></label>
                    <label class="toggle-control"><input type="checkbox" id="toggle-ch5"> <span class="control-indicator"></span><span class="control-label">Ch5 — Fog Awareness</span></label>
                </div>
            </div>

            <div class="layer-group">
                <div class="layer-group-title">🟨 Tactical (ch6-7)</div>
                <div class="form-group">
                    <label class="toggle-control disabled"><input type="checkbox" id="toggle-ch6" disabled> <span class="control-indicator"></span><span class="control-label">Ch6 — Interactable Terrain <small>(future)</small></span></label>
                    <label class="toggle-control disabled"><input type="checkbox" id="toggle-ch7" disabled> <span class="control-indicator"></span><span class="control-label">Ch7 — System Objective <small>(future)</small></span></label>
                </div>
            </div>

            <div class="layer-group">
                <div class="layer-group-title">Zone & Modifier Layers</div>
                <div class="form-group">
                    <label class="toggle-control"><input type="checkbox" id="toggle-zones" checked> <span class="control-indicator"></span><span class="control-label">Zone Modifiers</span></label>
                </div>
            </div>
            
            <hr class="panel-divider">
            <div class="layer-group-title">Fog of War</div>
            <div id="fog-toggles-container" class="form-group"></div>
        `;

        // Grid overlays
        body.querySelector('#toggle-grid').onchange = (e) => S.setShowGrid(e.target.checked);
        body.querySelector('#toggle-spatial').onchange = (e) => S.setShowSpatialGrid(e.target.checked);
        body.querySelector('#toggle-bounds').onchange = (e) => S.setShowArenaBounds(e.target.checked);
        
        // Entity overlays
        body.querySelector('#toggle-vel').onchange = (e) => S.setShowVelocity(e.target.checked);
        body.querySelector('#toggle-flow').onchange = (e) => S.setShowFlowField(e.target.checked);
        body.querySelector('#toggle-overrides').onchange = (e) => S.setShowOverrideMarkers(e.target.checked);
        
        // Force Picture channels
        body.querySelector('#toggle-ch0').onchange = (e) => S.setShowDensityHeatmap(e.target.checked);
        body.querySelector('#toggle-ch1').onchange = (e) => S.setShowEnemyDensity(e.target.checked);
        body.querySelector('#toggle-ch2').onchange = (e) => S.setShowFriendlyEcp(e.target.checked);
        body.querySelector('#toggle-ch3').onchange = (e) => S.setShowThreatDensity(e.target.checked);
        
        // Environment channels
        body.querySelector('#toggle-ch4').onchange = (e) => S.setShowTerrainCost(e.target.checked);
        body.querySelector('#toggle-ch5').onchange = (e) => S.setShowFogAwareness(e.target.checked);
        
        // Zones
        body.querySelector('#toggle-zones').onchange = (e) => S.setShowZoneModifiers(e.target.checked);
    }
};
