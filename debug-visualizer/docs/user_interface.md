# User Interface & Tooling

Located in `src/panels/`, `src/controls/`, and `src/main.js`.

## Dual-Mode Application Shell

The app supports two modes selected via hash routing:
- **`#training`** — Read-only monitoring during RL training sessions
- **`#playground`** — Interactive sandbox for scenario design

### Mode Router (`main.js`)
Reads `window.location.hash` to determine mode. Each mode registers its own panels via the panel registry system. Mode switches preserve WebSocket connection and canvas state.

## Panel System (`panels/registry.js`)

Panels are self-contained ES modules that register via:
```javascript
registerPanel('training', 'telemetry-dashboard', {
    label: 'Telemetry',
    icon: '📊',
    render: (container) => { ... },
    update: (container) => { ... }
});
```

### Training Mode Panels
| Panel | Purpose |
|-------|---------|
| **Telemetry Dashboard** | Episode count, win rate, reward meters, training stage |
| **Faction Telemetry** | Per-faction unit counts, HP, centroids |
| **Entity Inspector** | Click-select entity → anonymous stats with delta indicators |
| **Viewport Layers** | Toggle observation channel overlays (Ch0, Ch1, Ch4, Ch7) |
| **Perf Monitor** | Per-system microsecond timings (spatial, flow, interaction, etc.) |

### Playground Mode Panels
| Panel | Purpose |
|-------|---------|
| **Game Setup** | Configure factions, terrain, rules before starting |
| **Sim Controls** | Pause/resume, step, speed multiplier |
| **Spawn Controls** | Drop entities at coordinates |
| **Terrain Painter** | Paint wall/mud/push terrain cells |
| **Zone Modifiers** | Place pheromone/repellent zones |

## Input Controls (`controls/`)

### Camera Viewport (`split.js`)
- **Scroll wheel:** Zoom in/out (centered on cursor position)
- **Click + drag:** Pan the viewport
- **Click (no drag):** Select entity → populates Entity Inspector
- **Inverse transform:** Screen coordinates are converted to world coordinates via inverse of the viewport matrix

### Entity Selection
Single-click selects the nearest entity within selection radius. The Entity Inspector shows:
- Anonymous stats (S0, S1, S2, ...) with real-time meter bars
- Delta indicators (▲ buff / ▼ debuff) comparing current vs previous tick
- Faction color and ID

> [!NOTE]
> A "pan-after-select" bug was fixed by ensuring mousedown selection does NOT set
> the panning flag. The fix is in `split.js` — mousedown only sets selection state,
> mousemove requires an explicit drag threshold before panning starts.

## Design System

The **Tactical Command Center** aesthetic:
- **Font:** Geist (sans-serif, loaded from Google Fonts)
- **Primary accent:** Electric cyan `#00d4ff`
- **Surfaces:** Dark semi-transparent panels with `backdrop-filter: blur()`
- **Borders:** 1px solid `rgba(255,255,255,0.06)`
- **Animations:** Smooth transitions on hover, 200ms ease

All tokens are in `src/styles/tokens.css`. Panel styling in `src/styles/panels.css`.
