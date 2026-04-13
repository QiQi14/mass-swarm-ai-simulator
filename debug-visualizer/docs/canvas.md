# Canvas Rendering Engine

Located in `src/draw/terrain.js`, `src/draw/entities.js`, and `src/draw/effects.js`.

## Dual-Canvas Architecture

Two HTML5 canvases stacked:
1. **Terrain canvas** — static terrain costs, fog-of-war (offscreen pre-rendered)
2. **Entity canvas** — dynamic entities, overlays, effects (redrawn every frame)

## The Core Loop (`main.js`)

Uses `requestAnimationFrame` for GPU-synced rendering at monitor refresh rate (60/120Hz).
Each frame calls `drawEntities()` which orchestrates all rendering passes.

## Batch Rendering (entities.js)

To achieve 60fps with 10,000+ entities, we batch by faction:

1. Clear the entity canvas
2. For each faction: `beginPath()` → loop all entities → `.arc()` → single `fill()`
3. This minimizes GPU state changes (fillStyle switches) — the critical bottleneck

## Observation Channel Overlays (entities.js)

Overlays render BEFORE entities so entities appear on top. When active, entity opacity drops to 30%.

### Ch0/Ch1 — Density Heatmap
- Data: `S.densityHeatmap` (HashMap of faction → float[2500])
- Renders per-cell colored rectangles using faction color with alpha proportional to density
- Grid: 50×50 cells, 20px per cell

### Ch4 — Terrain Cost
- Data: Local terrain grid from WS `set_terrain` commands
- Renders cost tiers: impassable (red), destructible (amber), elevated (orange)

### Ch7 — Threat Density (ECP)
- Data: `S.ecpDensityMaps` (HashMap of faction → float[2500])
- **3-pass glow renderer** (`drawThreatGlow`):
  - **Pass 1 — Outer Halo:** Wide `shadowBlur` purple glow for visibility at distance
  - **Pass 2 — Core Fill:** HSL gradient from cool purple (low density) to hot magenta/white (high)
  - **Pass 3 — Bloom Pulse:** Hot-spot effect on cells in the top 50% of density
- Skips faction 0 (brain) — only renders enemy threat

### ECP vs Density
| | Density (Ch0/Ch1) | ECP (Ch7) |
|---|---|---|
| **Weights** | 1.0 per entity (headcount) | `max(hp × damage_mult, 1.0)` |
| **Out-of-bounds** | Skipped | Clamped to nearest grid edge |
| **Use case** | Where are units? | Where is the threat? |

## Viewport Transform (terrain.js)

The viewport uses `ctx.setTransform(scale, 0, 0, scale, offsetX, offsetY)` to handle pan/zoom.
All world-to-canvas coordinate conversions go through `worldToCanvas(wx, wy)`.

## Offscreen Rendering (terrain.js)

Static layers (terrain costs, fog-of-war) are drawn once to offscreen `OffscreenCanvas` objects and composited onto the main canvas with `drawImage()`. Only redrawn when terrain data changes.
