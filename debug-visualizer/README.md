# Debug Visualizer

Real-time visual window into the `micro-core` simulation engine, built with the **Tactical Command Center** design language.

## Architecture

Vite-powered ES module application. No React/Vue — raw Canvas2D rendering achieves 60fps with 10,000+ entities.

```
debug-visualizer/
├── index.html              # Entry point
├── vite.config.js          # Build config
├── package.json
├── src/
│   ├── main.js             # App shell, mode router (Training/Playground)
│   ├── config.js           # Constants, faction registry, grid dimensions
│   ├── state.js            # Flat state container (entity Map, toggles, telemetry)
│   ├── websocket.js        # WS connection, SyncDelta handler
│   ├── styles/
│   │   ├── tokens.css      # Design system variables (colors, spacing, fonts)
│   │   ├── reset.css       # CSS reset + base typography
│   │   ├── layout.css      # App shell grid, sidebar, bottom-sheet mobile
│   │   └── panels.css      # Panel components, accordions, inspector
│   ├── draw/
│   │   ├── terrain.js      # Offscreen terrain canvas, viewport transforms
│   │   ├── entities.js     # Entity batch rendering, observation channel overlays
│   │   └── effects.js      # Health bars, death animations, selection highlights
│   ├── controls/
│   │   ├── init.js         # Global event listeners (keyboard, resize)
│   │   └── split.js        # Canvas pan/zoom, entity click-select
│   └── panels/
│       ├── registry.js     # Panel auto-registration system
│       ├── training/       # Training mode panels (telemetry, inspector, layers)
│       └── playground/     # Playground mode panels (spawn, terrain, zones)
└── docs/
    ├── state_and_network.md
    ├── canvas.md
    └── user_interface.md
```

## Running

```bash
# Development (hot-reload)
cd debug-visualizer && npm run dev

# Production build
cd debug-visualizer && npm run build
```

The visualizer connects to `ws://localhost:8080` (the micro-core's WebSocket server).

## Observation Channel Overlays

Toggle via the **Viewport Layers** panel in the sidebar:

| Channel | Data Source | Visualization | Color |
|---------|-----------|---------------|-------|
| Ch0 — Ally Density | `density_heatmap[0]` | Heatmap | Green |
| Ch1 — Enemy Density | `density_heatmap[1+]` | Heatmap | Red |
| Ch4 — Terrain Cost | `terrainLocal` grid | Cost tiers | Red/Amber/Orange |
| Ch7 — Threat (ECP) | `ecp_density_maps[1+]` | 3-pass glow (halo → core → bloom) | Purple/Magenta |

When any overlay is active, entity opacity drops to 30% so the heatmap dominates visually.

## Design System

The **Tactical Command Center** aesthetic uses:
- Dark surfaces with noise texture
- Electric cyan (`#00d4ff`) accent color
- Geist font family
- Glassmorphism panels with backdrop blur

See `src/styles/tokens.css` for the full variable set.
