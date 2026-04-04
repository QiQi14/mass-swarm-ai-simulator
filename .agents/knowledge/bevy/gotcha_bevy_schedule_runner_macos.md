# Lesson: Bevy ScheduleRunnerPlugin Slow on macOS Headless

**Category:** gotcha
**Discovered:** task_04_integration_smoke (2026-04-03)
**Severity:** high — blocks all headless simulation from running at target TPS

## Context
Building a headless Bevy 0.18 simulation using `MinimalPlugins` with `ScheduleRunnerPlugin::run_loop(Duration::from_secs_f64(1.0 / 60.0))` for a 60 TPS fixed-timestep loop.

## Problem
`ScheduleRunnerPlugin::run_loop` ticks at ~2-3 FPS on macOS instead of the expected 60 TPS. Without a windowing event loop (`WinitPlugin`), the plugin's internal loop doesn't yield or sleep efficiently, causing extremely slow tick rates.

Symptoms:
- Zero tick log output for several seconds
- Tests hang indefinitely waiting for tick thresholds
- CPU usage is low (not busy-waiting — it's genuinely slow)

## Correct Approach
Use a **custom app runner** with explicit `thread::sleep()` instead of `ScheduleRunnerPlugin`:

1. Do NOT use `MinimalPlugins` as a bundle — decompose it into individual plugins
2. Add all plugins from `MinimalPlugins` EXCEPT `ScheduleRunnerPlugin`
3. Call `app.set_runner(custom_runner)` with a manual loop

## Example
- ❌ What the executor did:
```rust
App::new()
    .add_plugins(MinimalPlugins.set(
        ScheduleRunnerPlugin::run_loop(Duration::from_secs_f64(1.0 / 60.0))
    ))
    .run();
```

- ✅ What it should be:
```rust
App::new()
    .add_plugins(TaskPoolPlugin::default())
    .add_plugins(TypeRegistrationPlugin::default())
    .add_plugins(FrameCountPlugin::default())
    .set_runner(custom_runner)
    .run();

fn custom_runner(mut app: App) -> AppExit {
    let frame_duration = Duration::from_secs_f64(1.0 / 60.0);
    loop {
        let start = Instant::now();
        app.update();
        let elapsed = start.elapsed();
        if elapsed < frame_duration {
            thread::sleep(frame_duration - elapsed);
        }
    }
}
```
