# QA Certification Report: task_07_ipc_visualizer_upgrades

> Verification of the Telemetry & Debug Visualizer upgrade task.

## Verification Loop

| Attempt | Date | Result | Summary |
|---------|------|--------|---------|
| 1 | 2026-04-04 | FAIL | 5 defects found — 3 contract violations, 1 missing tests, 1 leftover artifact |

---

## Latest Verification (Attempt 1)

### 1. Build Gate
- **Command:** `cargo check` (default features) + `cargo check --no-default-features` (production)
- **Result:** PASS
- **Evidence:**
```
warning: `micro-core` (lib) generated 1 warning (run `cargo fix --lib -p micro-core` to apply 1 suggestion)
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.09s

# --no-default-features:
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.14s
```
Both dev and production builds compile cleanly (only pre-existing `FlowField` unused import warning from Task 06).

### 2. Regression Scan
- **Prior Tests Found:** None found in `.agents/history/*/tests/INDEX.md`
- **Reused/Adapted:** N/A

### 3. Test Authoring
- **Test Files Created:** None — using existing tests and Suggested_Test_Commands
- **Coverage:** See acceptance criteria below
- **Test Stack:** `cargo test` (Rust, per Verification_Strategy)

### 4. Test Execution Gate
- **Commands Run:** `cargo test` (full suite), `cargo test ws_sync`, `cargo test ws_command`
- **Results:** 62 passed, 0 failed, 0 skipped
- **Evidence:**
```
running 62 tests
test systems::ws_sync::tests::test_ws_sync_system_broadcasts_changes ... ok
test systems::ws_command::tests::test_step_tick_system_decrements_and_pauses ... ok
...
test result: ok. 62 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
```

### 5. Acceptance Criteria

| # | Criterion | Verified? | Evidence |
|---|-----------|-----------|----------|
| 1 | SyncDelta includes removed array and telemetry object | ⚠️ Partial | `removed` field present in protocol. BUT telemetry only sent when `!moved.is_empty()` — see Defect D1 |
| 2 | FlowFieldSync message broadcasts flow field vectors | ✅ | `FlowFieldSync` variant in `ws_protocol.rs:52-60`, `flow_field_broadcast_system` in `telemetry.rs:34-71` |
| 3 | PerfTelemetry resource populated by systems | ✅ | `PerfTelemetry` resource created by `TelemetryPlugin`, timing instrumented in `ws_sync` |
| 4 | Dual canvas: bg at ~2 TPS, entities at 60 FPS | ✅ | `#canvas-bg` (z:1) + `#canvas-entities` (z:2) in HTML. Background redraws on `FlowFieldSync` + toggle. Entities at `requestAnimationFrame`. |
| 5 | Sparkline graphs track telemetry values over time | ✅ | `Sparkline` class with ring buffer of 60 samples. `graph-tps` and `graph-entities` canvases in HTML |
| 6 | Performance bar chart with green/yellow/red | ✅ | `updatePerfBars()` with `<200=green, <1000=yellow, else=red`. `PERF_SYSTEMS` array matches PerfTelemetry fields |
| 7 | Click-to-inspect shows entity data | ✅ | `mouseup` handler with O(N) nearest search, threshold 100 (10 wu²), inspector panel update per frame |
| 8 | Spatial grid overlay toggleable | ✅ | `toggle-spatial-grid` checkbox + `drawSpatialGrid()` on bg canvas |
| 9 | Flow field arrows toggleable | ✅ | `toggle-flow-field` checkbox + `drawFlowFieldArrows()` on bg canvas |
| 10 | Health bars render only when damaged | ✅ | `drawHealthBars()` skips when `stats[0] >= 1.0`, green→red lerp |
| 11 | Death animation on entity removal | ✅ | `addDeathAnimation()` + `drawDeathAnimations()` with 500ms fade ring |
| 12 | Faction behavior toggles functional | ✅ | `initFactionToggles()` + `sendCommand('set_faction_mode', ...)` |
| 13 | set_faction_mode command modifies FactionBehaviorMode | ✅ | `ws_command.rs:96-108` — insert/remove from `static_factions` |

### 6. Negative Path Testing

| Scenario | Expected Behavior | Actual Behavior | Pass? |
|----------|-------------------|-----------------|-------|
| No entities moved (only removals) | Removal events still reach browser | `if !moved.is_empty()` gate prevents broadcast → **removal events LOST** | ❌ D1 |
| Selected entity dies | Auto-deselect in inspector | `updateInspectorPanel()` calls `deselectEntity()` when `!ent` — correct | ✅ |
| FlowFieldSync before any flow field computed | Skip arrow drawing | `flowFieldCache` empty → `drawFlowFieldArrows` iterates nothing — correct | ✅ |
| Sparkline < 2 samples | Skip drawing | `if (samples.length < 2) return;` — correct | ✅ |
| Telemetry feature disabled in production | Zero overhead | `--no-default-features` compiles cleanly, no PerfTelemetry fields in SyncDelta | ✅ |

---

## Defect List

### D1: `ws_sync_system` — Removal events dropped when no entities moved (CRITICAL)

**File:** `micro-core/src/systems/ws_sync.rs:53`
**Contract Violation:** Spec §2.4 and task brief §3 say: *"Always broadcast (even empty moved) so removal events always flow"*

**Problem:** The current implementation wraps SyncDelta creation inside `if !moved.is_empty()`. If no entities moved this tick but entities were removed, the removal events are drained (line 50-51) but never serialized/sent. They are permanently lost.

```rust
// CURRENT (BROKEN):
let removed = removal_events.removed_ids.clone();
removal_events.removed_ids.clear();              // ← drained here
if !moved.is_empty() {                            // ← but only sent if moved is non-empty
    let msg = WsMessage::SyncDelta { ... removed ... };
```

**Fix:** Remove the `if !moved.is_empty()` guard. Always broadcast SyncDelta.

### D2: Missing mandated unit tests (MODERATE)

**Contract:** Task brief §Unit Tests (Rust) mandates 4 tests:
1. `PerfTelemetry::default()` — all zeros
2. `SyncDelta serde roundtrip` — includes removed + telemetry
3. `FlowFieldSync serde roundtrip` — includes vectors
4. `set_faction_mode command` — toggles static_factions

**Actually present:** Only pre-existing tests for `ws_sync` and `step_tick_system`. None of the 4 mandated tests were written:
- No `test_perf_telemetry_default_all_zeros` in `telemetry.rs`
- No `test_sync_delta_serde_roundtrip_with_removed_and_telemetry` in `ws_protocol.rs`
- No `test_flow_field_sync_serde_roundtrip` in `ws_protocol.rs`
- No `test_set_faction_mode_toggles_static_factions` in `ws_command.rs`

### D3: `plugins/mod.rs` and `telemetry.rs` — Feature gate architecture mismatch (MODERATE)

**Contract:** Spec §2.1b says `plugins/mod.rs` should gate the module: `#[cfg(feature = "debug-telemetry")] pub mod telemetry;`
**Deviation noted:** The changelog says *"PerfTelemetry is NOT placed under #[cfg]"* but `plugins/mod.rs` DOES gate the entire module under `#[cfg(feature = "debug-telemetry")]`.

**Actual Problem:** In `lib.rs` line 24, `pub mod plugins;` is **NOT feature-gated**. This means in production (`--no-default-features`), `plugins/mod.rs` is compiled but is empty (since all its contents are `#[cfg(feature = "debug-telemetry")]`). The module compiles as an empty module — no functional issue, BUT `ws_sync.rs` line 17-18 has:
```rust
#[cfg(feature = "debug-telemetry")]
use crate::plugins::telemetry::PerfTelemetry;
```
This works because the import is also gated. **Result: No functional bug, but the architecture differs from spec.** The spec intended `lib.rs` to also gate `pub mod plugins;` or have the type visible unconditionally. Since the executor noted this deviation in the changelog and it compiles cleanly in both modes, this is a **minor deviation** but should be documented.

### D4: Leftover scratch file `micro-core/test.rs` (MINOR)

The executor left a scratch file `micro-core/test.rs` (98 bytes) used to verify `#[cfg]` on function parameters. This is not in `Target_Files` scope and should not be committed.

### D5: `telemetry.rs` missing module-level doc comment (STYLE)

**Contract:** Rust Code Standards (SKILL.md §1.1) require every `.rs` file to start with `//!` module-level doc comment with `## Ownership` and `## Depends On`. The `telemetry.rs` file has no module-level doc comment.

---

### 7. Certification Decision
- **Status:** FAIL
- **Reason:**
  1. **D1 (CRITICAL):** Removal events silently dropped when no entities moved — violates explicit contract requirement "Always broadcast"
  2. **D2 (MODERATE):** 4 mandated unit tests not implemented — PerfTelemetry default, SyncDelta serde roundtrip, FlowFieldSync serde roundtrip, set_faction_mode toggle test
  3. **D3 (MODERATE):** Architecture deviation from spec (acceptable but must be documented as intentional)
  4. **D4 (MINOR):** Leftover scratch file `micro-core/test.rs`
  5. **D5 (STYLE):** Missing module doc comment on `telemetry.rs`

> D1 and D2 are blocking. D3-D5 should be fixed but would not independently block certification.
