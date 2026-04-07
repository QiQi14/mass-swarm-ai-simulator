# Task A5: Remove Stat Fallback with Warning Log

**Task_ID:** task_a5_remove_stat_fallback
**Execution_Phase:** 1
**Model_Tier:** basic

## Target_Files
- `micro-core/src/bridges/zmq_bridge/reset.rs`
- `micro-core/src/bridges/zmq_protocol/payloads.rs`

## Dependencies
- None

## Context_Bindings
- context/architecture
- context/conventions
- skills/rust-code-standards

## Strict_Instructions

### Step 1: Remove stat fallback in `reset.rs`

Replace lines 130-135 in `reset.rs`:

**BEFORE:**
```rust
// Build stat defaults from spawn config or use fallback HP=100
let stat_defaults: Vec<(usize, f32)> = if spawn.stats.is_empty() {
    vec![(0, 100.0)]
} else {
    spawn.stats.iter().map(|e| (e.index, e.value)).collect()
};
```

**AFTER:**
```rust
// Build stat defaults from spawn config — adapter MUST provide explicit values
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

### Step 2: Update doc comment in `payloads.rs`

In `payloads.rs`, update the doc comment on the `stats` field of `SpawnConfig`:

**BEFORE:**
```rust
/// Optional per-spawn stat overrides. Each entry is {index, value}.
/// If absent, defaults to [(0, 100.0)] (HP=100).
```

**AFTER:**
```rust
/// Per-spawn stat values. Each entry is {index, value}.
/// If absent or empty, entities spawn with all-zero StatBlock.
/// The adapter (game profile) should always provide explicit stat values.
```

### Step 3: Verify

```bash
cd micro-core && cargo test bridges && cargo clippy
```

## Verification_Strategy
  Test_Type: unit
  Acceptance_Criteria:
    - "Empty spawn.stats produces StatBlock::default() (all zeros), not (0, 100.0)"
    - "Warning is printed to stdout when stats are empty"
    - "cargo test passes with zero failures"
    - "cargo clippy passes with zero warnings"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test bridges"
