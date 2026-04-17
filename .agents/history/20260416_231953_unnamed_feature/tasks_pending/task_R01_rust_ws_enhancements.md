# Task R01: Rust WS spawn_wave + set_interaction Enhancement

- **Task_ID:** `R01_rust_ws_enhancements`
- **Execution_Phase:** 0 (Playground — parallel with all Phase 1 frontend tasks)
- **Model_Tier:** `standard`
- **Live_System_Impact:** `additive` — adds optional fields to existing WS handlers

## Target_Files
- `micro-core/src/systems/ws_command.rs` — MODIFY

## Dependencies
- None

## Context_Bindings
- `implementation_plan_playground_feature_0.md` — Full strict instructions for R01 + R02
- `.agents/skills/rust-code-standards/SKILL.md`

## Strict_Instructions

**Read `implementation_plan_playground_feature_0.md` for complete implementation details.** Summary:

### R01: spawn_wave Enhancement
- Parse optional `unit_class_id: u32` from WS `spawn_wave` JSON payload (default: 0)
- Parse optional `movement` config block from payload
- Pass `unit_class_id` to `UnitClassId` component on spawned entities
- Pass movement config to `MovementConfig` component if provided
- All new fields use `#[serde(default)]` for backward compatibility

### R02: set_interaction Enhancement
- Parse optional `source_class: Option<u32>` and `target_class: Option<u32>` from WS `set_interaction` JSON
- Parse optional `cooldown_ticks: Option<u32>`
- Pass these to `InteractionRule` fields
- All new fields use `#[serde(default)]` for backward compatibility

**Both changes are additive — existing WS payloads without the new fields continue to work identically.**

## Verification_Strategy
```
Test_Type: unit
Acceptance_Criteria:
  - "spawn_wave without unit_class_id works as before (default 0)"
  - "spawn_wave with unit_class_id=2 spawns entities with UnitClassId(2)"
  - "spawn_wave with movement config sets custom MovementConfig"
  - "set_interaction without class filters works as before"
  - "set_interaction with source_class/target_class sets class-filtered rules"
  - "cargo test passes"
Suggested_Test_Commands:
  - "cd micro-core && cargo check"
  - "cd micro-core && cargo test"
```
