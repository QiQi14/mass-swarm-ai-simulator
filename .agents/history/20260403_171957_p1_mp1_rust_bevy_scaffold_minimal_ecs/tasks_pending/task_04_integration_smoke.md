# Task 04: Integration Wiring + Smoke Test (REVISION 2)

```yaml
Task_ID: task_04_integration_smoke
Feature: P1-MP1 Rust/Bevy Scaffold + Minimal ECS
Execution_Phase: C (sequential — depends on Task 02 + Task 03)
Model_Tier: standard
```

> [!CAUTION]
> **REVISION 2 — Previous attempt FAILED.** Root cause: `ScheduleRunnerPlugin::run_loop` ticks at ~2-3 FPS on macOS instead of 60 TPS. The fix is to replace it with a **custom runner** using explicit `thread::sleep` for precise timing control. Read the "Previous Failure" section below before coding.

## Previous Failure Analysis

**Symptoms:**
- The simulation ticked at 2-3 FPS instead of 60 TPS
- `cargo run` produced zero tick log output in 8 seconds
- Tests hung indefinitely waiting for 300 ticks

**Root Cause:**
`ScheduleRunnerPlugin::run_loop(Duration)` in headless mode (without `WinitPlugin`) has poor timing behavior on macOS. Without a windowing event loop to pace frames, the plugin's internal loop doesn't yield efficiently, resulting in extremely slow tick rates.

**Fix:**
Replace `MinimalPlugins.set(ScheduleRunnerPlugin::run_loop(...))` with a **custom app runner** that calls `app.update()` in a manual loop with explicit `std::thread::sleep()` for timing.

## Target Files
- `micro-core/src/main.rs` [MODIFY] (rewrite — replace the current broken version)

## Dependencies
- **Task 02** (ECS components must exist and compile)
- **Task 03** (Systems + config must exist and compile)

## Context_Bindings
- context/tech-stack
- context/conventions
- context/architecture
- skills/rust-code-standards

## Strict Instructions

### 1. Rewrite `src/main.rs` with a Custom Runner

Replace the **entire** contents of `main.rs` with the following:

```rust
//! # Entry Point
//!
//! Headless Bevy application with a custom runner for precise 60 TPS timing.
//!
//! ## Ownership
//! - **Task:** task_04_integration_smoke (revision 2)
//! - **Contract:** implementation_plan.md → Task 04
//!
//! ## Depends On
//! - `micro_core::components`
//! - `micro_core::config`
//! - `micro_core::systems`
//!
//! ## Design Note
//! We use a **custom app runner** instead of `ScheduleRunnerPlugin::run_loop`
//! because the latter has poor timing behavior on macOS in headless mode
//! (ticks at ~2-3 FPS instead of 60 TPS). The custom runner uses explicit
//! `thread::sleep()` to guarantee consistent tick rates.

use bevy::prelude::*;
use std::thread;
use std::time::{Duration, Instant};

use micro_core::components::NextEntityId;
use micro_core::config::{SimulationConfig, TickCounter};
use micro_core::systems::{initial_spawn_system, movement_system, tick_counter_system};

/// Maximum ticks before auto-exit in smoke test mode.
/// Set to 0 to disable auto-exit (run forever mode for bridges).
const SMOKE_TEST_MAX_TICKS: u64 = 300; // ~5 seconds at 60 TPS

/// Target ticks per second for the simulation loop.
const TARGET_TPS: f64 = 60.0;

fn main() {
    App::new()
        // DO NOT use MinimalPlugins — it forces ScheduleRunnerPlugin which
        // has broken timing on macOS. Instead, add only what we need.
        .add_plugins(TaskPoolPlugin::default())
        .add_plugins(TypeRegistrationPlugin::default())
        .add_plugins(FrameCountPlugin::default())
        // Resources
        .init_resource::<SimulationConfig>()
        .init_resource::<TickCounter>()
        .init_resource::<NextEntityId>()
        // Startup systems (run once)
        .add_systems(Startup, initial_spawn_system)
        // Per-tick systems (run every frame)
        .add_systems(Update, (
            tick_counter_system,
            movement_system,
            log_system,
        ))
        // Custom runner replaces ScheduleRunnerPlugin
        .set_runner(custom_runner)
        .run();
}

/// Custom application runner that ticks at exactly TARGET_TPS.
///
/// Replaces `ScheduleRunnerPlugin::run_loop` which had timing issues
/// on macOS in headless mode. Uses `thread::sleep` for frame pacing.
fn custom_runner(mut app: App) -> AppExit {
    let frame_duration = Duration::from_secs_f64(1.0 / TARGET_TPS);

    loop {
        let frame_start = Instant::now();

        // Run one ECS tick
        app.update();

        // Check if we should exit (read TickCounter from the world)
        if SMOKE_TEST_MAX_TICKS > 0 {
            if let Some(counter) = app.world().get_resource::<TickCounter>() {
                if counter.tick >= SMOKE_TEST_MAX_TICKS {
                    println!("[Tick {}] Smoke test complete. Exiting.", counter.tick);
                    return AppExit::Success;
                }
            }
        }

        // Sleep to maintain target TPS
        let elapsed = frame_start.elapsed();
        if elapsed < frame_duration {
            thread::sleep(frame_duration - elapsed);
        }
    }
}

/// Logs simulation status every 60 ticks (~1 second).
fn log_system(
    counter: Res<TickCounter>,
    query: Query<&micro_core::components::Position>,
) {
    if counter.tick > 0 && counter.tick % 60 == 0 {
        let entity_count = query.iter().count();
        println!("[Tick {}] Entities alive: {}", counter.tick, entity_count);
    }
}
```

### Key Changes from Revision 1

1. **Removed `MinimalPlugins`** — it bundles `ScheduleRunnerPlugin` which was the root cause of slow ticking.
2. **Added individual plugins** — `TaskPoolPlugin`, `TypeRegistrationPlugin`, and `FrameCountPlugin` are the core plugins Bevy needs without the problematic runner. Check what `MinimalPlugins` expands to in Bevy 0.18 and add the individual plugins it contains MINUS `ScheduleRunnerPlugin`.
3. **`custom_runner` function** — Uses `Instant::now()` + `thread::sleep()` for precise 60 TPS timing. This is the standard pattern for headless Bevy apps.
4. **Exit logic moved to runner** — Instead of an ECS system writing `AppExit` events, the runner reads `TickCounter` directly from the world and returns `AppExit::Success`. This is more reliable for headless exit.
5. **Removed `smoke_test_exit_system`** — Exit is now handled in the custom runner, avoiding the `EventWriter<AppExit>` / `MessageWriter<AppExit>` API ambiguity.

### 2. IMPORTANT: Verify Bevy 0.18 MinimalPlugins Composition

Before coding, you MUST check what plugins `MinimalPlugins` contains in Bevy 0.18. Run:

```bash
cd micro-core && grep -r "MinimalPlugins" $(cargo metadata --format-version 1 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['workspace_root'])")/../.cargo/registry/src/*/bevy-0.18*/crates/bevy_internal/src/lib.rs 2>/dev/null || echo "Check Bevy source or docs.rs for MinimalPlugins definition"
```

Or check [docs.rs/bevy/0.18/bevy/struct.MinimalPlugins.html](https://docs.rs/bevy/0.18/bevy/struct.MinimalPlugins.html).

Add ALL plugins from `MinimalPlugins` EXCEPT `ScheduleRunnerPlugin`. The code above lists `TaskPoolPlugin`, `TypeRegistrationPlugin`, and `FrameCountPlugin` as a best guess — **verify and adjust**.

### 3. Verify the Fix

After updating `main.rs`, run:

```bash
cd micro-core && cargo build
cd micro-core && cargo clippy
cd micro-core && cargo test
cd micro-core && cargo run
```

Expected `cargo run` output (must complete in ~5 seconds):
```
[Tick 60] Entities alive: 100
[Tick 120] Entities alive: 100
[Tick 180] Entities alive: 100
[Tick 240] Entities alive: 100
[Tick 300] Smoke test complete. Exiting.
```

**If it still hangs or ticks slowly**, the `MinimalPlugins` decomposition is wrong. Check which plugins are actually needed and adjust.

## Verification_Strategy

```yaml
Test_Type: integration
Test_Stack: cargo (Rust toolchain)
Acceptance_Criteria:
  - "`cargo build` succeeds with zero errors"
  - "`cargo clippy` — zero warnings"
  - "`cargo test` — all unit tests from Tasks 02 and 03 still pass"
  - "`cargo run` completes in approximately 5 seconds (300 ticks at 60 TPS)"
  - "Log output shows 5 tick checkpoints: Tick 60, 120, 180, 240, 300"
  - "Each checkpoint shows exactly 100 entities alive"
  - "Process exits with code 0"
  - "NO use of ScheduleRunnerPlugin anywhere in the codebase"
Suggested_Test_Commands:
  - "cd micro-core && cargo build 2>&1"
  - "cd micro-core && cargo clippy 2>&1"
  - "cd micro-core && cargo test 2>&1"
  - "cd micro-core && timeout 15 cargo run 2>&1"
Manual_Steps:
  - "Run `cargo run` and time it — should complete in ~5-6 seconds"
  - "Count the tick log lines — should be exactly 5 (at ticks 60, 120, 180, 240, 300)"
  - "Verify 'Smoke test complete. Exiting.' appears as the final line"
```
