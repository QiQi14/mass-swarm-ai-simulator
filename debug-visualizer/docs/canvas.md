# Canvas Rendering Engine

Located in `js/draw.js` and `js/main.js`.

## The HTML5 Canvas API

We draw everything using the raw `CanvasRenderingContext2D` API. 

## The Core Loop (`main.js`)
Instead of reacting to state changes, we use `requestAnimationFrame`. This is the browser's native game loop.
It runs at the exact refresh rate of your monitor (usually 60Hz or 120Hz).

On every frame, `main.js` calls `drawAll()`.

## Optimizations (`draw.js`)
If you naively loop through 10,000 entities and call `ctx.fillStyle = "red"; ctx.fillRect()`, it is extremely slow due to context switching. Every time you change the paint brush color (`fillStyle`), the GPU stalls and flushes the pipeline.

### Batch Drawing (How we achieve 60fps)
Instead of painting Entity 1 (Red), Entity 2 (Blue), Entity 3 (Red), we **batch render**.

1. The renderer clears the screen: `ctx.clearRect()`.
2. It begins drawing the Red Faction. `ctx.beginPath()`.
3. It iterates through the State Manager, finding *only* Red entities. It adds their coordinates to the current path using `.rect()` or `.arc()`.
4. It calls `ctx.fill()` **once**.
5. It switches the brush to Blue, and repeats.

By drastically minimizing state changes on the Canvas Context, we push the heavy lifting purely to the GPU's rasterizer.

## Fog of War & Terrain Rendering
These are static layers. Rather than redrawing 2,500 grid squares every 16ms, we draw them once to an "Offscreen Canvas" (a hidden canvas in memory), and simply `.drawImage()` that massive pre-rendered block onto the main screen behind the entities. We only recalculate it when the user actively paints new terrain.
