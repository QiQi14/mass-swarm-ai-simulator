# Implementation Plan - Task A5: Remove Stat Fallback with Warning Log

This task involves removing the hardcoded stat fallback (HP=100) in the simulation reset logic and replacing it with a warning log and an all-zero StatBlock default. This ensures the simulation remains context-agnostic and that game profiles are responsible for providing explicit stat values.

## Proposed Changes

### micro-core Component

#### [MODIFY] [reset.rs](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/micro-core/src/bridges/zmq_bridge/reset.rs)

Replace the fallback logic for `stat_defaults` when `spawn.stats` is empty.

```rust
// BEFORE:
let stat_defaults: Vec<(usize, f32)> = if spawn.stats.is_empty() {
    vec![(0, 100.0)]
} else {
    spawn.stats.iter().map(|e| (e.index, e.value)).collect()
};

// AFTER:
let stat_defaults: Vec<(usize, f32)> = if spawn.stats.is_empty() {
    println!(
        "[Reset] WARNING: SpawnConfig for faction_{} has empty stats. \
         Entities will spawn with all-zero StatBlock. \
         The adapter (game profile) should provide explicit stat values.",
        spawn.faction_id
    );
    vec![]
} else {
    spawn.stats.iter().map(|e| (e.index, e.value)).collect()
};
```

#### [MODIFY] [payloads.rs](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/micro-core/src/bridges/zmq_protocol/payloads.rs)

Update the doc comment for the `stats` field in `SpawnConfig`.

```rust
// BEFORE:
/// Optional per-spawn stat overrides. Each entry is {index, value}.
/// If absent, defaults to [(0, 100.0)] (HP=100).

// AFTER:
/// Per-spawn stat values. Each entry is {index, value}.
/// If absent or empty, entities spawn with all-zero StatBlock.
/// The adapter (game profile) should always provide explicit stat values.
```

## Verification Plan

### Automated Tests
- Run unit tests for bridges: `cd micro-core && cargo test bridges`
- Run clippy to ensure no regressions: `cargo clippy`

### Manual Verification
- Verify that the warning message appears in stdout if a reset request with empty stats is sent (this would ideally be done during an integration test, but unit tests with manual inspection of output or mock requests will be used).
