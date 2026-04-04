---
name: rust-code-standards
description: Rust commenting conventions and unit testing patterns for the Micro-Core. Load this skill for ANY Rust task.
keywords: [rust, test, unit-test, comment, doc, documentation, cargo-test]
---

# Skill: Rust Code Standards

> **Scope:** All Rust code in `micro-core/`.  
> **Audience:** Executor and QA agents working on Rust tasks.

---

## Part 1: Comment Structure

Comments serve two audiences: **humans reading code** and **agents scanning for context**. Use this layered system.

### 1.1 Module-Level Doc Comment (`//!`)

Every `.rs` file starts with a module-level doc comment. This is the **first thing agents read** when loading a file.

```rust
//! # Movement System
//!
//! Applies velocity to position each tick with world-boundary wrapping.
//!
//! ## Ownership
//! - **Task:** task_03_systems_config
//! - **Contract:** implementation_plan.md → Shared Contracts → System Signatures
//!
//! ## Depends On
//! - `crate::components::{Position, Velocity}`
//! - `crate::config::SimulationConfig`
```

**Rules:**
- `# Title` — matches the file's primary purpose (1 line)
- Short description — what this module does (1-2 lines)
- `## Ownership` — which task created/owns this file + contract reference
- `## Depends On` — explicit `use` dependencies (helps agents understand coupling)

### 1.2 Public Item Doc Comments (`///`)

Every `pub` struct, enum, function, and method gets a `///` doc comment.

```rust
/// 2D position in world space.
///
/// Origin is top-left `(0, 0)`. Positive Y goes down.
/// Values are clamped to `[0, world_width)` × `[0, world_height)` by the movement system.
#[derive(Component, Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Position {
    /// Horizontal coordinate in world units.
    pub x: f32,
    /// Vertical coordinate in world units.
    pub y: f32,
}
```

**Rules:**
- First line: **what it is** (noun phrase for types, verb phrase for functions)
- Second paragraph (optional): **constraints, invariants, or non-obvious behavior**
- Field-level `///` comments for structs with more than 2 fields or non-obvious semantics

### 1.3 Function Doc Comments

```rust
/// Applies velocity to position each tick, with world-boundary wrapping.
///
/// Entities that exit `[0, world_width) × [0, world_height)` wrap to the
/// opposite edge. This prevents drift-to-infinity in the pre-pathfinding phase.
///
/// # Arguments
/// * `query` — All entities with both `Position` and `Velocity` components.
/// * `config` — World dimensions for boundary wrapping.
pub fn movement_system(
    mut query: Query<(&mut Position, &Velocity)>,
    config: Res<SimulationConfig>,
) { ... }
```

**Rules:**
- First line: **what the function does** (imperative verb)
- Body: **why** it exists or **edge cases** it handles
- `# Arguments` section: only when parameters are non-obvious (skip for simple getters)
- Do NOT add `# Returns` for functions returning `()` or obvious types

### 1.4 Inline Comments (`//`)

Use sparingly. Only for **non-obvious logic** or **intentional design decisions**.

```rust
// Wrap around world boundaries (toroidal topology)
if pos.x < 0.0 {
    pos.x += config.world_width;
}

// IDs start at 1 — 0 is reserved for "no entity" sentinel
pub struct NextEntityId(pub u32);
```

**Anti-patterns — DO NOT do this:**
```rust
// ❌ BAD: Restating what the code already says
let x = pos.x + vel.dx; // add velocity to position

// ❌ BAD: Trivial comments
pos.x = 0.0; // set x to zero
```

---

## Part 2: Unit Testing

### 2.1 Test Location

Tests live **inside the same file** as the code they test, using the standard Rust `#[cfg(test)]` module pattern:

```rust
// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_descriptive_name() {
        // ...
    }
}
```

**Rules:**
- The `// ── Tests ──` visual separator makes the test block easy to locate for both humans and agents.
- One `mod tests` per file. No separate test files for unit tests.
- Integration tests go in `micro-core/tests/` (top-level `tests/` directory).

### 2.2 Test Naming Convention

```
test_<unit>_<scenario>[_<expected_outcome>]
```

**Examples:**
```rust
#[test]
fn test_movement_applies_velocity() { ... }

#[test]
fn test_movement_wraps_at_right_boundary() { ... }

#[test]
fn test_position_serialization_roundtrip() { ... }

#[test]
fn test_next_entity_id_default_starts_at_one() { ... }

#[test]
fn test_team_display_lowercase() { ... }
```

**Rules:**
- Always prefix with `test_`
- `<unit>` — the thing being tested (e.g., `movement`, `position`, `team`)
- `<scenario>` — the specific case (e.g., `wraps_at_right_boundary`)
- `<expected_outcome>` — optional, when the scenario name isn't sufficient

### 2.3 Test Structure: Arrange-Act-Assert (AAA)

Every test follows the **AAA pattern** with visual section comments:

```rust
#[test]
fn test_movement_applies_velocity() {
    // Arrange
    let mut app = App::new();
    app.insert_resource(SimulationConfig::default());
    app.add_systems(Update, movement_system);

    let entity = app.world_mut().spawn((
        Position { x: 100.0, y: 200.0 },
        Velocity { dx: 1.5, dy: -0.5 },
    )).id();

    // Act
    app.update();

    // Assert
    let pos = app.world().get::<Position>(entity).unwrap();
    assert!((pos.x - 101.5).abs() < f32::EPSILON, "x should be 101.5, got {}", pos.x);
    assert!((pos.y - 199.5).abs() < f32::EPSILON, "y should be 199.5, got {}", pos.y);
}
```

**Rules:**
- Use `// Arrange`, `// Act`, `// Assert` comments to visually separate sections
- Always include a descriptive message string in `assert!` / `assert_eq!` macros
- For simple tests (1-2 lines), the AAA comments can be omitted

### 2.4 Testing Bevy ECS Systems

Bevy systems need a mini `App` to run. Use this pattern:

```rust
#[test]
fn test_some_system() {
    // Arrange — build a minimal Bevy app with ONLY the system under test
    let mut app = App::new();
    app.insert_resource(MyResource::default());        // insert required resources
    app.add_systems(Update, system_under_test);        // register the system

    let entity = app.world_mut().spawn((               // spawn test entities
        ComponentA { ... },
        ComponentB { ... },
    )).id();

    // Act — run one tick
    app.update();

    // Assert — read back the component state
    let result = app.world().get::<ComponentA>(entity).unwrap();
    assert_eq!(result.field, expected_value);
}
```

**Rules:**
- **Minimal app:** Only add the system being tested + its required resources. Do NOT use `MinimalPlugins` in tests (it starts a real loop). Use a bare `App::new()`.
- **One `app.update()` = one tick.** Call it multiple times to test multi-tick behavior.
- **Spawn only what you need.** Don't spawn 100 entities when 1-2 will prove the behavior.

### 2.5 Testing Pure Functions and Data Types

For non-ECS code (plain structs, enums, pure functions), use standard Rust testing:

```rust
#[test]
fn test_position_serialization_roundtrip() {
    // Arrange
    let original = Position { x: 1.5, y: 2.5 };

    // Act
    let json = serde_json::to_string(&original).unwrap();
    let deserialized: Position = serde_json::from_str(&json).unwrap();

    // Assert
    assert_eq!(original, deserialized, "Position should survive JSON roundtrip");
}
```

### 2.6 Floating-Point Comparisons

**Never use `==` for `f32`/`f64` comparisons.** Always use epsilon-based checks:

```rust
// ✅ Correct
assert!((pos.x - 101.5).abs() < f32::EPSILON, "x should be ~101.5, got {}", pos.x);

// ✅ Also correct — for less precise checks
assert!((pos.x - 101.5).abs() < 0.001);

// ❌ WRONG — will fail due to floating point drift
assert_eq!(pos.x, 101.5);
```

### 2.7 Test File Template

When creating a new `.rs` file that needs tests, use this complete template:

```rust
//! # [Module Title]
//!
//! [Brief description of what this module does.]
//!
//! ## Ownership
//! - **Task:** [task_id]
//! - **Contract:** implementation_plan.md → [section reference]
//!
//! ## Depends On
//! - `crate::path::to::Dependency`

use bevy::prelude::*;
use serde::{Deserialize, Serialize};

// ... implementation code ...

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_example() {
        // Arrange
        // Act
        // Assert
    }
}
```

---

## Part 3: Running Tests

```bash
# Run all tests
cd micro-core && cargo test

# Run tests for a specific module
cd micro-core && cargo test components      # all component tests
cd micro-core && cargo test systems         # all system tests
cd micro-core && cargo test config          # config tests

# Run a specific test by name
cd micro-core && cargo test test_movement_applies_velocity

# Run tests with output (shows println! in tests)
cd micro-core && cargo test -- --nocapture

# Run tests and show which ones passed
cd micro-core && cargo test -- --show-output
```
