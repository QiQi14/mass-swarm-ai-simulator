# Task 12: Debug Visualizer Frontend Upgrade (Phase 3)

**Task_ID:** `task_12_visualizer_phase3`
**Execution_Phase:** 1 (after T11 within Phase 1 chain: T02→T11→T12)
**Model_Tier:** `advanced`
**Target_Files:**
  - `debug-visualizer/index.html` (MODIFY)
  - `debug-visualizer/style.css` (MODIFY)
  - `debug-visualizer/visualizer.js` (MODIFY)
**Dependencies:** Task 11 (WS protocol types for JSON parsing)
**Context_Bindings:**
  - `implementation_plan_feature_5.md` → Task 12 section (FULL)

## Strict Instructions

See `implementation_plan_feature_5.md` → **Task 12: Debug Visualizer Frontend Upgrade** for full instructions.

**Summary:**

### New UI Panels (index.html)
1. 🧠 **ML Brain Status** — Python connection, last directive, intervention flag
2. 🧲 **Zone Modifier Tool** — click-to-place with type/radius/intensity/duration controls
3. ✂️ **Faction Splitter** — click epicenter + percentage slider + sub-faction list with merge buttons
4. 🛡️ **Aggro Masks** — interactive matrix (click to toggle combat)
5. **Viewport Layer Toggles** — density heatmap, zone modifiers, engine overrides

### Canvas Rendering (visualizer.js)
1. Zone modifier circles with pulsing glow (blue=attract, red=repel)
2. Sub-faction color palette (hue-shifted from parent, deterministic)
3. Density heatmap overlay (yellow→red heat gradient)
4. EngineOverride flashing diamond markers
5. ML Brain status panel updates
6. Aggro mask matrix (interactive toggle)
7. Interactive canvas modes: zoneMode (radius preview), splitMode (crosshair + tooltip)
8. Dynamic legend updating from active_sub_factions

### CSS
- Zone modifier tool styles, aggro grid styles, ML status styles
- Zone type selector (attract/repel buttons)
- Sub-faction list with merge buttons

## Verification_Strategy
```
Test_Type: manual
Test_Stack: browser visual inspection
Acceptance_Criteria:
  - Zone modifier circles render with correct position, radius, color
  - Density heatmap overlay shows heat gradient
  - Sub-faction entities rendered with distinct colors
  - ML Brain panel shows connection status and last directive
  - Aggro mask matrix is interactive (click to toggle)
  - Zone mode: cursor preview circle + click-to-place
  - Split mode: click-to-set-epicenter + percentage slider
  - Legend updates dynamically with active sub-factions
  - EngineOverride entities have flashing diamond marker
  - All existing visualizer features still work
Manual_Steps:
  - "Open debug-visualizer/index.html, start Rust core"
  - "Verify all 5 new panels render correctly"
  - "Test zone placement mode with attract/repel"
  - "Test faction split with different epicenters"
  - "Toggle viewport layers and verify overlays"
```
