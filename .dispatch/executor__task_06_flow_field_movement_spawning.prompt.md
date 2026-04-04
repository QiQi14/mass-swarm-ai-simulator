# AGENT ROLE: EXECUTION SPECIALIST

You are an **Execution Specialist** in a multi-agent DAG workflow.
You have been assigned ONE specific task. You implement it with surgical precision.

---

## Your Assignment

| Field   | Value |
|---------|-------|
| Task ID | `task_06_flow_field_movement_spawning` |
| Feature | phase_2_universal_core_algorithms |
| Tier    | standard |

---

## ⛔ MANDATORY PROCESS — ALL TIERS (DO NOT SKIP)

> **These rules apply to EVERY executor, regardless of tier. Violating them
> causes an automatic QA FAIL and project BLOCK.**

### Rule 1: Scope Isolation
- You may ONLY create or modify files listed in `Target_Files` in your Task Brief.
- If a file must be changed but is NOT in `Target_Files`, **STOP and report the gap** — do NOT modify it.
- NEVER edit `task_state.json`, `implementation_plan.md`, or any file outside your scope.

### Rule 2: Changelog (Handoff Documentation)
After ALL code is written and BEFORE calling `./task_tool.sh done`, you MUST:

1. **Create** `tasks_pending/task_06_flow_field_movement_spawning_changelog.md`
2. **Include in the changelog:**
   - **Touched Files:** A bulleted list of every file you created or modified.
   - **Contract Fulfillment:** Brief confirmation of the interfaces/DTOs you implemented.
   - **Deviations/Notes:** Any edge cases you handled or deviations from the brief the QA agent should verify.
3. **Then and only then** run:
   ```bash
   ./task_tool.sh done task_06_flow_field_movement_spawning
   ```

> **⚠️ Calling `./task_tool.sh done` without creating the changelog file is FORBIDDEN.**

### Rule 3: No Placeholders
- Do not use `// TODO`, `/* FIXME */`, or stub implementations.
- Output fully functional, production-ready code.

---

## Context Loading (Tier-Dependent)

**If your tier is `basic`:**
- Skip all external file reading. Your Task Brief below IS your complete instruction.
- Implement the code exactly as specified in the Task Brief.
- Follow the MANDATORY PROCESS rules above (changelog + scope), then halt.

**If your tier is `standard` or `advanced`:**
1. Read `.agents/context.md` — Thin index pointing to context sub-files
2. Load ONLY the `context/*` sub-files listed in your `Context_Bindings` below
3. Scan `.agents/knowledge/` — Lessons from previous sessions relevant to your task
4. Read `.agents/workflows/execution-lifecycle.md` — Your 4-step execution loop
5. Read `.agents/rules/execution-boundary.md` — Scope and contract constraints

- `./.agents/context/conventions.md`
- `./.agents/context/architecture.md`
- `./.agents/skills/rust-code-standards/SKILL.md`

---

## Task Brief

---
Task_ID: task_06_flow_field_movement_spawning
Execution_Phase: Phase 2 (Parallel)
Model_Tier: standard
Target_Files:
  - micro-core/src/components/flow_field_follower.rs
  - micro-core/src/components/mod.rs
  - micro-core/src/systems/movement.rs
  - micro-core/src/systems/flow_field_update.rs
  - micro-core/src/systems/spawning.rs
Dependencies:
  - task_02_spatial_hash_grid
  - task_03_flow_field_registry
  - task_04_rule_resources
Context_Bindings:
  - context/conventions
  - context/architecture
  - skills/rust-code-standards
---

# STRICT INSTRUCTIONS

Create the FlowFieldFollower component, the flow field update system, modify the movement system for flow field integration, and add wave spawning.

**Read `implementation_plan.md` Contracts 4, 5, 7, 9, and 10.**

**DO NOT modify `systems/mod.rs` — Task 08 handles wiring.**

## 1. Create `micro-core/src/components/flow_field_follower.rs` [NEW]

```rust
use bevy::prelude::*;

/// Marker component. Entities with this opt into flow field navigation.
/// The movement system reads NavigationRuleSet to determine which flow field to follow.
#[derive(Component, Debug, Clone, Default)]
pub struct FlowFieldFollower;
```

Unit test: can be instantiated with `FlowFieldFollower::default()`.

## 2. Update `micro-core/src/components/mod.rs` [MODIFY]

Add `pub mod flow_field_follower;` and `pub use flow_field_follower::FlowFieldFollower;`.

## 3. Create `micro-core/src/systems/flow_field_update.rs` [NEW]

```rust
pub fn flow_field_update_system(
    mut registry: ResMut<FlowFieldRegistry>,
    nav_rules: Res<NavigationRuleSet>,
    query: Query<(&Position, &FactionId)>,
    config: Res<SimulationConfig>,
    tick: Res<TickCounter>,
)
```

Algorithm:
1. Only run every `config.flow_field_update_interval` ticks (check `tick.tick % interval == 0`). Skip tick 0.
2. Collect unique target faction IDs from `nav_rules.rules` (deduplicate).
3. For each unique target faction:
   - Gather all entity positions where `faction_id.0 == target_faction` → `Vec<Vec2>`.
   - If no entities found for this faction, skip (don't create empty field).
   - Create or reuse a `FlowField::new(width, height, config.flow_field_cell_size)` where width/height are derived from `config.world_width / config.flow_field_cell_size`.
   - Call `field.calculate(&goals, &[])` (no obstacles yet).
   - Insert into `registry.fields`.
4. Remove registry entries for faction IDs that are no longer targets in `nav_rules`.

## 4. Modify `micro-core/src/systems/movement.rs` [MODIFY]

Update `movement_system` signature to add:
- `registry: Res<FlowFieldRegistry>`
- `nav_rules: Res<NavigationRuleSet>`
- `behavior_mode: Res<FactionBehaviorMode>`
- `&FactionId` and `Option<&FlowFieldFollower>` to the entity query.

**Movement logic per entity:**
1. If entity HAS `FlowFieldFollower` AND faction is NOT in `behavior_mode.static_factions`:
   - Look up entity's `FactionId` in `nav_rules.rules` to find its `target_faction`.
   - Look up `target_faction` in `registry.fields`.
   - If a field exists: `let dir = field.sample(Vec2::new(pos.x, pos.y))`. If `dir != Vec2::ZERO`, override velocity: `vel.dx = dir.x * speed; vel.dy = dir.y * speed` where `speed = (vel.dx*vel.dx + vel.dy*vel.dy).sqrt()` (preserve original speed magnitude). If speed is 0, use a default speed of 1.0.
   - If no matching rule or field, keep current velocity unchanged.
2. If entity does NOT have `FlowFieldFollower` OR faction IS in `static_factions`: keep existing velocity unchanged (random drift from spawn).

**Boundary handling:** Replace any wrap-around logic with clamping:
```rust
pos.x = pos.x.clamp(0.0, config.world_width);
pos.y = pos.y.clamp(0.0, config.world_height);
```

## 5. Modify `micro-core/src/systems/spawning.rs` [MODIFY]

Add `wave_spawn_system`:

```rust
pub fn wave_spawn_system(
    tick: Res<TickCounter>,
    config: Res<SimulationConfig>,
    mut commands: Commands,
    mut next_id: ResMut<NextEntityId>,
)
```

Algorithm:
1. Only run every `config.wave_spawn_interval` ticks. Skip tick 0.
2. For each of `config.wave_spawn_count` entities:
   - Pick a random edge position: randomly select one of 4 edges, then random position along that edge.
   - Spawn with: `EntityId`, `Position`, `Velocity` (random direction, magnitude 1.0), `FactionId(config.wave_spawn_faction)`, `StatBlock::with_defaults(&config.wave_spawn_stat_defaults)`, `FlowFieldFollower`.
   - Increment `next_id.0`.

Also update `initial_spawn_system` to add `FlowFieldFollower` to faction 0 entities (those that match `wave_spawn_faction`).

## 6. Unit Tests

- **FlowFieldFollower entity moves toward goal:** Entity at (0,0) with FlowFieldFollower, flow field pointing right → velocity becomes (speed, 0).
- **Static faction ignores flow field:** Entity with FlowFieldFollower but faction in `static_factions` → velocity unchanged.
- **No matching rule:** Entity with FlowFieldFollower but no matching navigation rule → velocity unchanged.
- **No FlowFieldFollower:** Entity without marker → velocity unchanged, uses existing drift.
- **Boundary clamping:** Entity at world edge with velocity pointing outward → position clamps to boundary.
- **Wave spawn count:** After `wave_spawn_interval` ticks, exactly `wave_spawn_count` entities spawned.
- **Wave spawn edge position:** Spawned entities have position on a world edge (x=0 or x=world_width or y=0 or y=world_height).
- **Flow field update deduplication:** Two nav rules targeting same faction → only one flow field calculated.

---

# Verification_Strategy
Test_Type: unit
Test_Stack: cargo test
Acceptance_Criteria:
  - "FlowFieldFollower entities navigate toward correct target per NavigationRuleSet"
  - "Entities in static_factions use random drift even with FlowFieldFollower"
  - "Non-follower entities retain original velocity"
  - "Position clamps to world boundaries (no wrapping)"
  - "wave_spawn_system spawns correct count every N ticks"
  - "Multiple factions targeting same faction share one flow field calculation"
Suggested_Test_Commands:
  - "cd micro-core && cargo test movement"
  - "cd micro-core && cargo test spawning"
  - "cd micro-core && cargo test flow_field_update"

---

## Shared Contracts

# Phase 2 — Universal Core Algorithms (Context-Agnostic Architecture)

**TDD Reference:** CASE_STUDY.md §2.2, ROADMAP.md Phase 2
**Depends On:** Phase 1 (complete ✅)
**Architectural Pivot:** Universal Brain System — context-agnostic Micro-Core

---

## Architectural Vision: The Black-Box Universal Core

Phase 2 adopts the **Universal Brain System** thesis: the Rust Micro-Core and Python Macro-Brain must be **semantically blind** — they handle mathematical quantities, spatial vectors, numeric identifiers, and anonymous data blocks. They never know whether they're running a swarm RTS, an Action RPG's Nemesis-style system, an FPS combat arena, or a real-world drone swarm.

### Validated Principles

| Principle | Status | Notes |
|-----------|--------|-------|
| Context-agnostic core | ✅ Adopted | Core never knows "health" or "team" — only stat indices and faction IDs |
| Dynamic Payload Array (`Stats: [f32; N]`) | ✅ Adopted with refinement | Fixed `[f32; 8]` array per entity — cache-friendly, zero allocation |
| 4-Layer Architecture | ✅ Adopted | Dumb Client → Adapter → Universal Core → Macro-Brain |
| FlatBuffers/Protobuf | ⏸️ Deferred to Phase 4 | JSON remains for Phases 2–3 (debuggability). Binary serialization is a throughput optimization, not an algorithmic concern |
| Config-driven rule sets | ✅ Adopted | Interaction rules, removal rules loaded from config — zero hardcoded game logic |

### Design Refinement: ECS × Stats Array

The analysis proposes `Stats: [f32; 8]` as a flat array. This is correct but needs ECS-friendly refinement:

```
❌ Anti-pattern: Put EVERYTHING in Stats array (position, velocity, faction)
   → Loses Bevy query efficiency, can't filter "entities at position X"

✅ Best practice: Keep spatial components (Position, Velocity) as native ECS components.
   Use StatBlock ONLY for game-logic attributes (health, mana, fuel, damage, etc.)
   Use FactionId as a separate queryable component (critical for spatial queries)
```

**Why?** `Position` and `Velocity` are already context-agnostic (pure math). Merging them into a generic array would destroy Bevy's `Changed<Position>` tracking and `With<FactionId>` filtering — both critical for 10K+ entity performance.

### What Changes from Phase 1

| Phase 1 Concept | Phase 2 Replacement | Reason |
|-----------------|---------------------|--------|
| `Team` enum (`Swarm`/`Defender`) | `FactionId(u32)` | Numeric ID = context-agnostic. Adapter maps ID → name |
| No health/stats | `StatBlock([f32; 8])` | Anonymous stat array. Adapter maps index → meaning |
| Hardcoded "combat" | `InteractionRuleSet` config | Rules define what happens when factions proximity-interact |
| Hardcoded "death" | `RemovalRuleSet` config | Rules define when entities are removed (stat thresholds) |
| `Team::Swarm` string in IPC | `faction_id: 0` integer in IPC | Protocol becomes numeric, adapter adds labels |

### Adapter Layer in Phase 2

The formal Adapter layer (Layer 2 in the user's analysis) is a Phase 5 concern (engine integration). In Phase 2, the **Debug Visualizer acts as the adapter** — it contains a small `ADAPTER_CONFIG` object that maps:

```javascript
// debug-visualizer/visualizer.js — Adapter Config
const ADAPTER_CONFIG = {
    factions: {
        0: { name: "Swarm",    color: "#ff3b30" },
        1: { name: "Defender", color: "#0a84ff" },
    },
    stats: {
        0: { name: "Health", display: "bar", color_low: "#ff3b30", color_high: "#30d158" },
    },
};
```

This proves the adapter concept without building a separate layer.

---

## User Review Required

> [!IMPORTANT]
> **Breaking Refactor — `Team` → `FactionId`:** All Phase 1 code referencing `Team::Swarm`/`Team::Defender` will be refactored to `FactionId(0)`/`FactionId(1)`. This is a coordinated refactor touching 10 files (components, systems, bridges, visualizer). The refactor must run first (Phase 0) before any new features.

> [!IMPORTANT]
> **StatBlock Size:** Proposing `MAX_STATS = 8` (32 bytes per entity). For 10K entities = 320KB total. Is 8 slots sufficient? Can be changed at compile time, but increasing it later requires recompilation.

> [!IMPORTANT]
> **Movement Change:** Replacing world-edge wrapping with boundary clamping. Flow field navigation is incompatible with toroidal topology (entities chasing a target would wrap to the opposite side).

> [!WARNING]
> **FlatBuffers Deferral:** The analysis recommends "absolutely no JSON" for 10K+. I recommend keeping JSON for Phase 2–3 because: (1) algorithm development needs debuggable messages in browser DevTools; (2) the bottleneck is CPU (algorithms), not I/O; (3) ROADMAP already plans binary serialization for Phase 4. Switching to FlatBuffers now adds schema compilation complexity without algorithmic benefit.

> [!IMPORTANT]
> **ZMQ Protocol also refactored:** The `zmq_protocol.rs` currently uses `team: String` and game-specific `SummarySnapshot` fields (`swarm_count`, `defender_count`, `avg_swarm_health`). These must be made context-agnostic too: `faction_id: u32` and per-faction summary arrays.

---

## Shared Contracts

### Contract 1: `FactionId` Component (replaces `Team`)

```rust
// File: micro-core/src/components/faction.rs (replaces team.rs)
use bevy::prelude::*;
use serde::{Deserialize, Serialize};

/// Numeric faction identifier. Context-agnostic — the adapter maps ID to meaning.
/// Example: 0 = "swarm", 1 = "defender" (in the swarm demo adapter config).
#[derive(Component, Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct FactionId(pub u32);

impl std::fmt::Display for FactionId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "faction_{}", self.0)
    }
}
```

### Contract 2: `StatBlock` Component (anonymous stat array)

```rust
// File: micro-core/src/components/stat_block.rs
use bevy::prelude::*;
use serde::{Deserialize, Serialize};

/// Maximum number of stats per entity. Compile-time constant.
pub const MAX_STATS: usize = 8;

/// Anonymous stat array. The Micro-Core never knows what each index means.
/// The Adapter layer defines the mapping (e.g., index 0 = "health", index 1 = "mana").
///
/// Default: all zeros. Initialize via `StatBlock::with_defaults(&[...])`.
#[derive(Component, Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct StatBlock(pub [f32; MAX_STATS]);

impl Default for StatBlock {
    fn default() -> Self {
        Self([0.0; MAX_STATS])
    }
}

impl StatBlock {
    /// Create a StatBlock with specified (index, value) pairs.
    /// Unspecified indices default to 0.0.
    pub fn with_defaults(pairs: &[(usize, f32)]) -> Self {
        let mut block = Self::default();
        for &(idx, val) in pairs {
            if idx < MAX_STATS {
                block.0[idx] = val;
            }
        }
        block
    }
}
```

### Contract 3: `SpatialHashGrid` Resource

```rust
// File: micro-core/src/spatial/hash_grid.rs
use bevy::prelude::*;
use std::collections::HashMap;

/// Spatial hash grid for O(1) proximity lookups.
/// Rebuilt every tick by `update_spatial_grid_system`.
#[derive(Resource, Debug)]
pub struct SpatialHashGrid {
    pub cell_size: f32,
    grid: HashMap<IVec2, Vec<(Entity, Vec2)>>,
}

impl SpatialHashGrid {
    pub fn new(cell_size: f32) -> Self;
    pub fn rebuild(&mut self, entities: &[(Entity, Vec2)]);
    pub fn query_radius(&self, center: Vec2, radius: f32) -> Vec<(Entity, Vec2)>;
    fn world_to_cell(&self, pos: Vec2) -> IVec2;
}
```

### Contract 4: `FlowField` + `FlowFieldRegistry` (N-Faction Pathfinding)

```rust
// File: micro-core/src/pathfinding/flow_field.rs
use bevy::prelude::*;
use std::collections::HashMap;

/// Pre-computed vector flow field for mass pathfinding.
/// Each cell contains a normalized direction vector toward the nearest goal.
/// NOT a Resource — owned by FlowFieldRegistry.
#[derive(Debug)]
pub struct FlowField {
    pub width: u32,
    pub height: u32,
    pub cell_size: f32,
    /// Flat array of direction vectors, indexed as [y * width + x]
    pub directions: Vec<Vec2>,
    /// Integration field costs (for debug overlay)
    pub costs: Vec<u16>,
}

impl FlowField {
    pub fn new(width: u32, height: u32, cell_size: f32) -> Self;
    pub fn calculate(&mut self, goals: &[Vec2], obstacles: &[IVec2]);
    pub fn sample(&self, world_pos: Vec2) -> Vec2;
}

/// Registry of flow fields, keyed by target faction ID.
/// Each field converges on entities of that faction.
/// Supports N-faction scenarios (e.g., Wolves→Sheep, Sheep→Grass).
/// If 5 different factions target faction 1, the field for faction 1
/// is only calculated ONCE — deduplication is automatic.
#[derive(Resource, Debug, Default)]
pub struct FlowFieldRegistry {
    pub fields: HashMap<u32, FlowField>,
}
```

### Contract 5: Interaction, Removal & Navigation Rules (Config-Driven)

```rust
// File: micro-core/src/rules/interaction.rs

/// Defines what happens when entities of different factions are in proximity.
/// Loaded from config — zero hardcoded game logic.
#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct InteractionRuleSet {
    pub rules: Vec<InteractionRule>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InteractionRule {
    /// Faction ID of the source entity
    pub source_faction: u32,
    /// Faction ID of the target entity
    pub target_faction: u32,
    /// Range in world units at which this interaction activates
    pub range: f32,
    /// Effects to apply to TARGET entity's StatBlock
    pub effects: Vec<StatEffect>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StatEffect {
    /// Index into target's StatBlock
    pub stat_index: usize,
    /// Change per second (positive = buff, negative = debuff). Normalized to ticks internally.
    pub delta_per_second: f32,
}
```

```rust
// File: micro-core/src/rules/removal.rs

/// Defines when entities are removed from simulation.
#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct RemovalRuleSet {
    pub rules: Vec<RemovalRule>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RemovalRule {
    /// Which stat index to monitor
    pub stat_index: usize,
    /// Threshold value
    pub threshold: f32,
    /// Removal condition
    pub condition: RemovalCondition,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RemovalCondition {
    /// Remove when stat <= threshold (e.g., "health" drops to 0)
    LessOrEqual,
    /// Remove when stat >= threshold (e.g., "corruption" reaches 100)
    GreaterOrEqual,
}
```

```rust
// File: micro-core/src/rules/navigation.rs

/// Defines which factions navigate toward which other factions.
/// This is the N-faction navigation matrix — fully config-driven.
///
/// The flow_field_update_system reads this to decide:
/// 1. Which target factions need flow fields calculated.
/// 2. Which follower factions use which flow field.
///
/// Runtime-modifiable: the Macro-Brain can send IPC commands to
/// update this rule set mid-simulation (e.g., redirect swarm).
#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct NavigationRuleSet {
    pub rules: Vec<NavigationRule>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NavigationRule {
    /// Faction ID of entities that will follow the flow field
    pub follower_faction: u32,
    /// Faction ID of entities used as goals (flow field converges on them)
    pub target_faction: u32,
}
```

**Default "Swarm Demo" Config:**
```rust
// This is what the adapter config defines. The core just processes numbers.
InteractionRuleSet {
    rules: vec![
        InteractionRule {
            source_faction: 0,     // (swarm in adapter)
            target_faction: 1,     // (defender in adapter)
            range: 15.0,
            effects: vec![StatEffect { stat_index: 0, delta_per_second: -10.0 }],
        },
        InteractionRule {
            source_faction: 1,     // (defender in adapter)
            target_faction: 0,     // (swarm in adapter)
            range: 15.0,
            effects: vec![StatEffect { stat_index: 0, delta_per_second: -20.0 }],
        },
    ],
}
RemovalRuleSet {
    rules: vec![
        RemovalRule {
            stat_index: 0,        // (health in adapter)
            threshold: 0.0,
            condition: RemovalCondition::LessOrEqual,
        },
    ],
}
NavigationRuleSet {
    rules: vec![
        NavigationRule {
            follower_faction: 0,   // swarm follows flow field toward...
            target_faction: 1,     // ...defenders
        },
    ],
}
```

This same core handles ANY genre:
- **RTS 3-way:** `[{0→1}, {1→2}, {2→0}]` — triangle of pursuit
- **Ecosystem:** `[{0→1 (wolves→sheep)}, {1→2 (sheep→grass)}]`
- **RPG:** faction 0 heals faction 0 → `effects: [(0, +5.0)]`
- **Racing:** stat[1] = fuel, removal when `stat[1] <= 0.0`
- **Drones:** faction 0 converges on faction 1 (waypoints as entities)
- **Dynamic retargeting:** Macro-Brain sends IPC to change `target_faction` mid-game

### Contract 6: `RemovalEvents` Resource

```rust
/// Accumulates entity IDs removed this tick for WS broadcast.
#[derive(Resource, Debug, Default)]
pub struct RemovalEvents {
    pub removed_ids: Vec<u32>,
}
```

### Contract 10: `FactionBehaviorMode` Resource

```rust
// File: micro-core/src/rules/behavior.rs
use bevy::prelude::*;
use std::collections::HashSet;

/// Controls per-faction behavior mode at runtime.
/// Factions in `static_factions` use random drift (Phase 1 behavior).
/// All other factions follow NavigationRuleSet flow fields (brain-driven).
///
/// Toggleable via Debug Visualizer: `set_faction_mode` WS command.
/// This enables testing scenarios like:
/// - Both factions static (baseline)
/// - One faction brain-driven, other static (flow field validation)
/// - Both brain-driven (multi-brain combat testing in Phase 3)
#[derive(Resource, Debug, Clone)]
pub struct FactionBehaviorMode {
    /// Set of faction IDs currently in "static" mode (random drift).
    /// Factions NOT in this set follow flow fields.
    pub static_factions: HashSet<u32>,
}

impl Default for FactionBehaviorMode {
    fn default() -> Self {
        let mut static_factions = HashSet::new();
        static_factions.insert(1); // Defenders start in static mode (swarm demo default)
        Self { static_factions }
    }
}
```

### Contract 7: System Signatures

| System | Signature | Schedule | Run Condition |
|--------|-----------|----------|---------------|
| `update_spatial_grid_system` | `(ResMut<SpatialHashGrid>, Query<(Entity, &Position)>)` | `Update` | Always (runs before interaction) |
| `flow_field_update_system` | `(ResMut<FlowFieldRegistry>, Res<NavigationRuleSet>, Query<(&Position, &FactionId)>, Res<SimulationConfig>)` | `Update` | `SimState::Running`, every N ticks |
| `interaction_system` | `(Res<SpatialHashGrid>, Res<InteractionRuleSet>, Query<(Entity, &Position, &mut StatBlock, &FactionId)>)` | `Update` | `SimState::Running`, after spatial grid |
| `removal_system` | `(Res<RemovalRuleSet>, Query<(Entity, &EntityId, &StatBlock)>, Cmds, ResMut<RemovalEvents>)` | `Update` | After interaction |
| `movement_system` (modified) | `+Res<FlowFieldRegistry>, +Res<NavigationRuleSet>, +Res<FactionBehaviorMode>, +Option<&FlowFieldFollower>` | `Update` | `SimState::Running` (unchanged) |
| `wave_spawn_system` | `(Res<TickCounter>, Res<SimulationConfig>, Cmds, ResMut<NextEntityId>)` | `Update` | `SimState::Running` |

### Contract 8: IPC Protocol Changes

**WS EntityState** (Rust → Browser):
```json
{
    "id": 42,
    "x": 150.3,
    "y": 201.0,
    "dx": 0.5,
    "dy": -0.3,
    "faction_id": 0,
    "stats": [0.85, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
}
```

**WS SyncDelta** extended with `removed`:
```json
{
    "type": "SyncDelta",
    "tick": 1234,
    "moved": [ ... ],
    "removed": [42, 99, 107]
}
```

**WS Command — `set_faction_mode`** (Browser → Rust):
```json
{
    "type": "command",
    "cmd": "set_faction_mode",
    "params": { "faction_id": 1, "mode": "brain" }
}
```
`mode` values: `"static"` (random drift) | `"brain"` (flow field / Macro-Brain driven).
Updates `FactionBehaviorMode` resource at runtime.

**ZMQ EntitySnapshot** (Rust → Python):
```json
{
    "id": 42,
    "x": 150.3,
    "y": 201.0,
    "faction_id": 0,
    "stats": [0.85, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
}
```

**ZMQ SummarySnapshot** — made generic:
```json
{
    "faction_counts": { "0": 5000, "1": 200 },
    "faction_avg_stats": {
        "0": [0.72, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "1": [0.91, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    }
}
```

### Contract 9: SimulationConfig Extensions

```rust
// Added to config.rs:
pub flow_field_cell_size: f32,       // default: 20.0 world units
pub flow_field_update_interval: u64, // default: 30 ticks
// NOTE: flow_field_target_faction / flow_field_follower_faction REMOVED.
// Navigation targeting is now fully defined by NavigationRuleSet (Contract 5).
pub wave_spawn_interval: u64,        // default: 300 ticks (5 seconds)
pub wave_spawn_count: u32,           // default: 50 entities per wave
pub wave_spawn_faction: u32,         // default: 0
pub wave_spawn_stat_defaults: Vec<(usize, f32)>, // default: [(0, 1.0)] — stat[0] = 1.0
```

---

## DAG Execution Phases

```mermaid
graph LR
    subgraph "Phase 0 — Refactor (Sequential)"
        T01["Task 01<br/>Context-Agnostic Refactor<br/>Team→FactionId + StatBlock"]
    end

    subgraph "Phase 1 — Foundation (Parallel)"
        T02["Task 02<br/>SpatialHashGrid"]
        T03["Task 03<br/>FlowField<br/>+ FlowFieldRegistry"]
        T04["Task 04<br/>Interaction, Removal<br/>& Navigation Rules"]
    end

    subgraph "Phase 2 — Core Systems (Parallel)"
        T05["Task 05<br/>Interaction System<br/>+ Removal System"]
        T06["Task 06<br/>FlowFieldFollower<br/>+ Movement + Spawning"]
    end

    subgraph "Phase 3 — Visualization"
        T07["Task 07<br/>IPC Extensions<br/>+ Visualizer Upgrades"]
    end

    subgraph "Phase 4 — Integration"
        T08["Task 08<br/>Integration Wiring<br/>+ 10K Stress Test"]
    end

    T01 --> T02
    T01 --> T03
    T01 --> T04
    T02 --> T05
    T04 --> T05
    T02 --> T06
    T03 --> T06
    T05 --> T07
    T06 --> T07
    T07 --> T08
```

---

## Task Summaries

---

### Task 01 — Context-Agnostic Refactor
**Phase:** 0 (Sequential — must complete before all others) | **Tier:** `advanced` | **Domain:** Cross-cutting refactor

| Property | Value |
|----------|-------|
| **Target Files** | `components/faction.rs` [NEW], `components/stat_block.rs` [NEW], `components/team.rs` [DELETE], `components/mod.rs` [MODIFY], `systems/spawning.rs` [MODIFY], `systems/ws_sync.rs` [MODIFY], `systems/ws_command.rs` [MODIFY], `bridges/ws_protocol.rs` [MODIFY], `bridges/zmq_protocol.rs` [MODIFY], `bridges/zmq_bridge/systems.rs` [MODIFY], `debug-visualizer/visualizer.js` [MODIFY] |
| **Dependencies** | None |
| **Context Bindings** | `context/conventions`, `context/architecture`, `context/ipc-protocol`, `skills/rust-code-standards` |

**Strict Instructions:**

1. **Create `components/faction.rs`** — `FactionId(u32)` per Contract 1. Full serde derives, Display impl, unit tests.
2. **Create `components/stat_block.rs`** — `StatBlock([f32; MAX_STATS])` per Contract 2. `MAX_STATS = 8`. Default, `with_defaults()`, unit tests.
3. **Delete `components/team.rs`** — Remove the file entirely.
4. **Update `components/mod.rs`** — Remove `pub mod team` / `pub use Team`. Add `pub mod faction` / `pub mod stat_block` / re-exports `FactionId`, `StatBlock`, `MAX_STATS`.
5. **Update `systems/spawning.rs`** — Replace `Team` import with `FactionId` + `StatBlock`. Replace `Team::Swarm`/`Defender` with `FactionId(0)`/`FactionId(1)`. Add `StatBlock::with_defaults(&[(0, 1.0)])` to entity bundles (stat[0] = initial "health").
6. **Update `systems/ws_sync.rs`** — Replace `Team` import with `FactionId` + `StatBlock`. Query now includes `&StatBlock`. Serialize `faction_id: u32` and `stats: [f32; 8]` into `EntityState`.
7. **Update `systems/ws_command.rs`** — Replace `Team` import with `FactionId`. `spawn_wave` parses `faction_id: u32` from params (default 0). `kill_all` matches by `FactionId` instead of `Team`. Add `StatBlock::with_defaults(&[(0, 1.0)])` to spawned entities.
8. **Update `bridges/ws_protocol.rs`** — Replace `team: Team` with `faction_id: u32` and `stats: Vec<f32>` in `EntityState`. Remove `use crate::components::team::Team`.
9. **Update `bridges/zmq_protocol.rs`** — Replace `team: String` with `faction_id: u32` and `stats: Vec<f32>` in `EntitySnapshot`. Replace `SummarySnapshot` fields with generic `faction_counts: HashMap<u32, u32>` and `faction_avg_stats: HashMap<u32, Vec<f32>>`.
10. **Update `bridges/zmq_bridge/systems.rs`** — Replace `Team` import/usage with `FactionId`. Replace `Team::Swarm`/`Defender` match arms with `FactionId` numeric checks. Build generic summary by iterating factions dynamically.
11. **Update `debug-visualizer/visualizer.js`** — Add `ADAPTER_CONFIG` at top (faction→color, stat→display mapping). Replace `ent.team === "swarm"` with `ent.faction_id === 0` using adapter config. Replace `team: "swarm"` in `sendCommand` with `faction_id: 0`. Support `stats` array in entity data; render stat[0] as health bar if configured.

**Verification Strategy:**
```yaml
Verification_Strategy:
  Test_Type: unit + integration
  Test_Stack: cargo test (Rust), manual browser validation (JS)
  Acceptance_Criteria:
    - "cargo test passes with all existing tests updated for FactionId/StatBlock"
    - "cargo clippy -- -D warnings is clean"
    - "Debug Visualizer renders entities with correct colors based on faction_id"
    - "spawn_wave command works with faction_id parameter"
    - "kill_all command works with faction_id parameter"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test"
    - "cd micro-core && cargo clippy -- -D warnings"
  Manual_Steps:
    - "Run micro-core, open debug-visualizer/index.html"
    - "Verify entities render as red (faction 0) and blue (faction 1)"
    - "Click canvas to spawn entities — verify they appear correctly"
```

---

### Task 02 — Spatial Hash Grid
**Phase:** 1 (Parallel) | **Tier:** `standard` | **Domain:** Data Structure

| Property | Value |
|----------|-------|
| **Target Files** | `spatial/mod.rs` [NEW], `spatial/hash_grid.rs` [NEW], `lib.rs` [MODIFY] |
| **Dependencies** | Task 01 (only needs `Position` component — unchanged, no real dependency) |
| **Context Bindings** | `context/conventions`, `context/architecture`, `skills/rust-code-standards` |

**Strict Instructions:**

1. **Create `spatial/mod.rs`** — Re-export `hash_grid::SpatialHashGrid` and `hash_grid::update_spatial_grid_system`.
2. **Create `spatial/hash_grid.rs`** — Implement per Contract 3:
   - `SpatialHashGrid` resource with `HashMap<IVec2, Vec<(Entity, Vec2)>>`.
   - `new(cell_size: f32)` constructor.
   - `rebuild(&mut self, entities: &[(Entity, Vec2)])` — clear grid, insert all entities into cells.
   - `query_radius(&self, center: Vec2, radius: f32) -> Vec<(Entity, Vec2)>` — check 9-cell neighborhood, filter by Euclidean distance.
   - `world_to_cell(&self, pos: Vec2) -> IVec2` — floor division.
   - `update_spatial_grid_system` — Bevy system that calls `rebuild()` with all entity positions.
3. **Update `lib.rs`** — Add `pub mod spatial`.
4. **Unit tests** — empty grid returns empty, single entity found in correct cell, multi-cell radius query, exact boundary behavior, 1000-entity stress test.

**Verification Strategy:**
```yaml
Verification_Strategy:
  Test_Type: unit
  Test_Stack: cargo test
  Acceptance_Criteria:
    - "query_radius returns correct entities within radius"
    - "query_radius excludes entities outside radius"
    - "rebuild correctly handles entities at cell boundaries"
    - "1000-entity rebuild completes in under 1ms (debug build)"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test spatial"
```

---

### Task 03 — Flow Field + Flow Field Registry
**Phase:** 1 (Parallel) | **Tier:** `standard` | **Domain:** Algorithm

| Property | Value |
|----------|-------|
| **Target Files** | `pathfinding/mod.rs` [NEW], `pathfinding/flow_field.rs` [NEW], `lib.rs` [MODIFY] |
| **Dependencies** | None |
| **Context Bindings** | `context/conventions`, `context/architecture`, `skills/rust-code-standards` |

**Strict Instructions:**

1. **Create `pathfinding/mod.rs`** — Re-export `flow_field::FlowField` and `flow_field::FlowFieldRegistry`.
2. **Create `pathfinding/flow_field.rs`** — Implement per Contract 4:
   - `FlowField` struct (NOT a Resource — owned by registry) with flat `Vec<Vec2>` for directions and `Vec<u16>` for costs.
   - `new(width, height, cell_size)` — allocate zeroed vectors.
   - `calculate(&mut self, goals: &[Vec2], obstacles: &[IVec2])`:
     - Initialize all costs to `u16::MAX`.
     - Set goal cells to cost 0, add to BFS queue (`VecDeque`).
     - BFS flood-fill: for each neighbor (4-connected), if `new_cost < current_cost`, update and enqueue.
     - After BFS: for each cell, compare neighbor costs, store normalized direction toward lowest-cost neighbor.
   - `sample(&self, world_pos: Vec2) -> Vec2` — convert world pos to cell index, return direction. Return `Vec2::ZERO` if out of bounds or at goal.
   - `FlowFieldRegistry` resource (Contract 4) — `HashMap<u32, FlowField>` keyed by target faction ID. Implement `Default` (empty map).
3. **Update `lib.rs`** — Add `pub mod pathfinding`.
4. **Unit tests** — single goal at center produces outward gradient, multiple goals merge correctly, boundary cells handled, out-of-bounds returns zero, 50×50 grid calculation completes in under 5ms, registry stores and retrieves fields by faction ID.

**Verification Strategy:**
```yaml
Verification_Strategy:
  Test_Type: unit
  Test_Stack: cargo test
  Acceptance_Criteria:
    - "Single goal produces correct directional vectors in adjacent cells"
    - "Multiple goals generate shortest-path field"
    - "sample() returns Vec2::ZERO for out-of-bounds positions"
    - "50x50 grid calculation completes in < 5ms"
    - "FlowFieldRegistry stores/retrieves fields by target faction ID"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test pathfinding"
```

---

### Task 04 — Interaction, Removal & Navigation Rule Resources
**Phase:** 1 (Parallel) | **Tier:** `basic` | **Domain:** Data Model

| Property | Value |
|----------|-------|
| **Target Files** | `rules/mod.rs` [NEW], `rules/interaction.rs` [NEW], `rules/removal.rs` [NEW], `rules/navigation.rs` [NEW], `rules/behavior.rs` [NEW], `lib.rs` [MODIFY] |
| **Dependencies** | None |
| **Context Bindings** | `context/conventions`, `skills/rust-code-standards` |

**Strict Instructions:**

1. **Create `rules/mod.rs`** — Re-export all types from sub-modules.
2. **Create `rules/interaction.rs`** — `InteractionRuleSet`, `InteractionRule`, `StatEffect` per Contract 5. Implement `Default` with the swarm demo config. Include `RemovalEvents` resource (Contract 6).
3. **Create `rules/removal.rs`** — `RemovalRuleSet`, `RemovalRule`, `RemovalCondition` per Contract 5. Implement `Default` with stat[0] ≤ 0.0 removal rule.
4. **Create `rules/navigation.rs`** — `NavigationRuleSet`, `NavigationRule` per Contract 5. Implement `Default` with swarm demo config: `[{follower_faction: 0, target_faction: 1}]`. Unit tests for serialization and default values.
5. **Create `rules/behavior.rs`** — `FactionBehaviorMode` per Contract 10. Implement `Default` with faction 1 in `static_factions`. Unit tests for default and toggle logic.
6. **Update `lib.rs`** — Add `pub mod rules`.
7. **Unit tests** — Default configs have expected values. Serialization roundtrip. `RemovalCondition` enum coverage. NavigationRuleSet default has 1 rule. FactionBehaviorMode default has faction 1 static.

> [!NOTE]
> This task creates only the **data structures and default configs**. The systems that USE these rules (interaction_system, removal_system, flow_field_update_system) are in Tasks 05 and 06.

**Verification Strategy:**
```yaml
Verification_Strategy:
  Test_Type: unit
  Test_Stack: cargo test
  Acceptance_Criteria:
    - "Default InteractionRuleSet has 2 rules (faction 0→1 and 1→0)"
    - "Default RemovalRuleSet has 1 rule (stat[0] <= 0.0)"
    - "Default NavigationRuleSet has 1 rule (faction 0 → faction 1)"
    - "Default FactionBehaviorMode has faction 1 in static_factions"
    - "All rule types survive JSON serialization roundtrip"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test rules"
```

---

### Task 05 — Interaction System + Removal System
**Phase:** 2 (Parallel) | **Tier:** `standard` | **Domain:** ECS Systems

| Property | Value |
|----------|-------|
| **Target Files** | `systems/interaction.rs` [NEW], `systems/removal.rs` [NEW] |
| **Dependencies** | Task 02 (SpatialHashGrid), Task 04 (InteractionRuleSet, RemovalRuleSet, RemovalEvents) |
| **Context Bindings** | `context/conventions`, `context/architecture`, `skills/rust-code-standards` |

**Strict Instructions:**

1. **Create `systems/interaction.rs`** — `interaction_system`:
   - For each entity: get its `FactionId` and `Position`.
   - For each `InteractionRule` where `source_faction == entity.faction_id`:
     - Query `SpatialHashGrid::query_radius(entity.position, rule.range)`.
     - For each neighbor with matching `target_faction`:
       - Apply each `StatEffect`: `target.stat_block.0[effect.stat_index] += effect.delta_per_second / 60.0` (per-tick normalization).
   - **Optimization:** collect stat modifications into a `HashMap<Entity, Vec<(usize, f32)>>` first, then apply in a second pass (avoids mutable borrow conflicts in Bevy queries).
2. **Create `systems/removal.rs`** — `removal_system`:
   - For each entity with `StatBlock`:
     - For each `RemovalRule`: check if `stat_block.0[rule.stat_index]` crosses threshold per `rule.condition`.
     - If triggered: record `entity_id.id` in `RemovalEvents`, despawn entity.
3. **DO NOT modify `systems/mod.rs`** — The integration task (T08) handles wiring.
4. **Unit tests:**
   - Two entities of different factions in range → target stat decreases.
   - Same-faction entities with no matching rule → no stat changes.
   - Entity with stat[0] ≤ 0.0 → despawned and recorded in `RemovalEvents`.
   - Entity with stat[0] > 0.0 → not removed.

**Verification Strategy:**
```yaml
Verification_Strategy:
  Test_Type: unit
  Test_Stack: cargo test
  Acceptance_Criteria:
    - "interaction_system reduces target stat by delta_per_second / 60 per tick"
    - "Same-faction entities do not interact (unless rule exists)"
    - "removal_system despawns entities crossing stat threshold"
    - "RemovalEvents contains despawned entity IDs"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test interaction"
    - "cd micro-core && cargo test removal"
```

---

### Task 06 — FlowFieldFollower + Movement Integration + Wave Spawning
**Phase:** 2 (Parallel) | **Tier:** `standard` | **Domain:** ECS Components + Systems

| Property | Value |
|----------|-------|
| **Target Files** | `components/flow_field_follower.rs` [NEW], `components/mod.rs` [MODIFY], `systems/movement.rs` [MODIFY], `systems/flow_field_update.rs` [NEW], `systems/spawning.rs` [MODIFY] |
| **Dependencies** | Task 02 (SpatialHashGrid — for queries), Task 03 (FlowField + FlowFieldRegistry), Task 04 (NavigationRuleSet) |
| **Context Bindings** | `context/conventions`, `context/architecture`, `skills/rust-code-standards` |

**Strict Instructions:**

1. **Create `components/flow_field_follower.rs`** — Marker component. Entities with this opt into flow field navigation. Unit test for Default derive.
2. **Update `components/mod.rs`** — Add `pub mod flow_field_follower` and re-export `FlowFieldFollower`.
3. **Create `systems/flow_field_update.rs`** — `flow_field_update_system`:
   - Runs every `flow_field_update_interval` ticks (from `SimulationConfig`).
   - **Reads `NavigationRuleSet`** to determine which target factions need flow fields.
   - **Deduplicates targets:** collect unique `target_faction` IDs from all navigation rules.
   - For each unique target faction:
     - Query all entities with that `FactionId` → collect positions as goals.
     - Create/reuse a `FlowField` and call `calculate(goals, &[])` (no obstacles yet).
     - Insert into `FlowFieldRegistry::fields` keyed by target faction ID.
   - Remove any registry entries for target factions no longer in the rule set.
4. **Modify `systems/movement.rs`**:
   - Add `Res<FlowFieldRegistry>`, `Res<NavigationRuleSet>`, `Res<FactionBehaviorMode>`, `&FactionId`, and `Option<&FlowFieldFollower>` to system signature.
   - Entities WITH `FlowFieldFollower` AND faction NOT in `FactionBehaviorMode::static_factions`:
     - Look up entity's `FactionId` in `NavigationRuleSet` to find its `target_faction`.
     - Look up `target_faction` in `FlowFieldRegistry::fields`.
     - If a field exists, override velocity with `field.sample(position) * base_speed`. `base_speed` = magnitude of current velocity (preserves configured speed).
     - If no matching rule/field, keep current velocity (fallback).
   - Entities WITHOUT `FlowFieldFollower` OR faction IN `static_factions`: keep existing random velocity behavior.
   - **Replace wrap-around with clamping:** `pos.x = pos.x.clamp(0.0, config.world_width)`, same for y.
5. **Modify `systems/spawning.rs`** — Add `wave_spawn_system`:
   - Runs every `wave_spawn_interval` ticks.
   - Spawns `wave_spawn_count` entities of faction `wave_spawn_faction` at random edge positions.
   - Each entity gets `FlowFieldFollower` marker + `StatBlock::with_defaults(&config.wave_spawn_stat_defaults)`.
   - Uses `ResMut<NextEntityId>` for sequential IDs.
6. **DO NOT modify `systems/mod.rs`** — T08 handles wiring.
7. **Unit tests:**
   - Entity with FlowFieldFollower + matching navigation rule + faction NOT static → moves toward correct target.
   - Entity with FlowFieldFollower but faction IN static_factions → keeps random velocity.
   - Entity with FlowFieldFollower but no matching rule keeps current velocity.
   - Entity without FlowFieldFollower keeps random velocity.
   - Boundary clamping prevents position < 0 or > world_size.
   - wave_spawn_system spawns correct count at correct interval.
   - Multi-faction scenario: faction 0 → faction 1, faction 2 → faction 1 (field for faction 1 calculated once).

**Verification Strategy:**
```yaml
Verification_Strategy:
  Test_Type: unit
  Test_Stack: cargo test
  Acceptance_Criteria:
    - "FlowFieldFollower entities navigate toward correct target per NavigationRuleSet"
    - "Entities in static_factions use random drift even with FlowFieldFollower"
    - "Non-follower entities retain original velocity"
    - "Position clamps to world boundaries (no wrapping)"
    - "wave_spawn_system spawns correct count every N ticks"
    - "Multiple factions targeting same faction share one flow field calculation"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test movement"
    - "cd micro-core && cargo test spawning"
    - "cd micro-core && cargo test flow_field_update"
```

---

### Task 07 — IPC Protocol Extensions + Visualizer Upgrades
**Phase:** 3 (Sequential after Phase 2) | **Tier:** `standard` | **Domain:** IPC + Web UI

| Property | Value |
|----------|-------|
| **Target Files** | `bridges/ws_protocol.rs` [MODIFY], `systems/ws_sync.rs` [MODIFY], `systems/ws_command.rs` [MODIFY], `debug-visualizer/visualizer.js` [MODIFY] |
| **Dependencies** | Task 05 (interaction/removal — RemovalEvents), Task 06 (flow field) |
| **Context Bindings** | `context/conventions`, `context/ipc-protocol`, `skills/rust-code-standards` |

**Strict Instructions:**

**Rust side:**
1. **Update `bridges/ws_protocol.rs`**:
   - Add `stats: Vec<f32>` field to `EntityState` (already has `faction_id` from T01).
   - Add `removed: Vec<u32>` field to `WsMessage::SyncDelta`.
2. **Update `systems/ws_sync.rs`**:
   - Add `&StatBlock` to the query.
   - Populate `stats` field in `EntityState` from `stat_block.0.to_vec()`.
   - Drain `RemovalEvents::removed_ids` into `SyncDelta::removed`.
3. **Update `systems/ws_command.rs`**:
   - Add `set_faction_mode` command handler: parses `faction_id: u32` and `mode: "static" | "brain"` from params.
   - When `mode == "static"`: insert `faction_id` into `FactionBehaviorMode::static_factions`.
   - When `mode == "brain"`: remove `faction_id` from `FactionBehaviorMode::static_factions`.
   - Requires `ResMut<FactionBehaviorMode>` added to `ws_command_system` signature.

**Visualizer side:**
4. **Update `debug-visualizer/visualizer.js`**:
   - Parse `stats` array from moved entities.
   - Parse `removed` array — delete entities from local map (with brief fade animation).
   - **Health bars**: If `ADAPTER_CONFIG.stats[0].display === "bar"`, draw a small colored bar above each entity. Color interpolates from `color_high` to `color_low` based on `stat[0]` value.
   - **Death animation**: When entity removed, add to a `deathAnimations` list. Render as expanding, fading ring for 500ms, then remove.
   - **Per-faction behavior toggle**: For each faction in `ADAPTER_CONFIG.factions`, add a toggle button in the control panel: `"Static" / "Brain"`. Default state matches `FactionBehaviorMode::default()` (faction 1 starts static).
     - Clicking the toggle sends `set_faction_mode` WS command.
     - Toggle button label shows current mode and faction name from adapter config.
   - Update telemetry panel to show per-faction counts dynamically (not hardcoded "swarm"/"defender" labels).

**Verification Strategy:**
```yaml
Verification_Strategy:
  Test_Type: unit + manual_steps
  Test_Stack: cargo test (Rust), browser (JS)
  Acceptance_Criteria:
    - "SyncDelta JSON contains 'stats' array and 'removed' array"
    - "Visualizer renders health bars above entities"
    - "Removed entities disappear with fade animation"
    - "Telemetry shows faction counts based on adapter config"
    - "Per-faction behavior toggle buttons render in control panel"
    - "Clicking toggle sends set_faction_mode command and changes entity behavior"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test ws_sync"
    - "cd micro-core && cargo test ws_command"
  Manual_Steps:
    - "Run micro-core, open debug-visualizer"
    - "Verify health bars render in correct colors"
    - "Click 'Brain' toggle for faction 1 (Defender) — defenders should start navigating"
    - "Click 'Static' toggle for faction 0 (Swarm) — swarm should revert to random drift"
    - "Wait for combat — verify entities disappear when stat[0] reaches 0"
```

---

### Task 08 — Integration Wiring + 10K Stress Test
**Phase:** 4 (Sequential) | **Tier:** `advanced` | **Domain:** Integration

| Property | Value |
|----------|-------|
| **Target Files** | `main.rs` [MODIFY], `systems/mod.rs` [MODIFY], `config.rs` [MODIFY] |
| **Dependencies** | ALL previous tasks (01–07) |
| **Context Bindings** | `context/conventions`, `context/architecture`, `context/tech-stack`, `context/ipc-protocol`, `skills/rust-code-standards` |

**Strict Instructions:**

1. **Update `config.rs`** — Add all Phase 2 config fields from Contract 9 to `SimulationConfig`. Update `Default` impl with swarm demo defaults.
2. **Update `systems/mod.rs`** — Add `pub mod` for all new system modules: `interaction`, `removal`, `flow_field_update`. Re-export public system functions.
3. **Update `main.rs`**:
   - Insert new resources: `SpatialHashGrid::new(20.0)`, `FlowFieldRegistry::default()`, `InteractionRuleSet::default()`, `RemovalRuleSet::default()`, `NavigationRuleSet::default()`, `FactionBehaviorMode::default()`, `RemovalEvents::default()`.
   - Register new systems with ordering:
     ```
     update_spatial_grid_system
       → interaction_system (after spatial grid)
       → removal_system (after interaction)
       → ws_sync_system (after removal — to include removed IDs)
     flow_field_update_system (periodic, independent)
     wave_spawn_system (periodic, independent)
     ```
   - All new simulation systems gated by `SimState::Running` and pause/step conditions.
   - Add `--entity-count <N>` CLI arg to override `initial_entity_count`.
4. **Stress test:** Run with 10,000 entities:
   - `cargo run -- --entity-count 10000 --smoke-test`
   - Verify 60 TPS sustained over 600+ ticks.
   - Log average tick time each second.

**Verification Strategy:**
```yaml
Verification_Strategy:
  Test_Type: integration + manual_steps
  Test_Stack: cargo build + cargo run
  Acceptance_Criteria:
    - "cargo build succeeds with zero warnings"
    - "cargo clippy -- -D warnings is clean"
    - "cargo test passes all tests (existing + new)"
    - "10K entities sustain 60 TPS for 10+ seconds"
    - "Entities navigate via flow field visible in Debug Visualizer"
    - "Interaction causes stat[0] to decrease (health bars turning red)"
    - "Entities removed when stat[0] reaches 0 (visible in visualizer)"
    - "Wave spawning adds entities periodically at map edges"
  Suggested_Test_Commands:
    - "cd micro-core && cargo build"
    - "cd micro-core && cargo clippy -- -D warnings"
    - "cd micro-core && cargo test"
    - "cd micro-core && cargo run -- --entity-count 10000 --smoke-test"
  Manual_Steps:
    - "Run micro-core with default config, open debug-visualizer"
    - "Observe swarm entities navigating toward defenders"
    - "Observe health bars decreasing during proximity interaction"
    - "Observe dead entities disappearing"
    - "Observe wave spawning at map edges every 5 seconds"
    - "Toggle faction 1 (Defender) to 'Brain' mode — verify they start following flow fields"
    - "Toggle faction 0 (Swarm) to 'Static' — verify they revert to random drift"
```

---

## Phase 1 Refactoring Impact (File-Level Diff Summary)

| File | Change | Touched By |
|------|--------|------------|
| `components/team.rs` | **DELETED** | T01 |
| `components/faction.rs` | **NEW** — `FactionId(u32)` | T01 |
| `components/stat_block.rs` | **NEW** — `StatBlock([f32; 8])` | T01 |
| `components/flow_field_follower.rs` | **NEW** — marker | T06 |
| `components/mod.rs` | Remove Team, add FactionId + StatBlock | T01, T06 |
| `spatial/mod.rs` | **NEW** | T02 |
| `spatial/hash_grid.rs` | **NEW** | T02 |
| `pathfinding/mod.rs` | **NEW** | T03 |
| `pathfinding/flow_field.rs` | **NEW** — FlowField + FlowFieldRegistry | T03 |
| `rules/mod.rs` | **NEW** | T04 |
| `rules/interaction.rs` | **NEW** | T04 |
| `rules/navigation.rs` | **NEW** — NavigationRuleSet | T04 |
| `rules/behavior.rs` | **NEW** — FactionBehaviorMode | T04 |
| `rules/removal.rs` | **NEW** | T04 |
| `systems/interaction.rs` | **NEW** | T05 |
| `systems/removal.rs` | **NEW** | T05 |
| `systems/flow_field_update.rs` | **NEW** | T06 |
| `systems/movement.rs` | Modify — flow field + clamp | T06 |
| `systems/spawning.rs` | Modify — FactionId + wave spawn | T01, T06 |
| `systems/ws_sync.rs` | Modify — StatBlock + RemovalEvents | T01, T07 |
| `systems/ws_command.rs` | Modify — FactionId + set_faction_mode | T01, T07 |
| `systems/mod.rs` | Add new modules | T08 |
| `bridges/ws_protocol.rs` | Modify — faction_id + stats + removed | T01, T07 |
| `bridges/zmq_protocol.rs` | Modify — generic summary | T01 |
| `bridges/zmq_bridge/systems.rs` | Modify — FactionId | T01 |
| `config.rs` | Add Phase 2 config fields | T08 |
| `lib.rs` | Add spatial, pathfinding, rules modules | T02, T03, T04 |
| `main.rs` | Wire all new systems + resources | T08 |
| `debug-visualizer/visualizer.js` | Adapter config + health bars + removal | T01, T07 |

---

## Open Questions

> [!NOTE]
> **Flow Field Targeting: RESOLVED.** Adopted the `FlowFieldRegistry` + `NavigationRuleSet` architecture per user's design. Supports N-faction targeting with deduplication. Single-faction config fields removed.

> [!NOTE]
> **Defender Behavior: RESOLVED.** Added `FactionBehaviorMode` resource (Contract 10) with per-faction static/brain toggle. Default: faction 1 (defenders) starts in static mode. Debug Visualizer gets a per-faction toggle button. This enables testing flow fields independently per faction and prepares for multi-brain combat sessions in Phase 3 (one brain per faction, or one brain controlling multiple factions).

---

## Verification Plan

### Automated Tests
```bash
# All unit tests
cd micro-core && cargo test

# Lint gate
cd micro-core && cargo clippy -- -D warnings

# 10K entity stress test
cd micro-core && cargo run -- --entity-count 10000 --smoke-test
```

### Manual Verification (Debug Visualizer)
1. Open `debug-visualizer/index.html` while Micro-Core runs
2. ✅ Entities colored by faction via adapter config (not hardcoded "swarm"/"defender")
3. ✅ Swarm entities (faction 0) navigate toward defenders (faction 1) via flow field
4. ✅ Health bars render above entities (green → red as stat[0] decreases)
5. ✅ Entities in proximity interact — health (stat[0]) decreases
6. ✅ Dead entities disappear with fade animation
7. ✅ Wave spawning adds entities at map edges every 5 seconds
8. ✅ 10K entities render without browser lag
9. ✅ Per-faction behavior toggle works (Static ↔ Brain)

### Performance Gate
| Metric | Target |
|--------|--------|
| Tick Rate | 60 TPS sustained with 10K entities |
| Avg Tick Time | < 16.6ms |
| Spatial Grid Rebuild | < 2ms for 10K entities |
| Flow Field Calculate | < 5ms for 50×50 grid |

