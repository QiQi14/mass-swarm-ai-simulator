# Task 05 — Interaction + Removal Systems (Full Specification)

> **Parent Plan:** [`implementation_plan.md`](./implementation_plan.md) → Contracts 5, 6, 7
> **Architecture:** Zero-Allocation Disjoint Queries
> **This file:** Exhaustive spec for the Executor agent.

**Phase:** 2 (Parallel) | **Tier:** `standard` | **Domain:** ECS Systems  
**Target Files:** `systems/interaction.rs` [NEW], `systems/removal.rs` [NEW]  
**Dependencies:** Task 02 (SpatialHashGrid), Task 04 (Rule Resources)  
**Context Bindings:** `context/conventions`, `context/architecture`, `skills/rust-code-standards`

> **DO NOT** modify `systems/mod.rs` — Task 08 handles system wiring.

---

## 1. The Zero-Allocation Architecture

### The Monolithic Query Fallacy (REJECTED)

```rust
// ❌ WRONG — &mut StatBlock inside iterator locks the entire query.
// query.get() or query.get_mut() during iter() → RUNTIME PANIC.
Query<(Entity, &Position, &mut StatBlock, &FactionId)>
```

### The Collect→Apply Pattern (REJECTED)

```rust
// ❌ WASTEFUL — Snapshot 10K entities into Vec + HashMap every tick.
// 60 TPS × 10K entities = 600K heap allocations/sec. Trashes L1/L2 cache.
let entities: Vec<...> = query.iter().collect();
let faction_map: HashMap<...> = ...;
```

### Disjoint Queries (ADOPTED) ✅

Bevy evaluates borrow checking at the **Component level**, not the Entity level. If two queries access non-overlapping component sets, they are considered disjoint.

```rust
q_ro: Query<(Entity, &Position, &FactionId)>,  // Read-only spatial + faction
q_rw: Query<&mut StatBlock>,                    // Write-only stat mutation
```

- `q_ro` accesses `{Position, FactionId}` — immutable.
- `q_rw` accesses `{StatBlock}` — mutable.
- **Zero component overlap** → Bevy allows simultaneous access.

### Safety Proofs

| Operation | Why It's Safe |
|-----------|--------------|
| `q_ro.get(neighbor)` inside `q_ro.iter()` | Both `&self` borrows. Multiple shared refs allowed. |
| `q_rw.get_mut(neighbor)` inside `q_ro.iter()` | Disjoint component sets. Bevy validates at registration. |
| Sequential `q_rw.get_mut(Defender_X)` across iterations | `Mut<StatBlock>` dropped each scope, re-acquired next. |
| Mutation order within tick | Read loop via `q_ro` — untouched by stat writes. |

---

## 2. Critical Design Decisions (MANDATORY)

1. **Zero-Allocation Disjoint Queries** — NOT Collect→Apply. No Vec, no HashMap.
2. **Fixed delta `1.0 / 60.0`** — NOT `Res<Time>`. ML requires absolute determinism.
3. **No stat clamping** — Negative values provide "Overkill Gradient" for RL training.
4. **Self-skip** — `neighbor_entity == source_entity` → skip. SpatialHashGrid returns self.
5. **No `par_iter()`** — Single-threaded for L1 cache coherence on hot targets.

---

## 3. Full Rust Implementation

### 3.1 `micro-core/src/systems/interaction.rs` [NEW]

```rust
//! # Interaction System
//!
//! Config-driven proximity interactions using Zero-Allocation Disjoint Queries.
//! Separates read-only spatial data from mutable stat access to eliminate
//! all Vec snapshots, HashMaps, and heap allocations in the hot loop.
//!
//! ## Ownership
//! - **Task:** task_05_interaction_removal_systems
//! - **Contract:** implementation_plan.md → Contract 7
//!
//! ## Depends On
//! - `crate::components::{Position, FactionId, StatBlock}`
//! - `crate::spatial::SpatialHashGrid`
//! - `crate::rules::InteractionRuleSet`
//!
//! ## Architecture: Disjoint Queries
//! - `q_ro: Query<(Entity, &Position, &FactionId)>` — read-only spatial data
//! - `q_rw: Query<&mut StatBlock>` — write-only stat mutation
//! - Zero component overlap → safe simultaneous access
//! - Zero heap allocations in the interaction loop

use bevy::prelude::*;
use crate::components::{Position, FactionId, StatBlock};
use crate::spatial::SpatialHashGrid;
use crate::rules::InteractionRuleSet;

/// Processes proximity-based interactions between entities.
///
/// Uses Disjoint Queries for zero-allocation O(1) stat mutations:
/// - `q_ro` iterates all entities for position/faction (immutable).
/// - `q_ro.get(neighbor)` reads neighbor faction inside the loop (safe: shared borrows).
/// - `q_rw.get_mut(neighbor)` mutates neighbor stats (safe: disjoint component set).
///
/// ## Performance
/// - Single-threaded (L1 cache coherent on hot targets)
/// - Zero Vec/HashMap allocations
/// - O(N × R × K) where N=entities, R=rules, K=avg neighbors in range
/// - ~0.5ms for 10K entities with default config
pub fn interaction_system(
    grid: Res<SpatialHashGrid>,
    rules: Res<InteractionRuleSet>,
    // Query 1: Purely immutable spatial data.
    // Safe to iterate AND random-access simultaneously (multiple &self borrows).
    q_ro: Query<(Entity, &Position, &FactionId)>,
    // Query 2: Purely mutable stat data.
    // Disjoint from Query 1 (StatBlock ∩ {Position, FactionId} = ∅).
    mut q_rw: Query<&mut StatBlock>,
) {
    if rules.rules.is_empty() {
        return;
    }

    // Pre-calculate fixed delta — ML determinism requires strict fixed timestep
    let tick_delta = 1.0 / 60.0;

    for (source_entity, source_pos, source_faction) in q_ro.iter() {
        for rule in &rules.rules {
            // Only process rules where this entity is the source faction
            if rule.source_faction != source_faction.0 {
                continue;
            }

            // O(K) spatial lookup — only allocation is grid.query_radius's return Vec
            let center = Vec2::new(source_pos.x, source_pos.y);
            let neighbors = grid.query_radius(center, rule.range);

            for &(neighbor_entity, _) in &neighbors {
                // CRITICAL: Prevent self-interaction
                if neighbor_entity == source_entity {
                    continue;
                }

                // O(1) read-only lookup inside iter() — safe: multiple &self borrows
                if let Ok((_, _, neighbor_faction)) = q_ro.get(neighbor_entity) {
                    if neighbor_faction.0 != rule.target_faction {
                        continue;
                    }

                    // O(1) mutable lookup — safe: disjoint component set from q_ro
                    // Mut<StatBlock> is dropped at end of this scope before next get_mut()
                    if let Ok(mut stat_block) = q_rw.get_mut(neighbor_entity) {
                        for effect in &rule.effects {
                            if effect.stat_index < stat_block.0.len() {
                                stat_block.0[effect.stat_index] +=
                                    effect.delta_per_second * tick_delta;
                            }
                        }
                    }
                }
            }
        }
    }
}
```

### 3.2 `micro-core/src/systems/removal.rs` [NEW]

```rust
//! # Removal System
//!
//! Config-driven entity removal based on stat thresholds.
//! Uses Commands for deferred despawn — no borrow conflicts.
//!
//! ## Ownership
//! - **Task:** task_05_interaction_removal_systems
//! - **Contract:** implementation_plan.md → Contracts 5, 6, 7
//!
//! ## Depends On
//! - `crate::components::{EntityId, StatBlock}`
//! - `crate::rules::{RemovalRuleSet, RemovalCondition, RemovalEvents}`

use bevy::prelude::*;
use crate::components::{EntityId, StatBlock};
use crate::rules::{RemovalRuleSet, RemovalCondition, RemovalEvents};

/// Checks all entities against removal rules and despawns those
/// crossing stat thresholds.
///
/// Uses `Commands` for deferred despawn — entity is removed at end of frame.
/// No iterator invalidation, no borrow conflicts.
/// Records removed entity IDs in `RemovalEvents` for WebSocket broadcast.
///
/// ## Note on Negative Stats
/// Stats are NOT clamped. Health at -150.0 provides "Overkill Gradient"
/// signal to the Python Macro-Brain for learning efficient unit allocation.
pub fn removal_system(
    rules: Res<RemovalRuleSet>,
    query: Query<(Entity, &EntityId, &StatBlock)>,
    mut commands: Commands,
    mut events: ResMut<RemovalEvents>,
) {
    // Clear previous tick's removal events
    events.removed_ids.clear();

    for (entity, entity_id, stat_block) in query.iter() {
        for rule in &rules.rules {
            // Bounds check stat index
            if rule.stat_index >= stat_block.0.len() {
                continue;
            }

            let stat_value = stat_block.0[rule.stat_index];

            let should_remove = match rule.condition {
                RemovalCondition::LessOrEqual => stat_value <= rule.threshold,
                RemovalCondition::GreaterOrEqual => stat_value >= rule.threshold,
            };

            if should_remove {
                events.removed_ids.push(entity_id.id);
                commands.entity(entity).despawn();
                break; // Don't process more rules for this entity
            }
        }
    }
}
```

---

## 4. Edge Cases

| Edge Case | Behavior | How Handled |
|-----------|----------|-------------|
| Self-interaction | Entity does NOT damage itself | `neighbor_entity == source_entity` → skip |
| Same-faction no rule | No damage | No rule with source=0, target=0 in config |
| Out of range | No interaction | `grid.query_radius` returns only in-range |
| Despawned neighbor | `q_ro.get()` / `q_rw.get_mut()` returns `Err` | `if let Ok(...)` graceful |
| Stat index OOB | Skip | `stat_index < stat_block.0.len()` guard |
| 5K attackers → 1 defender | All modify same StatBlock sequentially | `Mut<StatBlock>` dropped each iteration |
| Negative stat values | Not clamped | "Overkill Gradient" for RL |
| Empty rules | No-op | Early return |

---

## 5. Performance

| Metric | Collect→Apply (REJECTED) | Disjoint Queries (ADOPTED) |
|--------|-------------------------|---------------------------|
| Allocations/tick | 10K Vec + 10K HashMap + 30K mod Vec | 0 (only grid.query_radius) |
| Cache behavior | Trashes L1/L2 | Hot Defender in L1 |
| Estimated time | ~2.0ms | **< 0.5ms** |

---

## 6. System Ordering (Task 08 Reference)

```
update_spatial_grid_system → interaction_system → removal_system → movement_system
```

---

## 7. Unit Tests

### Interaction Tests:
- **Two enemies in range:** Attacker (faction 0) + Defender (faction 1) within 15.0. After one tick: Defender stat[0] decreases by `10.0/60.0`. Attacker stat[0] decreases by `20.0/60.0`.
- **Same faction, no rule:** Two faction-0 entities near each other — no stat change.
- **Out of range:** Two different-faction entities distance > 15.0 — no stat change.

### Removal Tests:
- **Entity dies:** stat[0] = 0.0 → despawned, ID in `RemovalEvents`.
- **Entity alive:** stat[0] = 50.0 → not removed.
- **GreaterOrEqual condition:** Custom rule threshold 100.0. stat[0] = 100.0 → removed.

---

## 8. Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: unit
  Test_Stack: cargo test
  Acceptance_Criteria:
    - "interaction_system reduces target stat by delta_per_second * (1.0/60.0) per tick"
    - "Same-faction entities do not interact"
    - "Out-of-range entities do not interact"
    - "Self-interaction is prevented"
    - "Uses disjoint queries (q_ro + q_rw), NOT monolithic query"
    - "Uses fixed delta 1.0/60.0, NOT Res<Time>"
    - "Stats are NOT clamped (negative values allowed)"
    - "removal_system despawns entities crossing threshold"
    - "RemovalEvents contains despawned entity IDs"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test interaction"
    - "cd micro-core && cargo test removal"
```
