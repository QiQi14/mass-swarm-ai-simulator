---
Task_ID: task_01_context_agnostic_refactor
Execution_Phase: Phase 0 (Sequential — must complete before all others)
Model_Tier: advanced
Target_Files:
  - micro-core/src/components/faction.rs
  - micro-core/src/components/stat_block.rs
  - micro-core/src/components/team.rs
  - micro-core/src/components/mod.rs
  - micro-core/src/systems/spawning.rs
  - micro-core/src/systems/ws_sync.rs
  - micro-core/src/systems/ws_command.rs
  - micro-core/src/bridges/ws_protocol.rs
  - micro-core/src/bridges/zmq_protocol.rs
  - micro-core/src/bridges/zmq_bridge/systems.rs
  - debug-visualizer/visualizer.js
Dependencies: None
Context_Bindings:
  - context/conventions
  - context/architecture
  - context/ipc-protocol
  - skills/rust-code-standards
---

# STRICT INSTRUCTIONS

This task performs a cross-cutting refactor to make the Micro-Core context-agnostic. The semantic `Team` enum is replaced with numeric `FactionId(u32)`, and a generic `StatBlock([f32; 8])` component is added. All existing code referencing `Team` must be updated.

**Read `implementation_plan.md` Contracts 1, 2, and 8 for the exact data model specs.**

## 1. Create `micro-core/src/components/faction.rs` [NEW]

```rust
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

Unit tests: display format, serde roundtrip, equality.

## 2. Create `micro-core/src/components/stat_block.rs` [NEW]

```rust
use bevy::prelude::*;
use serde::{Deserialize, Serialize};

pub const MAX_STATS: usize = 8;

/// Anonymous stat array. The Micro-Core never knows what each index means.
#[derive(Component, Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct StatBlock(pub [f32; MAX_STATS]);

impl Default for StatBlock {
    fn default() -> Self {
        Self([0.0; MAX_STATS])
    }
}

impl StatBlock {
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

Unit tests: default is all zeros, `with_defaults` sets correct indices, serde roundtrip.

## 3. Delete `micro-core/src/components/team.rs` [DELETE]

Remove the file entirely.

## 4. Update `micro-core/src/components/mod.rs` [MODIFY]

- Remove `pub mod team;` and `pub use team::Team;`.
- Add `pub mod faction;` and `pub mod stat_block;`.
- Re-export: `pub use faction::FactionId;`, `pub use stat_block::{StatBlock, MAX_STATS};`.

## 5. Update `micro-core/src/systems/spawning.rs` [MODIFY]

- Replace `use crate::components::{..., Team, ...}` with `use crate::components::{..., FactionId, StatBlock, ...}`.
- Replace `let team = if i % 2 == 0 { Team::Swarm } else { Team::Defender };` with `let faction = FactionId(if i % 2 == 0 { 0 } else { 1 });`.
- Add `StatBlock::with_defaults(&[(0, 1.0)])` to entity spawn bundles (stat[0] = initial "health").
- Replace `team.clone()` in spawn bundle with `faction` and the new `StatBlock`.
- Update any tests to use `FactionId` instead of `Team`.

## 6. Update `micro-core/src/systems/ws_sync.rs` [MODIFY]

- Replace `use crate::components::{..., team::Team, ...}` with `use crate::components::{..., FactionId, StatBlock, ...}`.
- Add `&StatBlock` and `&FactionId` to the query (replacing `&Team`).
- Serialize `faction_id: faction.0` and `stats: stat_block.0.to_vec()` into `EntityState`.
- Update tests.

## 7. Update `micro-core/src/systems/ws_command.rs` [MODIFY]

- Replace `use crate::components::{..., Team, ...}` with `use crate::components::{..., FactionId, StatBlock, ...}`.
- `spawn_wave`: parse `faction_id: u32` from params (default 0) instead of `team: String`. Create `FactionId(faction_id)`.
- Add `StatBlock::with_defaults(&[(0, 1.0)])` to spawned entity bundles.
- `kill_all`: parse `faction_id: u32` from params. Match `FactionId(faction_id)` instead of `Team`.
- Replace `team_query: Query<(Entity, &Team)>` with `faction_query: Query<(Entity, &FactionId)>`.
- Update tests.

## 8. Update `micro-core/src/bridges/ws_protocol.rs` [MODIFY]

- Remove `use crate::components::team::Team;`.
- Replace `pub team: Team` with `pub faction_id: u32` in `EntityState`.
- Add `pub stats: Vec<f32>` to `EntityState`.
- Add `pub dx: f32` and `pub dy: f32` if not already present (check current state).

## 9. Update `micro-core/src/bridges/zmq_protocol.rs` [MODIFY]

- Replace `pub team: String` with `pub faction_id: u32` and `pub stats: Vec<f32>` in `EntitySnapshot`.
- Replace `SummarySnapshot` fields:
  - Remove: `swarm_count`, `defender_count`, `avg_swarm_health`, `avg_defender_health`.
  - Add: `faction_counts: std::collections::HashMap<u32, u32>`, `faction_avg_stats: std::collections::HashMap<u32, Vec<f32>>`.
- Update all tests.

## 10. Update `micro-core/src/bridges/zmq_bridge/systems.rs` [MODIFY]

- Replace `use crate::components::{..., Team}` with `use crate::components::{..., FactionId, StatBlock}`.
- Replace `Team::Swarm`/`Team::Defender` match arms with numeric `FactionId` iterations.
- Build generic summary by iterating all entities and accumulating per-faction counts dynamically using a `HashMap<u32, u32>` and `HashMap<u32, Vec<f32>>`.
- Update queries: `Query<(&EntityId, &Position, &Team)>` → `Query<(&EntityId, &Position, &FactionId, &StatBlock)>`.
- Update all tests to use `FactionId` and `StatBlock` instead of `Team`.

## 11. Update `debug-visualizer/visualizer.js` [MODIFY]

- Add `ADAPTER_CONFIG` constant at the top of the file:
  ```javascript
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
- Replace all `ent.team === "swarm"` / `ent.team === "defender"` with adapter config lookups using `ent.faction_id`.
- Replace `team: "swarm"` in `sendCommand("spawn_wave", ...)` with `faction_id: 0`.
- Support `stats` array in entity data (store alongside existing entity data).
- Use `ADAPTER_CONFIG.factions[ent.faction_id].color` for entity rendering color.
- Update entity counting to use `ent.faction_id` comparisons.

---

# Verification_Strategy
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
