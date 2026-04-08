# Task B2 Changelog: ZMQ Batch Directive Protocol

## Summary
Updated the Micro-Core ZMQ protocol parser and executor systems to securely parse and map an array of macro directives within a single tick window natively, removing backwards-compatibility for singular directive formatting as specified.

## Core Code Adjustments
- **`micro-core/src/systems/directive_executor/executor.rs`:** Upgraded `LatestDirective` resource struct to contain `pub directives: Vec<MacroDirective>` tracking batched directives uniformly. Refactored the `directive_executor_system` to natively loop through and map `std::mem::take(&mut latest.directives)` correctly iterating upon all macro directives in order per game tick execution window, maintaining identical execution mapping semantics upon every element iteration gracefully.
- **`micro-core/src/bridges/zmq_bridge/systems.rs`:** Upgraded the `ai_poll_system` parser natively extracting `"msg_type": "macro_directives"` JSON parsing. Added parsing and formatting handling specifically mapping back compatibility rejection error streams printing gracefully instead of mutating ECS structs errantly natively.
- **Tests Updating:** Upgraded parameter references natively resolving `.directives` from isolated test coverage mapping vectors effectively. Adjusted and verified validation mapping correctly ensuring backward syntax error cases safely returning `[]` and mapping cleanly to batch format. 

## Context Independence Met
- Maintained 100% agnostic mapping execution semantics completely preserving zero game context in the `Micro-Core` structure.
- `cargo test` executes gracefully natively ensuring all `executor_tests` and `zmq_bridge` test paths compile with total execution validation safely passing completely smoothly across zero system errors natively.
