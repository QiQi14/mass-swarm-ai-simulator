# Phase A: Context-Agnostic ECP Audit — Fix All 6 Violations

> **Goal:** Eliminate all hardcoded `stat[0]` / `HP` references from the ECP density pipeline, Python schema, and observation vectorizer. Make the engine truly context-agnostic.

## Violation Overview

| ID | Fix | Files Modified |
|----|-----|---------------|
| V-01 | Add `ecp_stat_index` to `DensityConfig` | `buff.rs`, `snapshot.rs`, `ws_sync.rs`, `reset.rs`, `directives.rs`, `systems.rs` |
| V-02 | Rename `hp` → `primary_stat` in Rust ECP code | `snapshot.rs`, `ws_sync.rs`, `state_vectorizer.rs` |
| V-03 | Rename `FactionStats.hp` → `FactionStats.primary_stat` | `definitions.py`, `parser.py`, `curriculum.py` |
| V-04 | Make summary vector stat index configurable | `vectorizer.py` |
| V-05 | Derive primary stat index from removal rules | `swarm_env.py` |
| V-06 | Rename `_max_entity_hp` → `_max_primary_stat` | `swarm_env.py` |

---

## Proposed Changes

### Component 1: Rust — DensityConfig + ECP Pipeline (V-01, V-02)

#### [MODIFY] [buff.rs](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/micro-core/src/config/buff.rs)
- Added `ecp_stat_index: Option<usize>` to `DensityConfig`
- Default: `Some(0)` — backward-compatible

#### [MODIFY] [snapshot.rs](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/micro-core/src/bridges/zmq_bridge/snapshot.rs)
- Replaced `let hp = stat_block.0[0]` → configurable index via `density_config.ecp_stat_index`
- Renamed variable `hp` → `primary_stat`

#### [MODIFY] [ws_sync.rs](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/micro-core/src/systems/ws_sync.rs)
- Same fix as snapshot.rs for the WebSocket ECP telemetry path

#### [MODIFY] [state_vectorizer.rs](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/micro-core/src/systems/state_vectorizer.rs)
- Renamed `hp` → `primary_stat` in function docs, tuple comments, and loop bindings

#### [MODIFY] Protocol chain: directives.rs → systems.rs → reset.rs
- Added `ecp_stat_index: Option<Option<usize>>` to `AiResponse::ResetEnvironment`, `ResetRequest`, and reset handler

### Component 2: Python — Schema + Vectorizer (V-03 through V-06)

#### [MODIFY] [definitions.py](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/macro-brain/src/config/definitions.py)
- Renamed `FactionStats.hp` → `FactionStats.primary_stat`

#### [MODIFY] [parser.py](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/macro-brain/src/config/parser.py)
- Updated parsing with backward-compat fallback: `get("primary_stat", get("hp", 100.0))`

#### [MODIFY] [vectorizer.py](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/macro-brain/src/utils/vectorizer.py)
- Added `summary_stat_index: int = 0` parameter
- All hardcoded `[0]` stat accesses now use configurable index with bounds checking

#### [MODIFY] [swarm_env.py](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/macro-brain/src/env/swarm_env.py)
- Renamed `_max_entity_hp` → `_max_primary_stat`
- Added `_primary_stat_index` derived from `removal_rules[0].stat_index`
- Updated reset payload, both vectorizer calls, and debuff condition check

#### [MODIFY] [curriculum.py](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/macro-brain/src/training/curriculum.py)
- Updated `_faction_stats()` to use `f.stats.primary_stat`

#### Tests Updated
- `test_validator.py` — `FactionStats(hp=100)` → `FactionStats(primary_stat=100)`
- `test_stage5_terrain.py` — Mock `.stats.hp` → `.stats.primary_stat`

## Verification

- **209 Rust tests** ✅ all pass
- **214 Python tests** ✅ all pass
- **Clippy** ✅ no new warnings
- **Context docs updated:** `engine-mechanics.md`, `ipc-protocol.md`
