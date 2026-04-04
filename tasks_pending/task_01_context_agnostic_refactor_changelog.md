# Changelog: task_01_context_agnostic_refactor

## Touched Files
- `micro-core/src/components/faction.rs` [NEW]
- `micro-core/src/components/stat_block.rs` [NEW]
- `micro-core/src/components/team.rs` [DELETE]
- `micro-core/src/components/mod.rs` [MODIFY]
- `micro-core/src/systems/spawning.rs` [MODIFY]
- `micro-core/src/systems/ws_sync.rs` [MODIFY]
- `micro-core/src/systems/ws_command.rs` [MODIFY]
- `micro-core/src/bridges/ws_protocol.rs` [MODIFY]
- `micro-core/src/bridges/zmq_protocol.rs` [MODIFY]
- `micro-core/src/bridges/zmq_bridge/systems.rs` [MODIFY]
- `debug-visualizer/visualizer.js` [MODIFY]

## Contract Fulfillment
- FactionId component implementation follows Contract 1. Serde, Eq, defaults, tests working.
- StatBlock array-based component implementation follows Contract 2 with MAX_STATS = 8.
- ws_sync_system and ws_command_system migrated from Team to FactionId and StatBlock logic. Tests updated.
- ZMQ Protocol updated to report per-faction dynamically aggregated statistics (counts and avg stats) via hashmaps, mapping string tags away.
- Debug Visualizer updated with Adapter config to dynamically map factions to strings/colors and render via faction_id efficiently.

## Deviations / Notes / Gaps
- **Gap Reported:** `cargo clippy -- -D warnings` throws the following error on an out-of-scope file:
  `src/config.rs:46:1: error: this impl can be derived`. 
  `micro-core/src/config.rs` is NOT in `Target_Files` list, so according to Rule 1 I am reporting this gap and leaving the file unmodified. This prevents the clippy run from being perfectly clean, but all in-scope modifications strictly abide by the rules.
- **Note:** In `ws_command.rs`, a `clippy::too_many_arguments` was suppressed with `#[allow(clippy::too_many_arguments)]` on `ws_command_system` as dictated by the conventions knowledge.
