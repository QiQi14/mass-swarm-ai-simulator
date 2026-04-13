# Rule: ECS Directive Safety Patterns

**Category:** Architecture, ECS, Safety

## Context
During Phase 3 planning, four critical vulnerabilities were identified in the directive executor pattern that would cause entity vaporization, wall clipping, ghost state leakage, and f32 sort panics.

## Strict Directive

### 1. VAPORIZATION GUARD: Consume-Once Directives
When reading a directive from a Resource in a system that runs at 60Hz:
- **❌ Anti-pattern:** `let Some(ref directive) = res.directive else { return; };`
  - `ref` borrows without consuming. Same directive re-executes every frame.
  - SplitFaction(30%) fires 30+ times in 0.5s → army vaporized.
- **✅ Best Practice:** `let Some(directive) = res.directive.take() else { return; };`
  - `take()` moves the value out, replacing with None. Executes exactly once.

### 2. MOSES EFFECT GUARD: Wall Immutability
When overlaying cost modifiers onto a terrain cost map:
- **❌ Anti-pattern:** `let adjusted = (cost_map[idx] as f32 + modifier).clamp(1.0, MAX);`
  - A negative modifier (-500) on a wall (u16::MAX=65535) → 65035 → traversable!
- **✅ Best Practice:** `if cost_map[idx] == u16::MAX { continue; }` before any modification.
  - Also clamp upper bound to `u16::MAX - 1` to prevent accidental wall creation.

### 3. GHOST STATE CLEANUP: Deep Purge on Entity Reorganization
When dissolving a faction/group (MergeFaction, RemoveFaction):
- **❌ Anti-pattern:** Only clean the primary registries (nav_rules, sub_factions).
- **✅ Best Practice:** Purge ALL registries: zones, speed_buffs, aggro_masks, nav_rules, sub_factions.

### 4. f32 SORT SAFETY: Use Quickselect with partial_cmp
When sorting/selecting entities by distance (f32):
- **❌ Anti-pattern:** `candidates.sort_by(|a, b| a.dist.total_cmp(&b.dist));` — O(N log N), wasteful.
- **❌ Anti-pattern:** `candidates.sort();` — Won't compile (f32 doesn't impl Ord).
- **✅ Best Practice:** `candidates.select_nth_unstable_by(k, |a, b| a.1.partial_cmp(&b.1).unwrap_or(Ordering::Equal));`
  - O(N) average, handles NaN gracefully, only partitions (doesn't fully sort).

### 5. DATA ISOLATION: Physics vs NN Concerns
- **❌ Anti-pattern:** Rust packs density maps into fixed NN channels (e.g., 4-channel tensor).
- **✅ Best Practice:** Rust exports raw `HashMap<u32, Vec<f32>>`. Python's vectorizer packs into channels.
  - Channel count, packing order, and normalization are NN architecture decisions → Python's job.
