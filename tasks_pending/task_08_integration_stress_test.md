---
Task_ID: task_08_integration_stress_test
Execution_Phase: Phase 4 (Sequential — Final)
Model_Tier: advanced
Target_Files:
  - micro-core/src/main.rs
  - micro-core/src/systems/mod.rs
  - micro-core/src/config.rs
Dependencies:
  - task_01_context_agnostic_refactor
  - task_02_spatial_hash_grid
  - task_03_flow_field_registry
  - task_04_rule_resources
  - task_05_interaction_removal_systems
  - task_06_flow_field_movement_spawning
  - task_07_ipc_visualizer_upgrades
Context_Bindings:
  - context/conventions
  - context/architecture
  - context/tech-stack
  - context/ipc-protocol
  - skills/rust-code-standards
---

# STRICT INSTRUCTIONS

Wire all Phase 2 systems and resources into the Bevy app. Add CLI args. Run 10K entity stress test.

**Read `implementation_plan.md` Contracts 7 and 9 for system ordering and config fields.**

## 1. Update `micro-core/src/config.rs` [MODIFY]

Add the following fields to `SimulationConfig`:

```rust
pub flow_field_cell_size: f32,       // default: 20.0
pub flow_field_update_interval: u64, // default: 30
pub wave_spawn_interval: u64,        // default: 300
pub wave_spawn_count: u32,           // default: 50
pub wave_spawn_faction: u32,         // default: 0
pub wave_spawn_stat_defaults: Vec<(usize, f32)>, // default: vec![(0, 1.0)]
```

Update the `Default` impl to include these with the specified defaults.

## 2. Update `micro-core/src/systems/mod.rs` [MODIFY]

Add module declarations and re-exports for all new systems:
```rust
pub mod interaction;
pub mod removal;
pub mod flow_field_update;
```

Re-export public system functions:
```rust
pub use interaction::interaction_system;
pub use removal::removal_system;
pub use flow_field_update::flow_field_update_system;
```

Also re-export `wave_spawn_system` from spawning if not already exported.

## 3. Update `micro-core/src/main.rs` [MODIFY]

### 3a. Insert New Resources
```rust
use micro_core::spatial::SpatialHashGrid;
use micro_core::pathfinding::FlowFieldRegistry;
use micro_core::rules::{
    InteractionRuleSet, RemovalRuleSet, NavigationRuleSet,
    FactionBehaviorMode, RemovalEvents,
};
```

Insert resources into the Bevy app:
```rust
.insert_resource(SpatialHashGrid::new(config.flow_field_cell_size))
.insert_resource(FlowFieldRegistry::default())
.insert_resource(InteractionRuleSet::default())
.insert_resource(RemovalRuleSet::default())
.insert_resource(NavigationRuleSet::default())
.insert_resource(FactionBehaviorMode::default())
.insert_resource(RemovalEvents::default())
```

### 3b. Register Systems with Ordering

Systems must be ordered to ensure data flows correctly within each tick:

```
update_spatial_grid_system        (runs ALWAYS, before all sim systems)
  → interaction_system            (after spatial grid, gated by SimState::Running + pause/step)
  → removal_system                (after interaction)
  → ws_sync_system                (after removal — picks up removed IDs)
flow_field_update_system          (periodic, gated by SimState::Running + pause/step)
wave_spawn_system                 (periodic, gated by SimState::Running + pause/step)
movement_system                   (gated by SimState::Running + pause/step)
```

Use Bevy's `.before()` / `.after()` ordering constraints and the existing `run_if` conditions from Phase 1 (pause/step gating).

### 3c. CLI Arguments

Add `--entity-count <N>` argument using `std::env::args()`:
- If present, override `config.initial_entity_count` with the parsed value.
- Used for stress testing: `cargo run -- --entity-count 10000 --smoke-test`.

### 3d. Stress Test Verification

Run the full simulation with 10,000 entities:
```bash
cargo run -- --entity-count 10000 --smoke-test
```

Verify:
- Simulation starts with 10,000 entities.
- 60 TPS is sustained for at least 600 ticks (10 seconds).
- No panics or errors.
- Log average tick time each second (should be < 16.6ms).

## 4. Final Verification Checklist

Before marking done:
- [ ] `cargo build` succeeds with zero warnings.
- [ ] `cargo clippy -- -D warnings` is clean.
- [ ] `cargo test` passes ALL tests (existing + new from all tasks).
- [ ] `cargo run -- --entity-count 10000 --smoke-test` completes successfully.
- [ ] Open Debug Visualizer while running — entities navigate, interact, die, respawn.

---

# Verification_Strategy
Test_Type: integration + manual_steps
Test_Stack: cargo build + cargo run
Acceptance_Criteria:
  - "cargo build succeeds with zero warnings"
  - "cargo clippy -- -D warnings is clean"
  - "cargo test passes all tests (existing + new)"
  - "10K entities sustain 60 TPS for 10+ seconds"
  - "Entities navigate via flow field visible in Debug Visualizer"
  - "Interaction causes stat[0] to decrease (health bars turning red)"
  - "Entities removed when stat[0] reaches 0 (visible in visualizer)"
  - "Wave spawning adds entities periodically at map edges"
Suggested_Test_Commands:
  - "cd micro-core && cargo build"
  - "cd micro-core && cargo clippy -- -D warnings"
  - "cd micro-core && cargo test"
  - "cd micro-core && cargo run -- --entity-count 10000 --smoke-test"
Manual_Steps:
  - "Run micro-core with default config, open debug-visualizer"
  - "Observe swarm entities navigating toward defenders"
  - "Observe health bars decreasing during proximity interaction"
  - "Observe dead entities disappearing"
  - "Observe wave spawning at map edges every 5 seconds"
  - "Toggle faction 1 (Defender) to 'Brain' mode — verify they start following flow fields"
  - "Toggle faction 0 (Swarm) to 'Static' — verify they revert to random drift"
