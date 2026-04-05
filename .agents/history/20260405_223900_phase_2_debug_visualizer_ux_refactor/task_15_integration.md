# Task 15 — Integration: Resource Registration + System Gating + Smoke Test

## Metadata
- **Task_ID:** task_15_integration
- **Execution_Phase:** Phase 4 — Final Integration (sequential, depends on ALL)
- **Model_Tier:** advanced
- **Dependencies:**
  - Task 09 (TerrainGrid)
  - Task 10 (FactionVisibility, VisionRadius)
  - Task 11 (Flow Field + Movement terrain integration)
  - Task 12 (Visibility system + IPC)
  - Task 13 (WS Commands)
  - Task 14 (Visualizer UI)
- **Context_Bindings:**
  - `.agents/skills/rust-code-standards/SKILL.md`
  - `implementation_plan.md` → Feature 4: State Management + all feature sections

## Target Files
- `micro-core/src/main.rs` — **MODIFY** (resource registration, system scheduling, state gating)

## Contract: SimState Gating + Resource Wiring

### Resource Registration
All new resources must be registered in `main.rs` App builder:

```rust
// TerrainGrid (Task 09) — matches flow field dimensions
let cell_size = 20.0;
let grid_w = (1000.0 / cell_size).ceil() as u32;  // 50
let grid_h = (1000.0 / cell_size).ceil() as u32;  // 50
app.insert_resource(TerrainGrid::new(grid_w, grid_h, cell_size));

// FactionVisibility (Task 10)
app.insert_resource(FactionVisibility::new(grid_w, grid_h, cell_size));

// ActiveFogFaction (Task 12)
app.insert_resource(ActiveFogFaction(None));
```

VisionRadius is a Component — no resource registration needed, but it MUST be added to all entity spawn bundles (`wave_spawn_system`, `ws_command spawn_wave`, etc).

### System Scheduling with SimState Gating

| System | Schedule | run_if |
|--------|----------|--------|
| `ws_command_system` | Update | Always (no gate) |
| `ws_sync_system` | Update | Always (no gate) |
| `visibility_update_system` | Update | Always (no gate) |
| `flow_field_update_system` | Update | Always (no gate) |
| `movement_system` | Update | `in_state(SimState::Running)` |
| `interaction_system` | Update | `in_state(SimState::Running)` |
| `removal_system` | Update | `in_state(SimState::Running)` |
| `wave_spawn_system` | Update | `in_state(SimState::Running)` |

### Visualizer starts Paused
The app should initialize with `SimState::Setup` (or equivalent paused state) so the user can design terrain and place units before pressing Play.

## Strict Instructions

### 1. Modify `micro-core/src/main.rs`

**a. Add imports:**
```rust
use crate::terrain::TerrainGrid;
use crate::visibility::FactionVisibility;
// ActiveFogFaction from wherever Task 12 defined it
```

**b. Register resources** as described above.

**c. Add `visibility_update_system` to the system schedule** (always runs).

**d. Gate physics systems** with `run_if(in_state(SimState::Running))`:
- `movement_system`
- `interaction_system`
- `removal_system`
- `wave_spawn_system`

**e. Ensure ws_command, ws_sync, flow_field_update, visibility_update run WITHOUT state gates** (must work while paused for terrain painting and fog preview).

**f. Add `VisionRadius::default()` to ALL entity spawn bundles** — check `wave_spawn_system` and any initial entity spawning in `main.rs`.

### 2. Build + Test

After modifications:
```bash
cd micro-core && cargo build    # Must compile
cd micro-core && cargo test     # All tests pass
./dev.sh --smoke                # 300-tick smoke test clean exit
```

## Verification Strategy

**Test_Type:** integration
**Test_Stack:** `cargo test` + `./dev.sh --smoke` + browser

**Acceptance Criteria:**
1. `cargo build` succeeds with no errors
2. `cargo test` — all tests pass (including new terrain, visibility, flow field tests)
3. `./dev.sh --smoke` — 300 ticks, clean shutdown
4. `./dev.sh` + browser at `http://127.0.0.1:3000`:
   - Paint terrain while paused → terrain visible in browser
   - Spawn units while paused → entities appear
   - Press Play → entities move, respecting terrain (wall-sliding, speed reduction)
   - Toggle fog → fog overlay renders correctly
   - Save scenario → download JSON
   - Load scenario → state restored
5. `cargo build --no-default-features` — production build compiles without telemetry

**Commands:**
```bash
cd micro-core && cargo build
cd micro-core && cargo test
cd micro-core && cargo build --no-default-features
./dev.sh --smoke
./dev.sh  # Manual browser testing
```
