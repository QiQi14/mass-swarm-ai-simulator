# Observation Channel v4.0 — Profile-Driven Normalization & Channel Layout Overhaul

> **Date:** 2026-04-12
> **Status:** COMPLETE
> **Process:** Direct implementation (bypassed DAG planning — approved via artifact comments)

---

## Problem Statement

The observation pipeline had 3 critical design flaws:
1. **Hardcoded normalization constants** (`* 100.0`) in `snapshot.rs`, `ws_sync.rs`, and `vectorizer.py` caused input clamping for heterogeneous unit types (200 HP traps vs 24 HP targets).
2. **Wasted channel capacity** — ch2 was "reserved/zero", fog consumed 2 channels (ch5/ch6) instead of 1.
3. **Missing brain combat power** — the CNN could not see the swarm's own ECP, preventing engage/retreat decision-making.

## Solution: 8-Channel v4.0 Layout

### Channel Assignment

| Ch | Old Layout | New Layout (v4.0) | Change |
|----|-----------|-------------------|--------|
| ch0 | Brain density | → All friendly count density | Added sub-faction merge |
| ch1 | Unified enemy density | → All enemy count density | Same purpose |
| ch2 | Reserved (zeros) | → **All friendly ECP density** | **NEW: enables engage/retreat** |
| ch3 | Sub-faction density | → **All enemy ECP density** | Moved from ch7 |
| ch4 | Terrain cost | → Terrain cost | Unchanged |
| ch5 | Fog explored | → **Merged 3-level fog** (0/0.5/1.0) | Merged ch5+ch6 |
| ch6 | Fog visible | → **Interactable terrain** (zeros) | Plumbed for future |
| ch7 | Enemy ECP density | → **System objective signal** (zeros) | Plumbed for future |

### Normalization Fix

**Before:** `max_ecp_per_cell = DEFAULT_MAX_DENSITY * 100.0` (hardcoded)
**After:** `max_ecp_per_cell = density_config.max_density × density_config.max_entity_ecp` (profile-driven)

`max_entity_ecp` is auto-computed from spawn stats during `reset()` and transmitted via the ZMQ `ResetEnvironment` payload.

---

## Files Modified

### Rust Micro-Core (6 files)

| File | Change |
|------|--------|
| `micro-core/src/config/buff.rs` | Added `max_entity_ecp: f32` to `DensityConfig` (default 100.0) |
| `micro-core/src/bridges/zmq_bridge/snapshot.rs` | Replaced `DEFAULT_MAX_DENSITY * 100.0` with `density_config.max_density * density_config.max_entity_ecp`; added `DensityConfig` param + import |
| `micro-core/src/bridges/zmq_bridge/systems.rs` | Added `Res<DensityConfig>` to `ai_trigger_system`; wired `max_entity_ecp` in reset pattern match + `ResetRequest` construction; added `DensityConfig` to 2 test apps |
| `micro-core/src/bridges/zmq_bridge/reset.rs` | Added `max_entity_ecp: Option<f32>` to `ResetRequest`; wired into `density_config` during reset |
| `micro-core/src/bridges/zmq_protocol/directives.rs` | Added `max_entity_ecp: Option<f32>` to `AiResponse::ResetEnvironment` variant |
| `micro-core/src/systems/ws_sync.rs` | Replaced `max_density * 100.0` with `max_density * max_entity_ecp` from `DensityConfig` |

### Python Macro-Brain (4 files)

| File | Change |
|------|--------|
| `macro-brain/src/utils/vectorizer.py` | **Full rewrite.** v4.0 channel layout: ch0-1=count, ch2-3=ECP (w/ sub-faction merge), ch5=merged 3-level fog, ch6-7=zeros. Added `max_hp` and `active_sub_faction_ids` params. Updated summary vector (force_ratio, intervention_active). |
| `macro-brain/src/env/swarm_env.py` | Auto-computes `_max_entity_hp` from spawn stats; sends `max_entity_ecp` in reset payload; passes `max_hp` + `active_sub_faction_ids` to both vectorize calls |
| `macro-brain/src/env/spaces.py` | Updated channel docstring to v4.0 layout |
| `macro-brain/src/env/rewards.py` | Fixed fog threshold from `> 0.5` to `>= 0.4` for 3-level fog encoding |

### Tests (3 files)

| File | Change |
|------|--------|
| `macro-brain/tests/test_vectorizer.py` | Updated 10 tests: ch2→friendly ECP, ch3→enemy ECP, ch7→zeros, LKP tracks ch3 not ch7, summary indices shifted |
| `macro-brain/tests/test_channel_integrity.py` | **Full rewrite.** 97 tests for v4.0: engage/retreat decision test, trap/target differentiation, force ratio, plumbed zeros, 3-level fog |
| `macro-brain/tests/test_tactical_integration.py` | Fixed `test_fog_disabled_channels`: ch6 is now interactable terrain (zeros), not fog_visible (1.0) |

### Documentation — Agent Context (updated in previous session)

| File | Change |
|------|--------|
| `.agents/context/engine-mechanics.md` | Updated §14 Observation Channel Layout table and ECP normalization formula |
| `.agents/context/training-curriculum.md` | Updated §4 Observation Space with v4.0 layout and summary vector |
| `.agents/context/ipc-protocol.md` | Added `max_entity_ecp` to `ResetEnvironment` payload documentation |

### Documentation — Human-Facing

| File | Change |
|------|--------|
| `TRAINING_STATUS.md` | Added v4.0 Observation Channel Layout section, updated test counts (221 Rust / 214 Python), added training history entries for heterogeneous mechanics and channel overhaul |
| `ROADMAP.md` | Updated Phase 3.5 status to v4.0, added heterogeneous mechanics and channel overhaul milestones |
| `docs/architecture.md` | Updated outdated warning banner to reference v4.0 channels and `TRAINING_STATUS.md` |
| `USAGE.md` | Complete rewrite: updated architecture diagram, 3-workflow quickstart (Playground/Training/Watch), Vite-based dev server, train.sh reference, 8-channel overlay table, game profile system, 9-stage curriculum table, accurate file tree |

### Debug Visualizer (3 files)

| File | Change |
|------|--------|
| `debug-visualizer/src/panels/shared/viewport.js` | Rewrote Observation Channels section: 3 grouped blocks (🟦 Force ch0-3, 🟩 Environment ch4-5, 🟨 Tactical ch6-7), disabled toggles for future channels |
| `debug-visualizer/src/state.js` | Added `showFriendlyEcp` and `showFogAwareness` toggle state variables |
| `debug-visualizer/src/draw/entities.js` | Replaced `drawThreatGlow` with `drawEcpGlow` (dual-mode: friendly=cyan, enemy=magenta), added `drawFogAwarenessOverlay` (3-level fog visualization) |
| `debug-visualizer/src/styles/controls.css` | Added `.toggle-control.disabled` styling for future ch6/ch7 channels |

---

## Summary Vector (12-dim) — Updated

| Index | Content | Normalization |
|-------|---------|---------------|
| 0 | Own alive count | / max_entities |
| 1 | Enemy alive count | / max_entities |
| 2 | Own avg HP | / max_hp (profile-driven) |
| 3 | Enemy avg HP | / max_hp (profile-driven) |
| 4 | Sub-faction count | / 5.0 |
| 5 | Own total HP | / (max_entities × max_hp) |
| 6 | Enemy total HP | / (max_entities × max_hp) |
| 7 | Time elapsed | / max_steps |
| 8 | Fog explored % | [0, 1] |
| 9 | Has sub-factions | 0 or 1 |
| 10 | Intervention active | 0 or 1 |
| 11 | Force ratio | own/(own+enemy) |

---

## Verification Results

| Suite | Result |
|-------|--------|
| `cargo check` | ✅ 0 errors |
| `cargo test` | ✅ 221 passed (209 lib + 4 integration + 8 doctests) |
| `pytest tests/` | ✅ 214 passed, 0 failed |

---

## Impact on Training

> [!IMPORTANT]
> This change **requires a fresh training start**. Existing checkpoints are incompatible due to:
> - Channel semantics changed (ch2, ch3, ch5, ch6, ch7 all have new meanings)
> - Summary vector indices shifted (indices 5-11 reassigned)
> - Normalization constants now dynamic
>
> The CNN kernel weights for ch6/ch7 are pre-allocated as zeros from episode 1, preventing "kernel weight shock" when these channels are activated in future curriculum stages.
