# Task 01: UnitClassId Component

**Task_ID:** `task_01_unit_class_component`
**Feature:** Heterogeneous Swarm Mechanics
**Execution_Phase:** 1 (Parallel)
**Model_Tier:** `basic`

## Target_Files
- `micro-core/src/components/unit_class.rs` [NEW]
- `micro-core/src/components/mod.rs` [MODIFY]

## Dependencies
None

## Context_Bindings
- `skills/rust-code-standards`

## Strict_Instructions

### 1. Create `micro-core/src/components/unit_class.rs`

Create a new file with the following content:

```rust
//! # UnitClassId Component
//!
//! Context-agnostic unit class identifier.
//! The Micro-Core never knows what class 0 or class 1 means.
//! The game profile defines the mapping (e.g., class 0 = "Infantry", class 1 = "Sniper").
//!
//! ## Ownership
//! - **Task:** task_01_unit_class_component
//! - **Contract:** implementation_plan.md → Contract C1
//!
//! ## Depends On
//! - None

use bevy::prelude::*;
use serde::{Deserialize, Serialize};

/// Context-agnostic unit class identifier. Default: 0 (generic).
///
/// Used by `InteractionRule` to apply class-specific combat rules.
/// When `UnitClassId` is absent or 0, all rules with `source_class: None`
/// and `target_class: None` apply (backward compatible).
#[derive(Component, Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct UnitClassId(pub u32);

impl Default for UnitClassId {
    fn default() -> Self {
        Self(0)
    }
}

impl std::fmt::Display for UnitClassId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "class_{}", self.0)
    }
}
```

### 2. Add Tests

Add a `#[cfg(test)] mod tests` block with:
- `test_unit_class_id_default` — verifies `UnitClassId::default()` returns `UnitClassId(0)`
- `test_unit_class_id_display` — verifies `UnitClassId(5).to_string()` returns `"class_5"`
- `test_unit_class_id_serde_roundtrip` — serialize to JSON, deserialize back, assert equality

Follow AAA pattern (Arrange, Act, Assert) with section comments.

### 3. Modify `micro-core/src/components/mod.rs`

Add two lines:
```rust
pub mod unit_class;
```
(after the `pub mod vision_radius;` line)

And add to the re-exports:
```rust
pub use unit_class::UnitClassId;
```
(after the `pub use vision_radius::VisionRadius;` line)

## Verification_Strategy

```yaml
Test_Type: unit
Test_Stack: cargo test (Rust)
Acceptance_Criteria:
  - "UnitClassId::default() returns UnitClassId(0)"
  - "UnitClassId(5).to_string() returns 'class_5'"
  - "Serde roundtrip preserves value"
  - "cargo test components::unit_class passes"
  - "cargo test (full suite) still passes — no regressions"
Suggested_Test_Commands:
  - "cd micro-core && cargo test components::unit_class"
  - "cd micro-core && cargo test"
```
