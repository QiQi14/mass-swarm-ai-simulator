# Task 02: ECS Components

```yaml
Task_ID: task_02_ecs_components
Feature: P1-MP1 Rust/Bevy Scaffold + Minimal ECS
Execution_Phase: B (parallel with Task 03 — zero file overlap)
Model_Tier: basic
```

## Target Files
- `micro-core/src/components/mod.rs` [MODIFY]
- `micro-core/src/components/position.rs` [NEW]
- `micro-core/src/components/velocity.rs` [NEW]
- `micro-core/src/components/team.rs` [NEW]
- `micro-core/src/components/entity_id.rs` [NEW]

## Dependencies
- **Task 01** must be complete (project must compile)

## Context_Bindings
- context/conventions
- context/ipc-protocol
- skills/rust-code-standards

## Strict Instructions

### 1. Create `src/components/position.rs`

```rust
use bevy::prelude::*;
use serde::{Deserialize, Serialize};

/// 2D position in world space.
/// Origin is top-left (0,0), positive Y goes down.
#[derive(Component, Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Position {
    pub x: f32,
    pub y: f32,
}
```

### 2. Create `src/components/velocity.rs`

```rust
use bevy::prelude::*;
use serde::{Deserialize, Serialize};

/// Per-tick velocity vector applied by the movement system.
#[derive(Component, Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Velocity {
    pub dx: f32,
    pub dy: f32,
}
```

### 3. Create `src/components/team.rs`

```rust
use bevy::prelude::*;
use serde::{Deserialize, Serialize};
use std::fmt;

/// Team affiliation for an entity.
#[derive(Component, Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum Team {
    Swarm,
    Defender,
}

impl fmt::Display for Team {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Team::Swarm => write!(f, "swarm"),
            Team::Defender => write!(f, "defender"),
        }
    }
}
```

> **IPC convention:** Team serializes to `"Swarm"` / `"Defender"` via serde by default.
> The `Display` impl provides lowercase output for logging.
> If the IPC protocol requires lowercase JSON keys, add `#[serde(rename_all = "lowercase")]` on the enum.

### 4. Create `src/components/entity_id.rs`

```rust
use bevy::prelude::*;
use serde::{Deserialize, Serialize};

/// Globally unique entity identifier within a simulation session.
/// Monotonically assigned via the `NextEntityId` resource.
#[derive(Component, Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct EntityId {
    pub id: u32,
}

/// Resource tracking the next available entity ID.
/// Incremented each time a new simulation entity is spawned.
#[derive(Resource, Debug)]
pub struct NextEntityId(pub u32);

impl Default for NextEntityId {
    fn default() -> Self {
        Self(1) // IDs start at 1, 0 is reserved
    }
}
```

### 5. Update `src/components/mod.rs`

Replace the empty stub with:

```rust
pub mod entity_id;
pub mod position;
pub mod team;
pub mod velocity;

pub use entity_id::{EntityId, NextEntityId};
pub use position::Position;
pub use team::Team;
pub use velocity::Velocity;
```

### 6. Write Unit Tests

Add tests in each component file (inside `#[cfg(test)] mod tests { ... }`):

**position.rs tests:**
- Create a `Position { x: 1.5, y: 2.5 }`, serialize to JSON, deserialize back, assert equality.

**velocity.rs tests:**
- Create a `Velocity { dx: -0.5, dy: 1.0 }`, serialize to JSON, deserialize back, assert equality.

**team.rs tests:**
- `Team::Swarm` Display output is `"swarm"`.
- `Team::Defender` Display output is `"defender"`.
- Serialize `Team::Swarm` to JSON, deserialize back, assert equality.

**entity_id.rs tests:**
- `NextEntityId::default()` starts at 1.
- Create `EntityId { id: 42 }`, serialize to JSON, deserialize back, assert equality.

## Verification_Strategy

```yaml
Test_Type: unit
Test_Stack: cargo (Rust toolchain)
Acceptance_Criteria:
  - "All 4 component files exist with correct derives"
  - "mod.rs re-exports all types"
  - "`cargo build` succeeds"
  - "`cargo test` — all serialization round-trip tests pass"
  - "`cargo clippy` — zero warnings"
  - "Each component derives Component, Debug, Clone, Serialize, Deserialize"
  - "Team has Display impl producing lowercase strings"
  - "NextEntityId defaults to 1"
Suggested_Test_Commands:
  - "cd micro-core && cargo test components 2>&1"
  - "cd micro-core && cargo clippy 2>&1"
```
