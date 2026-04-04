# Lesson: Update Doc Comments During Cross-Cutting Refactors

**Category:** convention
**Discovered:** task_01_context_agnostic_refactor (2026-04-04)
**Severity:** low

## Context
During the Team → FactionId cross-cutting refactor, the executor updated all code references (imports, queries, struct fields, match arms) but left 3 stale `///` doc comments in `zmq_bridge/systems.rs` that still mentioned "Team" instead of "FactionId".

## Problem
When performing a cross-cutting rename/refactor, executors focus on code that affects compilation (types, imports, match arms) but overlook doc comments that reference the old concept. This creates confusion for future agents scanning files for context.

## Correct Approach
When refactoring a concept across multiple files, grep for the old name in ALL content (not just code paths) including:
- `///` doc comments
- `//!` module-level comments
- `//` inline comments
- String literals in println/eprintln

## Example
- ❌ What the executor left:
```rust
/// Queries all entities with EntityId, Position, and Team components
fn build_state_snapshot(
    query: &Query<(&EntityId, &Position, &FactionId, &StatBlock)>,
```
- ✅ What it should be:
```rust
/// Queries all entities with EntityId, Position, FactionId and StatBlock components
fn build_state_snapshot(
    query: &Query<(&EntityId, &Position, &FactionId, &StatBlock)>,
```
