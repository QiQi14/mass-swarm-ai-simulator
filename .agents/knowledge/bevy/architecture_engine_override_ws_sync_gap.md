# Lesson: EngineOverride entity state not synced in WS EntityState

**Category:** architecture
**Discovered:** task_12_visualizer_phase3 QA audit (2026-04-06)
**Severity:** low

## Context
Task 12 (Debug Visualizer Phase 3) added an EngineOverride flashing diamond marker 
in the canvas rendering layer. The marker checks `entity.has_override` on each entity.

## Problem
The `EntityState` struct in `ws_protocol.rs` does NOT include a `has_override` field.
The `SyncDelta.moved[]` array only sends `id, x, y, dx, dy, faction_id, stats`.
Therefore the EngineOverride marker will never activate because the field is always 
undefined/falsy in the JS client.

## Correct Approach
When the integration task (or a future task) needs to visualize EngineOverride entities,
either:
1. Add `has_override: bool` to `EntityState` in `ws_protocol.rs` and populate it in `ws_sync_system`
2. OR send a separate `override_entities: Vec<u32>` field in `SyncDelta` listing entity IDs with active overrides

Option 2 is more bandwidth-efficient since overrides are rare.

## Example
- ❌ What the executor did: Assumed `ent.has_override` would be available from WS messages
- ✅ What it should be: Extend the WS protocol to explicitly include override state before relying on it in the frontend
