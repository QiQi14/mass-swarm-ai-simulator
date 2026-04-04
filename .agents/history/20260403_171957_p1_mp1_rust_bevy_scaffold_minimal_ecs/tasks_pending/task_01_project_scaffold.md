# Task 01: Project Scaffold

```yaml
Task_ID: task_01_project_scaffold
Feature: P1-MP1 Rust/Bevy Scaffold + Minimal ECS
Execution_Phase: A (first — no dependencies)
Model_Tier: basic
```

## Target Files
- `micro-core/Cargo.toml` [NEW]
- `micro-core/src/main.rs` [NEW] (stub only — Task 04 wires the full app)
- `micro-core/src/components/mod.rs` [NEW] (empty module)
- `micro-core/src/systems/mod.rs` [NEW] (empty module)
- `micro-core/src/lib.rs` [NEW] (crate root for cdylib — re-exports modules)

## Dependencies
None — this is the first task.

## Context_Bindings
- context/tech-stack
- context/conventions
- skills/rust-code-standards

## Strict Instructions

### 1. Create the `micro-core/` directory structure

```
micro-core/
├── Cargo.toml
└── src/
    ├── main.rs
    ├── lib.rs
    ├── components/
    │   └── mod.rs
    └── systems/
        └── mod.rs
```

### 2. Write `Cargo.toml`

```toml
[package]
name = "micro-core"
version = "0.1.0"
edition = "2024"

[lib]
crate-type = ["cdylib", "rlib"]

[dependencies]
bevy = { version = "0.18", default-features = false, features = ["bevy_app", "bevy_ecs"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
rand = "0.9"
```

> **CRITICAL:** Use `edition = "2024"`. Use `default-features = false` for Bevy.
> The `cdylib` crate type enables future C-ABI export. The `rlib` crate type allows `cargo test` to work.

### 3. Write `src/lib.rs`

```rust
pub mod components;
pub mod systems;
```

This is the crate root for the library target. It re-exports the module tree.

### 4. Write `src/main.rs`

Create a minimal Bevy application that compiles and runs:

```rust
use bevy::app::ScheduleRunnerPlugin;
use bevy::prelude::*;
use std::time::Duration;

fn main() {
    App::new()
        .add_plugins(
            MinimalPlugins.set(
                ScheduleRunnerPlugin::run_loop(Duration::from_secs_f64(1.0 / 60.0))
            ),
        )
        .run();
}
```

> This app has no systems yet — it just proves Bevy headless runs at 60 TPS.
> Task 04 will update this file to wire in all components and systems.

### 5. Write `src/components/mod.rs`

```rust
// ECS components — populated by Task 02
```

Empty file with a comment. Task 02 will add module declarations and re-exports.

### 6. Write `src/systems/mod.rs`

```rust
// ECS systems — populated by Task 03
```

Empty file with a comment. Task 03 will add module declarations and re-exports.

## Verification_Strategy

```yaml
Test_Type: unit
Test_Stack: cargo (Rust toolchain)
Acceptance_Criteria:
  - "`cd micro-core && cargo build` succeeds with zero errors"
  - "`cd micro-core && cargo clippy` produces zero warnings"
  - "`cd micro-core && cargo run` starts and runs (process starts without crash — can be killed manually)"
  - "Directory structure matches the layout above exactly"
  - "Cargo.toml dependencies match pinned versions from context/tech-stack.md"
Suggested_Test_Commands:
  - "cd micro-core && cargo build 2>&1"
  - "cd micro-core && cargo clippy 2>&1"
  - "cd micro-core && timeout 3 cargo run || true"
```
