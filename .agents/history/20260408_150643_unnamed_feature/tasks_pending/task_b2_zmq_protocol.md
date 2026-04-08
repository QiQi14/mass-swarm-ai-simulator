Task_ID: B2
Execution_Phase: 2
Model_Tier: advanced
Target_Files:
  - micro-core/src/systems/directive_executor/executor.rs
  - micro-core/src/systems/directive_executor/mod.rs
  - micro-core/src/bridges/zmq_bridge/systems.rs
Dependencies: A1
Context_Bindings:
  - implementation_plan.md
  - implementation_plan_feature_1.md
Strict_Instructions:
  1. In `directive_executor/mod.rs`, update `LatestDirective` to use `pub directives: Vec<MacroDirective>`.
  2. In `directive_executor/executor.rs`, swap the `take()` logic to `std::mem::take(&mut latest.directives)` and iterate over all directives. Apply NO game logic.
  3. In `zmq_bridge/systems.rs`, update `parse_ai_response` to ACCEPT ONLY the `macro_directives` batch format. Drop the legacy format (PATCH 1).
Verification_Strategy:
  Test_Type: unit
  Test_Stack: cargo test
  Acceptance_Criteria:
    - ZMQ bridge parses `"macro_directives"` correctly
    - Old `"macro_directive"` format prints an error (no panic) and returns empty
    - Executor loops through all elements
  Suggested_Test_Commands:
    - cd micro-core && cargo test directive_executor
    - cd micro-core && cargo test zmq
