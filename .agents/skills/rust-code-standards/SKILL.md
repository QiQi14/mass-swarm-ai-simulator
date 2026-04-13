---
name: rust-code-standards
description: Rust commenting conventions and unit testing patterns for the Micro-Core. Load this skill for ANY Rust task.
keywords: [rust, test, unit-test, comment, doc, documentation, cargo-test, verify]
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

For non-ECS code (plain structs, enums, pure functions), **prefer doc tests** (see §2.8) over `#[cfg(test)]` when:
- The test also serves as usage documentation
- The function has a simple input → output contract
- No Bevy App or complex test fixtures are needed

When doc tests aren't appropriate (e.g., multi-step setup, error paths), use standard `#[cfg(test)]`:

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

### 2.8 Doc Tests (`rustdoc` examples)

Rust's `cargo test` automatically runs code examples in `///` doc comments. Use doc tests to **combine documentation and testing** — this reduces `#[cfg(test)]` bloat while keeping examples always up-to-date.

#### When to Use Doc Tests

| Use doc tests for | Keep `#[cfg(test)]` for |
|-------------------|------------------------|
| Pure functions with simple I/O | Bevy ECS system tests (need `App`) |
| Data type constructors & helpers | Multi-step integration tests |
| Showing "how to use this API" | Edge cases & error paths |
| Config/protocol struct examples | Performance-sensitive hot loops |

#### Format

```rust
/// Get the cumulative multiplier for a specific stat, respecting entity targeting.
///
/// Returns `1.0` if no active multiplier buff targets this entity.
///
/// # Examples
///
/// ```
/// use micro_core::config::*;
///
/// let mut buffs = FactionBuffs::default();
/// // No buffs → multiplier is 1.0
/// assert!((buffs.get_multiplier(0, 1, 0) - 1.0).abs() < f32::EPSILON);
///
/// // Add a 1.5× multiplier on stat 0, targeting all units (empty vec)
/// buffs.buffs.insert(0, vec![ActiveBuffGroup {
///     modifiers: vec![ActiveModifier {
///         stat_index: 0,
///         modifier_type: ModifierType::Multiplier,
///         value: 1.5,
///     }],
///     remaining_ticks: 60,
///     targets: Some(vec![]),  // All units
/// }]);
/// assert!((buffs.get_multiplier(0, 1, 0) - 1.5).abs() < f32::EPSILON);
/// ```
pub fn get_multiplier(&self, faction: u32, entity_id: u32, stat_index: usize) -> f32 {
    // ...
}
```

#### Rules

1. **`# Examples` heading** — always include so `rustdoc` renders it properly
2. **Use full import paths** — doc tests run as standalone, so `use micro_core::...` is required
3. **Keep examples short** — 5-15 lines max. If the example needs 20+ lines of setup, use `#[cfg(test)]` instead
4. **Test the happy path** — doc tests show *how to use*. Test edge cases in `#[cfg(test)]`
5. **Run with `cargo test --doc`** — verifies all doc examples compile and pass

#### Migration Strategy

When refactoring existing files, migrate simple `#[cfg(test)]` tests to doc tests where appropriate:

```rust
// ❌ Before: test + comment duplicating the same info
/// Check if combat is allowed between two factions.
pub fn is_combat_allowed(&self, source: u32, target: u32) -> bool { ... }

#[cfg(test)]
mod tests {
    #[test]
    fn test_combat_allowed_default() {
        let reg = AggroMaskRegistry::default();
        assert!(reg.is_combat_allowed(0, 1)); // default: all allowed
    }
}

// ✅ After: doc test = documentation + test in one place
/// Check if combat is allowed between two factions.
///
/// # Examples
///
/// ```
/// use micro_core::config::AggroMaskRegistry;
///
/// let reg = AggroMaskRegistry::default();
/// assert!(reg.is_combat_allowed(0, 1)); // default: all pairs allowed
/// ```
pub fn is_combat_allowed(&self, source: u32, target: u32) -> bool { ... }
```


---

## Part 3: Running Tests

```bash
# Run all tests
cd micro-core && cargo test

# Run doc tests only
cd micro-core && cargo test --doc

# Run tests for a specific module
cd micro-core && cargo test components      # all component tests
cd micro-core && cargo test systems         # all system tests
cd micro-core && cargo test config          # config tests

# Run a specific test by name
cd micro-core && cargo test test_movement_applies_velocity

# Build gate
cd micro-core && cargo build
cd micro-core && cargo clippy

# Verbose output (when debugging failures)
cd micro-core && cargo test -- --nocapture      # println! visible
cd micro-core && cargo test -- --show-output    # show stdout for passing tests
```

---

## Part 4: File Organization & Module Splitting

> **Origin:** Learned from `zmq_bridge.rs` growing to 421+ lines with 7 concerns. Now `zmq_bridge/systems.rs` is at **1098 lines** — a clear violation.

### 4.1 When to Split

A Rust source file **MUST** be split into submodules when it meets **ANY** of:

| Trigger | Threshold |
|---------|-----------|
| Lines (excluding tests) | **> 300 lines** |
| Distinct concerns | **3+ concerns** (e.g., data types + async I/O + Bevy systems) |
| Parallel agent collision | Multiple agents need different parts of the same file |

### 4.2 When NOT to Split

A file **MAY** remain as a single module when:
- It is under 300 lines
- All items are tightly coupled (e.g., a single system + its helper + its tests)
- Splitting would create modules with only 1-2 items each

### 4.3 If Not Splitting: Document Why

If a file exceeds 300 lines but you choose NOT to split, add a rationale at the top:

```rust
//! # ZMQ Bridge Plugin
//!
//! This module is intentionally kept as a single file because [reason].
//! Consider splitting if it grows beyond [threshold] or gains [new concern].
```

### 4.4 Recommended Split Patterns

**Bridge modules** (with config + I/O + systems):
```
bridges/zmq_bridge/
├── mod.rs          // pub use re-exports + ZmqBridgePlugin
├── config.rs       // AiBridgeConfig, AiBridgeChannels, SimState
├── io_loop.rs      // zmq_io_loop async function
├── systems.rs      // ai_trigger_system, ai_poll_system
├── reset.rs        // reset_environment_system + ResetRequest
└── snapshot.rs     // build_state_snapshot helper
```

**System modules** (with logic + tests exceeding 300 lines):
```
systems/
├── movement.rs         // Single system, keeps tests inline
├── interaction.rs      // Single system, keeps tests inline
├── directive_executor/ // Complex system with multiple directives
│   ├── mod.rs          // pub use + system registration
│   ├── executor.rs     // directive_executor_system
│   ├── buff_tick.rs    // buff_tick_system
│   └── zone_tick.rs    // zone_tick_system
```

**Config modules** (types + impls exceeding 300 lines):
```
config/
├── mod.rs              // pub use re-exports
├── simulation.rs       // SimulationConfig, TickCounter, SimPaused, SimSpeed
├── buff.rs             // BuffConfig, FactionBuffs, ActiveBuffGroup, ModifierType
├── zones.rs            // ActiveZoneModifiers, InterventionTracker
└── aggro.rs            // AggroMaskRegistry, ActiveSubFactions
```

### 4.5 Planning Implications

When the Planner creates a task that will produce a file with 3+ concerns:
1. **Pre-split** — Define the submodule structure in the task brief
2. OR **Document the decision** — Add a note: "Single file acceptable because [reason]"

### 4.6 Anti-patterns

- **❌** Creating a 400+ line file without acknowledging size or documenting why splitting was deferred.
- **❌** Splitting a 150-line file into 3 modules with 50 lines each — creates unnecessary navigation overhead.
- **✅** Split into focused submodules with clear single responsibility, OR add a module-level comment explaining why it stays together.

