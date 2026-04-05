---
Task_ID: task_05_interaction_removal_systems
Execution_Phase: Phase 2 (Parallel)
Model_Tier: standard
Target_Files:
  - micro-core/src/systems/interaction.rs
  - micro-core/src/systems/removal.rs
Dependencies:
  - task_02_spatial_hash_grid
  - task_04_rule_resources
Context_Bindings:
  - context/conventions
  - context/architecture
  - skills/rust-code-standards
---

# STRICT INSTRUCTIONS

Implement the Interaction System and Removal System using **Zero-Allocation Disjoint Queries**.

**Read `implementation_plan.md` Contracts 5, 6, 7 AND the deep-dive spec `implementation_plan_task_05.md` for the exact architecture, safety proofs, and unit tests.**

> **CRITICAL:** The spec file `implementation_plan_task_05.md` (project root) contains the Disjoint Query architecture. Adopt the concept and verify correctness before implementation. DO NOT fall back to Collect→Apply or monolithic queries.

**DO NOT modify `systems/mod.rs` — Task 08 handles wiring.**

## Architecture: Zero-Allocation Disjoint Queries

The interaction system MUST use two disjoint queries:

```rust
q_ro: Query<(Entity, &Position, &FactionId)>,   // Read-only spatial data
mut q_rw: Query<&mut StatBlock>,                  // Write-only stat mutation
```

**Why:**
- `{Position, FactionId}` ∩ `{StatBlock}` = ∅ → Bevy allows simultaneous access
- `q_ro.get(neighbor)` inside `q_ro.iter()` → multiple shared borrows → safe
- `q_rw.get_mut(neighbor)` inside `q_ro.iter()` → disjoint components → safe
- Zero Vec snapshots, zero HashMaps, zero heap allocations

**REJECTED patterns:**
- ❌ Monolithic `Query<(Entity, &Position, &mut StatBlock, &FactionId)>` → panics on `get_mut()` during `iter()`
- ❌ Collect→Apply with Vec/HashMap → 600K allocations/sec, trashes L1/L2 cache
- ❌ `par_iter()` → data race on shared targets (5K→1 Defender crush)

## Mandatory Design Decisions

1. **Fixed delta `1.0 / 60.0`** — NOT `Res<Time>`. ML determinism: same initial state must yield identical outcomes across runs.
2. **No stat clamping** — Stats can go negative. "Overkill Gradient" signal for RL training.
3. **Self-skip** — `if neighbor_entity == source_entity { continue; }` — SpatialHashGrid returns self in results.
4. **Single-threaded** — NO `par_iter()`. Hot Defender's StatBlock stays in L1 cache.

## File Structure

### 1. `micro-core/src/systems/interaction.rs` [NEW]

`interaction_system` with disjoint queries. See spec for complete code:
- Early return if rules empty
- Pre-calc `tick_delta = 1.0 / 60.0`
- Iterate `q_ro`, match source faction, query spatial grid
- Self-skip, faction check via `q_ro.get()`, stat mutation via `q_rw.get_mut()`
- Stat index bounds check

### 2. `micro-core/src/systems/removal.rs` [NEW]

`removal_system` using `Commands::despawn()` (deferred). See spec for complete code:
- Clear `RemovalEvents` each tick
- Check each entity against removal rules
- Record entity ID, despawn, break after first match

## Unit Tests (6 tests)

### Interaction:
- Two enemies in range: stats decrease by `delta_per_second * (1.0/60.0)`
- Same faction: no interaction (no matching rule)
- Out of range: no interaction

### Removal:
- Entity with stat[0] = 0.0 → despawned, ID in RemovalEvents
- Entity with stat[0] = 50.0 → alive
- GreaterOrEqual condition: stat[0] = 100.0, threshold 100.0 → removed

---

# Verification_Strategy
Test_Type: unit
Test_Stack: cargo test
Acceptance_Criteria:
  - "interaction_system reduces target stat by delta_per_second * (1.0/60.0) per tick"
  - "Same-faction entities do not interact"
  - "Out-of-range entities do not interact"
  - "Self-interaction is prevented"
  - "Uses disjoint queries (q_ro + q_rw), NOT monolithic query"
  - "Uses fixed delta 1.0/60.0, NOT Res<Time>"
  - "Stats are NOT clamped"
  - "removal_system despawns entities crossing threshold"
  - "RemovalEvents contains despawned entity IDs"
Suggested_Test_Commands:
  - "cd micro-core && cargo test interaction"
  - "cd micro-core && cargo test removal"
