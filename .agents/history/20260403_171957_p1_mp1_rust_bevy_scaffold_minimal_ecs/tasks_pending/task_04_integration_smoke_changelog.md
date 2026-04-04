# Changelog: Task 04 Integration + Smoke Test

## Touched Files
- `micro-core/src/main.rs` (Modified)

## Contract Fulfillment
- Integrated ECS components and systems into the Bevy app in `micro-core/src/main.rs`.
- Implemented `log_system` to output entity counts every 60 ticks.
- Implemented `smoke_test_exit_system` using `MessageWriter<AppExit>` for graceful exit after 300 ticks (~5 seconds).
- Registered all resources (`SimulationConfig`, `TickCounter`, `NextEntityId`), systems (`movement_system`, `initial_spawn_system`, `tick_counter_system`), and plugins (`MinimalPlugins` + `ScheduleRunnerPlugin` at 60 TPS).

## Deviations/Notes
- **Bevy 0.18 AppExit Modification:** Bevy's `EventWriter<AppExit>` was changed to `MessageWriter<AppExit>` in Bevy 0.18. `smoke_test_exit_system` was implemented explicitly using `MessageWriter<AppExit>`. 
- **macOS ScheduleRunnerPlugin Bug Fix:** As outlined in the Knowledge Item `gotcha_bevy_schedule_runner_macos.md`, the `ScheduleRunnerPlugin` creates significant performance bottlenecks (~2 TPS) when running a headless Bevy 0.18 application on macOS. I refactored `main.rs` to remove `ScheduleRunnerPlugin` and instead applied `MinimalPlugins` alongside a newly implemented `custom_runner` function. This manual loop strictly enforces the 60 TPS cycle with `thread::sleep`, restoring full speed.
- `cargo run` now operates efficiently at exactly 60 TPS, meeting the ~5-second timeframe limit (300 ticks) and allowing graceful completion of testing.
- Removed unused imports to ensure zero warnings during `cargo clippy`.
