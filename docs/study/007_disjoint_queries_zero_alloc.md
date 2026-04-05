# Architecture Study: Zero-Allocation Disjoint Queries in Bevy ECS

**Date:** 2026-04-04  
**Domain:** ECS Architecture, Bevy, Systems Design  
**Full Specification:** [implementation_plan_task_05.md](../../.agents/history/20260404_234812_phase_2_universal_core_algorithms/implementation_plan_task_05.md)  
**Implementation:** [micro-core/src/systems/interaction.rs](../../micro-core/src/systems/interaction.rs)  
**Tags:** `bevy`, `ecs`, `disjoint-queries`, `zero-allocation`, `data-oriented`

---

## 1. Problem Statement

The `interaction_system` must mutate TWO entities simultaneously: attacker writes
to victim's `StatBlock`. Bevy's borrow checker prevents a single `Query<&mut StatBlock>`
from being accessed twice (shared mutable reference). Additionally, at 10K entities,
allocating a `Vec` per query per tick creates 600K+ allocations per second.

## 2. Bevy's Disjoint Query Pattern

### The Monolithic Anti-Pattern

```rust
// ❌ WRONG: This panics at runtime — two mutable borrows of same entity possible
fn interaction_system(mut query: Query<(&mut StatBlock, &Position)>) {
    for (mut attacker_stats, attacker_pos) in query.iter_mut() {
        // Cannot query for victim — query is already borrowed mutably
    }
}
```

### The Disjoint Solution

```rust
// ✅ CORRECT: Two disjoint queries — Bevy guarantees no overlap
fn interaction_system(
    mut attacker_query: Query<(Entity, &Position, &FactionId, &StatBlock)>,  // READ-ONLY
    mut victim_query: Query<&mut StatBlock>,                                  // WRITE-ONLY
) {
    // Read attacker data from query 1
    // Write victim data via query 2
    // Bevy ensures these access disjoint component sets
}
```

**Key insight:** Split your data needs across queries:
- Read-only data → immutable references `&T`
- Write targets → separate `&mut T` query accessed by `Entity` handle

### Entity Handle Pattern

```rust
for (attacker_entity, attacker_pos, attacker_faction, attacker_stats) in attacker_query.iter() {
    grid.for_each_in_radius(attacker_pos, range, |victim_entity, victim_pos| {
        if attacker_entity == victim_entity { return; }  // Skip self
        if let Ok(mut victim_stats) = victim_query.get_mut(victim_entity) {
            victim_stats.0[stat_index] += delta * dt;  // Mutate victim
        }
    });
}
```

## 3. Zero-Allocation via Closure-Based Spatial Query

### The Allocation Problem

```rust
// ❌ SLOW: allocates Vec per entity per tick
let neighbors = grid.query_radius(pos, range);  // Vec<(Entity, Vec2)>
for (n_entity, n_pos) in neighbors {
    // ...
}
```

At 10K entities × 60 TPS = 600K `Vec` allocations per second. Each `Vec` is a
heap allocation, creating GC-like pressure in Rust.

### The Zero-Allocation Solution

```rust
// ✅ FAST: closure executed in-place, zero heap allocation
grid.for_each_in_radius(pos, range, |n_entity, n_pos| {
    // Process each neighbor directly — no Vec, no allocation
});
```

The closure is inlined by the compiler. The only data structure is the spatial grid
itself, which persists across frames.

## 4. Fixed-Delta Time Consistency

All interactions use `dt = 1.0 / 60.0` (fixed timestep) regardless of actual
frame time. This ensures:

1. **Deterministic simulation** — same inputs → same outputs
2. **Rate independence** — stat changes are per-second rates
3. **ML training stability** — reward signals are consistent

```rust
let dt = 1.0 / 60.0;
victim_stats.0[stat_index] += delta * dt;  // Per-second rate × time step
```

## 5. Self-Interaction Prevention

An entity MUST NOT interact with itself:
```rust
if attacker_entity == victim_entity { return; }
```

Without this check, each entity applies its own interaction rule to itself every
tick, creating explosive stat growth.

## 6. Rule-Based Architecture

Interactions are config-driven, not hardcoded:

```rust
pub struct InteractionRule {
    pub attacker_faction: u32,    // Who attacks
    pub victim_faction: u32,      // Who gets affected
    pub stat_index: usize,        // Which stat (e.g., 0 = HP)
    pub delta: f32,               // Change per second (+heal / -damage)
    pub range: f32,               // Proximity trigger (world units)
}
```

This enables scenario hot-swapping without recompilation:
```json
{ "attacker_faction": 0, "victim_faction": 1, "stat_index": 0, "delta": -5.0, "range": 15.0 }
```

## 7. Performance Summary

| Metric | Value |
|:---|:---|
| Query pattern | 2 disjoint queries (read + write) |
| Allocation per tick | **Zero** (closure-based spatial query) |
| Time complexity | O(N × K) where K = avg neighbors |
| Determinism | Fixed `dt = 1/60` |
