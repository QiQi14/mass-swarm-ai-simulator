# Lesson: Stale rust-analyzer errors from cached fingerprints

**Category:** tooling
**Discovered:** task_07_zmq_bridge_plugin (2026-04-03)
**Severity:** low

## Context
After an executor makes multiple fix iterations (e.g., adding Mutex wrappers, fixing type annotations), rust-analyzer may continue showing errors from earlier failed compilation attempts even though `cargo check` and `cargo clippy` pass cleanly.

## Problem
Rust-analyzer reads diagnostic data from `target/debug/.fingerprint/`. When the compiler emits errors during an intermediate build, those diagnostics get cached in fingerprint files. Even after the source is fixed and a subsequent `cargo check` succeeds, rust-analyzer may still display the stale errors from the cached fingerprint data.

## Correct Approach
Run `cargo clean && cargo check` to wipe stale fingerprints and regenerate them from scratch. Rust-analyzer will then pick up the clean diagnostics.

## Example
- ❌ What it looks like: Rust-analyzer shows "type annotations needed" and "Receiver cannot be shared between threads" — but `cargo check` passes with zero errors.
- ✅ Fix: `cd micro-core && cargo clean && cargo check` — errors disappear in rust-analyzer within seconds.
