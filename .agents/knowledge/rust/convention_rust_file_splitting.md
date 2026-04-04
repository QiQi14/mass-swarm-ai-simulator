# Rule: Rust File Size & Module Splitting Convention

**Category:** Convention
**Discovered:** task_07_zmq_bridge_plugin — zmq_bridge.rs grew to 421 lines with 7 distinct concerns
**Severity:** medium

## Context
`zmq_bridge.rs` contains: SimState enum, AiBridgeConfig resource, AiBridgeChannels resource, ZmqBridgePlugin, zmq_io_loop (async background task), build_state_snapshot helper, ai_trigger_system, ai_poll_system, and 4 unit tests — all in a single 421-line file. While functional, this reduces readability and makes parallel agent work harder (larger scope per file = more merge conflicts).

## Strict Directive

### When to Split
A Rust source file SHOULD be split into submodules when it meets ANY of these criteria:
- **> 300 lines** (excluding tests)
- **3+ distinct concerns** (e.g., data types + async I/O + Bevy systems + plugin wiring)
- **Multiple parallel agents** will need to modify different parts of the same file

### When NOT to Split
A file MAY remain as a single module when:
- It is under 300 lines
- All items are tightly coupled (e.g., a single system + its helper + its tests)
- Splitting would create modules with only 1-2 items each

### If Not Splitting: Document Why
If a file exceeds 300 lines but you choose NOT to split, add a rationale comment at the top of the module doc:

```rust
//! # ZMQ Bridge Plugin
//!
//! This module is intentionally kept as a single file because [reason].
//! Consider splitting if it grows beyond [threshold] or gains [new concern].
```

### Recommended Split Pattern for Bridge-type Modules
For bridge modules with multiple concerns, use this submodule pattern:

```
bridges/zmq/
├── mod.rs          // pub use re-exports + ZmqBridgePlugin
├── config.rs       // AiBridgeConfig, AiBridgeChannels, SimState
├── io_loop.rs      // zmq_io_loop async function + FALLBACK_ACTION
└── systems.rs      // ai_trigger_system, ai_poll_system, build_state_snapshot
```

### Planning Implications
When the Planner creates a task brief that will produce a file with 3+ concerns:
1. **Pre-split** — Define the submodule structure in the task brief
2. OR **Document the decision** — Add a note in the brief: "Single file acceptable because [reason]"

## Example
- ❌ Anti-pattern: Creating a 400+ line file without acknowledging the size or documenting why splitting was deferred.
- ✅ Best Practice: Either split into focused submodules, OR add a module-level comment explaining why it's kept together (e.g., "All items share the same channel resources and splitting would fragment the ownership chain").
