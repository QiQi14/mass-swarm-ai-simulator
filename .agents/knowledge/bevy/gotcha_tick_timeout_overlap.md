# Lesson: Wait timeout overlaps with tick-based simulation exits

**Category:** gotcha
**Discovered:** Task 08 - Integration ZMQ QA
**Severity:** medium

## Context
During QA of the ZMQ bridge integration (Task 08), the acceptance criteria required verifying a ZMQ timeout error message on stdout while running `cargo run -- --smoke-test` without the Python stub running. The smoke test was designed to automatically exit at exactly 300 ticks. The simulation ran at 60 TPS natively.

## Problem
The acceptance criterion was logically impossible to fulfill.
- The simulation runs at exactly 60 TPS via a strict sleeper runner.
- The `SMOKE_TEST_MAX_TICKS` limit was set to 300, which evaluates to exactly 5.0 seconds of real execution time.
- The AI communication trigger fired at tick 30 (0.5 seconds elapsed real time).
- The `zmq_timeout_secs` config for the `zeromq-rs` connection was exactly 5.0 seconds.
Because the ZMQ timeout (0.5s + 5.0s = 5.5s real time) takes place **after** the smoke test limit stops the container (5.0s real time), the simulation gracefully exited at tick 300 without ever logging the timeout error to stderr. The Acceptance Criteria demanded a warning log that was mathematically preempted by the smoke test termination limit.

## Correct Approach
When assigning Acceptance Criteria for parallel limits (time-based vs. tick-based), always ensure the threshold for the tested warning logic clears the smoke test's enforced limits.

## Example
- ❌ **What the task design did:** Required observing a 5.0-second timeout warning in a system hardcoded to exit unconditionally at a 5.0-second tick limit.
- ✅ **What it should be:** Lower the timeout configuration (e.g. `zmq_timeout_secs: 2`) during testing, OR raise the `SMOKE_TEST_MAX_TICKS` limit (e.g. `SMOKE_TEST_MAX_TICKS = 600`) to guarantee the timeout sequence resolves entirely before the smoke test triggers an implicit teardown.
