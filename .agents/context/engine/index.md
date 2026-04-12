# Engine Overview

This directory contains the context files for the Rust Micro-Core and the underlying simulation engine logic.

## Fast Scan Registry

- **`architecture.md`**: Core high-level system architecture, decoupled design, app shell routing, and multi-node setup.
- **`combat.md`**: Entity model, combat logic, interactions, damage distribution, stats, mitigation, buffs, and entity removal.
- **`navigation.md`**: Movement physics (Boids 2.0 — 3-vector blending), tactical sensor system (10 Hz sharded), unit type registry, engagement range hold, macro directives, and spatial grid.
- **`terrain.md`**: Terrain cells, pheromone/repellent zones, fog of war, and ECP (Effective Combat Power) density visualization.
- **`protocol-zmq.md`**: ZMQ socket structures, JSON directives handling, Rust-to-Python messaging models.
- **`protocol-state.md`**: End-of-Match flags, state payload vectorization, Curriculum configuration loading via ZeroMQ.
