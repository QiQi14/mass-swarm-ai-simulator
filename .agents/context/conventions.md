# Conventions

## Naming

### Rust (Micro-Core)
- **Files:** `snake_case.rs`
- **Modules:** `snake_case` directories with `mod.rs`
- **Structs / Enums:** `PascalCase` (`Position`, `MacroAction`, `SpatialGrid`)
- **Functions:** `snake_case` (`update_spatial_grid`, `calculate_flow_field`)
- **Constants:** `UPPER_SNAKE_CASE` (`DEFAULT_TICK_RATE`, `MAX_ENTITIES`)
- **Components:** PascalCase, derive `Component` (`Health`, `Velocity`, `FlowFieldFollower`)
- **Resources:** PascalCase, derive `Resource` (`SimulationConfig`, `FlowField`)
- **Systems:** `snake_case` functions registered into Bevy schedule (`movement_system`, `combat_system`)

### Python (Macro-Brain)
- **Files:** `snake_case.py`
- **Packages:** `snake_case/` with `__init__.py`
- **Classes:** `PascalCase` (`SwarmEnv`, `MacroBrainModel`)
- **Functions / Methods:** `snake_case` (`vectorize_state`, `compute_reward`)
- **Constants:** `UPPER_SNAKE_CASE` (`OBSERVATION_GRID_SIZE`, `ACTION_SPACE_SIZE`)

### JavaScript (Debug Visualizer)
- **Files:** `camelCase.js` or `kebab-case.js`
- **Functions:** `camelCase` (`drawEntities`, `handleCommand`)
- **Constants:** `UPPER_SNAKE_CASE` (`WS_URL`, `CANVAS_WIDTH`)
- **DOM IDs:** `kebab-case` (`spawn-btn`, `speed-slider`, `entity-count`)

## Code Style

### Rust
- **Edition:** 2024
- **Formatting:** `cargo fmt` (default rustfmt)
- **Linting:** `cargo clippy` — treat warnings as errors in CI
- **Error handling:** Use `Result<T, E>` for fallible operations; `unwrap()` only in tests
- **Exports:** Each module exposes a clean public API via `pub` — no wildcard re-exports
- **Derives:** Always derive `Debug`; derive `Serialize, Deserialize` for any struct crossing IPC

### Python
- **Formatting:** Black (default config)
- **Linting:** Ruff
- **Type Hints:** Required on all public function signatures
- **Docstrings:** Google-style for public functions and classes
- **Imports:** Standard lib → Third-party → Local (separated by blank lines)

### JavaScript
- **Formatting:** Prettier (default config) if using a build step; otherwise manual consistency
- **Comments:** JSDoc for public functions
- **No frameworks** — vanilla JS, no React/Vue/Angular

## Git
- **Branch naming:** `feature/<short-desc>`, `fix/<short-desc>`, `infra/<short-desc>`
- **Commit format:** Conventional Commits — `feat(core): add spatial grid`, `fix(brain): ZMQ timeout handling`
- **Commit scope prefixes:** `core` (Rust), `brain` (Python), `viz` (Web UI), `infra` (build/CI), `docs`

## IPC Conventions
- **Message format:** JSON objects with a `"type"` discriminator field (e.g., `"state_snapshot"`, `"macro_action"`, `"command"`)
- **Entity IDs:** Unsigned 32-bit integers, globally unique within a simulation session
- **Coordinates:** Floating-point `(x, y)`, origin at top-left `(0, 0)`, positive Y goes down
- **Health:** Normalized `0.0` to `1.0`
- **Team values:** `"swarm"` or `"defender"` (lowercase string in JSON)

## Project-Specific Patterns
- **Bevy headless mode:** Always use `MinimalPlugins` + `ScheduleRunnerPlugin` — never `DefaultPlugins`
- **Tick-based simulation:** All game logic operates on discrete ticks (60 TPS), not wall-clock time
- **AI evaluation is decoupled:** Python receives state every N ticks (configurable), not every frame
- **Delta syncing for Web UI:** Broadcast only changed entities (spawned, moved, died), not full state every tick
- **C-ABI readiness:** Core logic functions should be structured to be exposable via `#[no_mangle] pub extern "C"` for future FFI
- **WASM compatibility:** Micro-Core code must avoid APIs that prevent `wasm32-unknown-unknown` compilation (raw file I/O, `std::thread::spawn`, platform-specific syscalls). Use Bevy/Tokio abstractions instead.
- **10K+ entity minimum:** The architecture exists to solve the 10,000+ entity problem. All design decisions (spatial grids, flow fields, delta sync) are justified by this scale target. Do not optimize for 1K — that works without any optimization.
