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
- **Message format:** JSON objects with a `"type"` discriminator field (e.g., `"state_snapshot"`, `"macro_directives"`, `"reset"`)
- **Entity IDs:** Unsigned 32-bit integers, globally unique within a simulation session
- **Faction IDs:** Unsigned 32-bit integers (0 = brain, 1+ = bot factions)
- **Coordinates:** Floating-point `(x, y)`, origin at top-left `(0, 0)`, positive Y = down
- **Stats:** `StatBlock[8]` — raw float values (NOT normalized). Index meaning defined by game profile (index 0 = HP by convention)
- **Full directive/snapshot schemas:** See `ipc-protocol.md`

## File Organization & Module Splitting

> Applies to ALL languages in this project: Rust, Python, JavaScript.

### When to Split

A source file **MUST** be split when it meets **ANY** of:

| Trigger | Threshold |
|---------|-----------|
| Lines (excluding tests) | **> 300 lines** |
| Distinct concerns | **3+ concerns** (e.g., data types + I/O + business logic) |
| Parallel agent collision | Multiple agents need different parts of the same file |

### When NOT to Split

A file **MAY** remain as a single module when:
- It is under 300 lines
- All items are tightly coupled (single class/system + its helpers + its tests)
- Splitting would create modules with only 1-2 items each

### If Not Splitting: Document Why

If a file exceeds 300 lines but you choose NOT to split, add a rationale at the top:

**Rust:**
```rust
//! This module is intentionally kept as a single file because [reason].
```

**Python:**
```python
# NOTE: This module exceeds 300 lines but is not split because [reason].
```

**JavaScript:**
```javascript
// NOTE: This file exceeds 300 lines but is not split because [reason].
```

### Language-Specific Split Patterns

**Rust:** Use submodule directories with `mod.rs` re-exports. See `rust-code-standards` skill → Part 4 for concrete patterns.

**Python:** Use packages (`__init__.py` + focused modules). Example:
```
config/
├── __init__.py         # from .game_profile import GameProfile, ...
├── game_profile.py     # GameProfile class + loader
├── dataclasses.py      # MovementConfigDef, AbilitiesDef, etc.
└── serializers.py      # Payload serialization helpers
```

**JavaScript:** Use ES module files with a barrel `index.js`. Example:
```
visualizer/
├── index.js            // import/export barrel
├── canvas.js           // Canvas rendering logic
├── websocket.js        // WS connection + message handling
├── ui-panels.js        // DOM panel management
└── state.js            // Client-side state tracking
```

### Planning Implications

When the Planner creates a task that will produce a file with 3+ concerns:
1. **Pre-split** — Define the submodule structure in the task brief
2. OR **Document** — Add a note: "Single file acceptable because [reason]"

## Project-Specific Patterns
- **Bevy headless mode:** Always use `MinimalPlugins` + `ScheduleRunnerPlugin` — never `DefaultPlugins`
- **Tick-based simulation:** All game logic operates on discrete ticks (60 TPS), not wall-clock time
- **AI evaluation is decoupled:** Python receives state every N ticks (configurable), not every frame
- **Delta syncing for Web UI:** Broadcast only changed entities (spawned, moved, died), not full state every tick
- **C-ABI readiness:** Core logic functions should be structured to be exposable via `#[no_mangle] pub extern "C"` for future FFI
- **WASM compatibility:** Micro-Core code must avoid APIs that prevent `wasm32-unknown-unknown` compilation (raw file I/O, `std::thread::spawn`, platform-specific syscalls). Use Bevy/Tokio abstractions instead.
- **10K+ entity minimum:** The architecture exists to solve the 10,000+ entity problem. All design decisions (spatial grids, flow fields, delta sync) are justified by this scale target. Do not optimize for 1K — that works without any optimization.

## RL Action Space Design — "The General" Principle

> **The model is a General, not a state machine picker.**
> It must learn to compose atomic primitives into complex tactics — not pick from a menu of pre-baked compound actions.

### Rules for Action Design

1. **Every action MUST be a single, atomic primitive.** One action = one effect on the simulation. Never combine multiple effects into one action index.
2. **Actions MUST be universal.** Each action should be usable in many different tactical contexts, not designed for one specific scenario.
3. **Complex tactics emerge from COMPOSITION.** The model learns multi-step sequences (e.g., Scout → AttackCoord → Retreat) on its own. Never pre-bake a combo.
4. **No action should encode strategy.** "Split group + navigate + set aggro mask" is strategy. "Split group to coordinate" is a primitive. Only primitives belong in the action space.

### Current 8-Action Vocabulary (v3.1)

| Index | Name | Type | Effect |
|-------|------|------|--------|
| 0 | Hold | Non-spatial | Stop movement |
| 1 | AttackCoord | Spatial | Navigate main force to (x,y) |
| 2 | DropPheromone | Spatial | Attract zone at (x,y) |
| 3 | DropRepellent | Spatial | Repel zone at (x,y) |
| 4 | SplitToCoord | Spatial | Split 30% to (x,y) |
| 5 | MergeBack | Non-spatial | Merge first sub-faction back |
| 6 | Retreat | Spatial | Withdraw to (x,y) |
| 7 | Scout | Spatial | Split 10% recon group to (x,y) |

### Anti-Pattern: Compound Actions (DO NOT)

The old `Lure` action violated these rules by combining 4 directives (Split + Navigate + AggroMask×2) into one action index. This made the model a "tactic picker" instead of a "tactician." It was replaced with `Scout` (atomic: split + navigate).

**If you need a new tactic:** Add atomic primitives that enable it, not the tactic itself. Example: if you need "lure patrol away," the model should learn to combine `Scout(patrol_area) → AttackCoord(target) → Retreat(safe_zone)` on its own.

