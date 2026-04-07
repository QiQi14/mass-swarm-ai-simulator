# State Management & Networking

Located in `js/state.js`, `js/websocket.js`, and `js/config.js`.

## WebSockets (`websocket.js`)
This is the artery of the visualizer.

### How it works
1. On initialization, it opens a `ws://` connection to the Rust `micro-core`.
2. It attaches a `.onmessage` listener. 
3. The Rust core streams JSON chunks containing `SyncDelta` payloads (arrays of `[entity_id, x, y, faction_id]`).
4. Instead of deeply parsing complex objects, we loop over the raw arrays and pass them directly into the State Manager.

### Sending Commands (Bidirectional)
The socket is not just listen-only. When a user clicks "Pause" on the dashboard, `websocket.js` sends a command string upstream to the running engine.

## State Container (`state.js`)
We do not use Redux or any complex state managers. `state.js` holds a flat, raw dictionary `entities: Map<ID, {x, y, faction}>`.

### Preventing Memory Leaks
When an entity dies in the Rust core, it sends a removal flag in the Delta Sync. The `state.js` explicitly `delete`s that key. If we skipped this step, over the course of an hour-long simulation, dead entities would pile up in the browser's heap memory until the tab threw an Out-Of-Memory exception.

Because the data is so flat, Javascript's V8 engine can optimize the map access, yielding nanosecond retrieval times when the renderer asks for coordinates.
