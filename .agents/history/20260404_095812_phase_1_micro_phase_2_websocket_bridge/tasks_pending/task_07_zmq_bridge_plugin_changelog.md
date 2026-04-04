# Changelog: task_07_zmq_bridge_plugin

## Touched Files
- `micro-core/src/bridges/zmq_bridge.rs` (Created/Implemented)

## Contract Fulfillment
- Implemented `ZmqBridgePlugin` Bevy plugin.
- Added `SimState` enum for non-blocking simulation gating.
- Defined `AiBridgeConfig` and `AiBridgeChannels` resources.
- Implemented `zmq_io_loop` for background tokio operations with timeout and HOLD fallback.
- Added Bevy systems `ai_trigger_system` and `ai_poll_system`.
- Provided 4 unit tests which all pass, matching acceptance criteria.
- Ensured all code conforms to `skills/rust-code-standards` doc structures.

## Deviations/Notes
- `mpsc::Receiver` does not implement `Sync`, so wrapping `mpsc::Receiver<String>` in `std::sync::Mutex` was required within the `AiBridgeChannels` Resource to allow Bevy to use it safely as a `Resource`.
- Replaced `tick.tick % config.send_interval_ticks != 0` with `!tick.tick.is_multiple_of(...)` to adhere to rust/clippy suggestions.
- Fixed `in_state` and `AppExtStates` traits usage to match Bevy state abstraction decoupling layout (`bevy::state::prelude::*`).
- Unit tests `test_ai_trigger_system_fires_on_interval` and `test_ai_trigger_system_skips_non_interval_ticks` required an additional `app.update()` (in one case) to allow Bevy to propagate `NextState` to `State` before validation, and appending `bevy_state::app::StatesPlugin` initialized it correctly without risking visual overhead.
