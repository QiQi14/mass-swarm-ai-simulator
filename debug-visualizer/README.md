# Debug Visualizer

Welcome to the **Debug Visualizer**! While the `micro-core` crunching physics in headless rust, and the `macro-brain` is training neural nets in python, resolving a bug using only print statements is torturous. 

This module provides a real-time visual window into the engine.

## What is the Debug Visualizer?
It is a lightweight, zero-dependency, vanilla HTML5/JavaScript web application. No React, no Vue, no bloated build step. You open `index.html` in your browser, and it connects directly to the `micro-core`'s WebSocket port.

## Why Vanilla JavaScript?
Performance over ergonomics. 
When the `micro-core` is simulating 10,000 entities, it broadcasts coordinates 60 times a second. If you pump 600,000 state mutations per second into React's Virtual DOM, the browser will crash immediately.

By using raw JavaScript arrays and drawing directly onto an HTML `<canvas>`, we achieve buttery smooth 60fps rendering of massive swarms on standard hardware.

## Directory Map (Deep Dive)
To avoid an overwhelmingly large document, technical details are split into specific domains:

1. [**State & Network (`state.js`, `websocket.js`)**](docs/state_and_network.md) - How we connect to the Rust core and securely manage incoming delta updates without memory leaks.
2. [**Canvas Rendering (`draw.js`, `main.js`)**](docs/canvas.md) - How we clear and re-render thousands of entities on an HTML5 canvas linearly every frame.
3. [**User Interface & Tooling (`ui-panels.js`, `controls.js`)**](docs/user_interface.md) - How the dashboard tools (painting modifiers, selecting units, pausing) interact with the core simulation.
