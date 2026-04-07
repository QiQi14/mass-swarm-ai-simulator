# User Interface & Tooling

Located in `js/ui-panels.js` and `js/controls.js`.

## The DOM Tooling (`ui-panels.js`)

While the canvas renders the simulation, standard HTML/CSS draws the control panels (buttons, sliders, data tables).

### How it works
This file attaches `Event Listeners` to the HTML buttons. 
- **Pause/Play**: Unlocks or locks the ECS tick flow.
- **Wave Spawner**: Commands Rust to drop 500 new entities into a Fibonacci spiral.
- **ML Brain Status**: Parses read-only telemetry coming down the WebSocket to display the current Win Rate or Curriculum Phase of the active training run.

## Input Controls (`controls.js`)

This handles the terrifying math of dragging and manipulating a 2D camera viewport.

### The Viewport Matrix
When you scroll the mouse wheel, the entire 1000x1000 canvas zooms in. When you click and drag, it pans.
To achieve this, `controls.js` tracks an `offsetX`, `offsetY`, and `scale`. 

Before `draw.js` renders anything, it applies a `ctx.setTransform(scale, 0, 0, scale, offsetX, offsetY)`. This tells the graphics card to automatically stretch and move all subsequent draw commands, completely removing the need for us to manually multiply the X/Y coordinates of every single ant by zooming factors.

### The Raycast Problem (Clicking an Entity)
If you zoom in by 200%, pan right by 50px, and click the screen, where did your mouse actually click in the simulation's coordinate space?

`controls.js` computes an inverse translation matrix. It calculates your mouse's physical screen coordinates, subtracts the `offsetX`, and divides by the `scale`. It then sends that converted `World X / World Y` through the WebSocket to the Rust engine, allowing you to accurately drop a nuke right on an enemy's head, regardless of your camera view!
