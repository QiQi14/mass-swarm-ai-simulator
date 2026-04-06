# Feature 4: Integration & Smoke Test (v3 — Patched)

> **Tasks:** 10 (Integration)
> **Domain:** Rust + Python (cross-node)
> **v3 Patches:** ZMQ deadlock recovery test, MDP pollution test, Pacifist Flank verification

---

## Task 10: Integration & End-to-End Smoke Test

**Task_ID:** `task_10_integration_smoke_test`
**Execution_Phase:** 5 (final, sequential)
**Model_Tier:** `advanced`
**Target_Files:**
  - `micro-core/src/main.rs` (MODIFY)
**Dependencies:** All previous tasks (01–09)

### Strict Instructions

#### 1. Wire New Resources into `main.rs`

```rust
use micro_core::config::{
    ActiveZoneModifiers, InterventionTracker, FactionSpeedBuffs,
    AggroMaskRegistry, ActiveSubFactions,
};
use micro_core::systems::directive_executor::{
    LatestDirective, directive_executor_system,
    zone_tick_system, speed_buff_tick_system,
};
use micro_core::systems::engine_override::engine_override_system;

app.init_resource::<ActiveZoneModifiers>()
   .init_resource::<InterventionTracker>()
   .init_resource::<FactionSpeedBuffs>()
   .init_resource::<AggroMaskRegistry>()
   .init_resource::<ActiveSubFactions>()
   .init_resource::<LatestDirective>();
```

#### 2. Register Systems

```rust
// After AI poll, before movement:
.add_systems(Update, (
    directive_executor_system,
    zone_tick_system,
    speed_buff_tick_system,
).chain()
 .run_if(|paused: Res<SimPaused>, step: Res<SimStepRemaining>| !paused.0 || step.0 > 0))

// After movement:
.add_systems(Update, engine_override_system
    .after(movement_system)
    .run_if(|paused: Res<SimPaused>, step: Res<SimStepRemaining>| !paused.0 || step.0 > 0))
```

#### 3. End-to-End Verification

**Phase A — Backward Compatibility:**
```bash
cd micro-core && cargo test           # All existing 111+ tests pass
cd micro-core && cargo clippy -- -D warnings   # Zero warnings
cd macro-brain && python -m pytest tests/ -v   # All Python tests pass
```

**Phase B — Stub AI (Legacy Protocol):**
```bash
# Terminal 1: cd micro-core && cargo run -- --entity-count 200
# Terminal 2: cd macro-brain && python -m src.stub_ai
# Verify: Stub receives snapshots with density_maps, replies HOLD, legacy fallback works
```

**Phase C — Training (New Protocol):**
```bash
# Terminal 1: cd micro-core && cargo run -- --entity-count 200
# Terminal 2: cd macro-brain && python -m src.training.train --timesteps 5000 --max-steps 50
```

Verify:
- [ ] SwarmEnv connects, PPO trains without crashes
- [ ] Reward values appear (non-zero)
- [ ] Checkpoint saved to `./checkpoints/`

**Phase D — Directive Behavior Verification:**

Open Debug Visualizer during training and verify:

| Directive | Expected Visual | ✓ |
|-----------|----------------|---|
| `UpdateNavigation` | Swarm changes flow direction | |
| `TriggerFrenzy` | Visually faster movement | |
| `Retreat` | Swarm pulls back toward retreat point | |
| `SetZoneModifier` | Entities cluster around attracted zone | |
| `SplitFaction` | Subset of entities changes behavior/direction | |
| `MergeFaction` | Sub-faction returns to main force | |
| `SetAggroMask` | Flanking unit passes through enemy without fighting | |

**Phase E — Patch Regression Verification (Manual):**

> [!CAUTION]
> These tests specifically reproduce the 8 vulnerabilities identified during review.

| Patch | Test Procedure | Expected Result |
|-------|---------------|----------------|
| **P1: Vaporization** | Insert SplitFaction(30%) manually, observe entity counts over 3 ticks | Count changes exactly once, not continuously |
| **P2: Moses Effect** | Place wall, apply SetZoneModifier with cost_modifier=-500 on wall | Entities route around wall, NOT through it |
| **P3: Ghost State** | SplitFaction → TriggerFrenzy for sub-faction → MergeFaction → SplitFaction with same ID | New split army does NOT inherit stale speed buff |
| **P4: f32 Sort** | SplitFaction with 10000 entities | No panic, correct count split |
| **P5: Pacifist Flank** | Monitor reward during training — check flanking_bonus when sub-faction is far from enemy | Bonus = 0.0 for distant sub-factions |
| **P6: Static Epicenter** | Log epicenter values during SplitFaction — should track swarm position | Epicenter near swarm centroid, NOT (800, 500) |
| **P7: Sub-Faction Desync** | Kill all entities of a sub-faction, then check Python's `_active_sub_factions` | List updates from Rust snapshot, doesn't retain ghost ID |
| **P8: ZMQ Deadlock** | Pause Rust core mid-training (Ctrl+Z), wait for timeout | Python prints timeout warning, truncates episode, continues training |
| **P8: MDP Pollution** | Enable EngineOverride on some entities, check SB3 reward log | No zero-reward entries during intervention (ticks swallowed) |

#### 4. Known Risks

> [!WARNING]
> **ZMQ REP Socket Ordering:** Python uses `zmq.REP` (binds, strict `recv → send`).
> Rust uses `zmq.REQ` (connects). The tick swallowing loop maintains correct
> alternation: each iteration does `recv → send(Hold)`. Breaking this ordering
> will deadlock both processes.

> [!WARNING]
> **NavigationRule Breaking Change:** `target_faction → target: NavigationTarget`.
> All existing tests referencing `target_faction` must be migrated.

> [!WARNING]
> **SplitFaction Flow Field Delay:** After splitting, the new sub-faction needs
> a flow field calculated on the next interval tick (~0.5s delay). During this
> window, split entities idle. This is acceptable for Phase 3.

> [!CAUTION]
> **Training Speed:** ~2 steps/sec with full ZMQ round-trip per step.
> Phase 4 optimizes with batch inference and binary serialization.

### Verification_Strategy
```
Test_Type: integration + e2e
Test_Stack: cargo test (Rust) + pytest (Python) + manual visual
Acceptance_Criteria:
  Phase A: cargo build + test + clippy all pass
  Phase B: Stub AI backward compatible
  Phase C: PPO trains 5000 steps without crash
  Phase D: All 7 directive types produce visible behavior
  Phase E: All 8 patch regression tests pass
Suggested_Test_Commands:
  - "cd micro-core && cargo test"
  - "cd micro-core && cargo clippy -- -D warnings"
  - "cd macro-brain && python -m pytest tests/ -v"
Manual_Steps:
  - See Phase D and Phase E tables above
```
