# Task A4: Configurable Initial Spawn System

**Task_ID:** task_a4_configurable_spawning
**Execution_Phase:** 1
**Model_Tier:** standard

## Target_Files
- `micro-core/src/config/simulation.rs`
- `micro-core/src/systems/spawning.rs`

## Dependencies
- None

## Context_Bindings
- context/architecture
- context/conventions
- skills/rust-code-standards

## Strict_Instructions

### Step 1: Add fields to `SimulationConfig` in `simulation.rs`

Add two new fields to `SimulationConfig`:

```rust
/// Number of factions to alternate between during initial spawn.
/// Default: 2 (faction 0 and faction 1).
pub initial_faction_count: u32,
/// Default stat values for initially spawned entities.
/// Each tuple is (stat_index, value). Default: [(0, 1.0)].
pub initial_stat_defaults: Vec<(usize, f32)>,
```

Update the `Default` impl to set:
```rust
initial_faction_count: 2,
initial_stat_defaults: vec![(0, 1.0)],
```

Update `test_default_config` to verify the new defaults:
```rust
assert_eq!(config.initial_faction_count, 2, "default faction count should be 2");
assert_eq!(config.initial_stat_defaults, vec![(0, 1.0)], "default stats should be [(0, 1.0)]");
```

### Step 2: Update `initial_spawn_system` in `spawning.rs`

Replace the hardcoded faction alternation and stat defaults:

**BEFORE:**
```rust
let faction = FactionId(if i % 2 == 0 { 0 } else { 1 });
```

**AFTER:**
```rust
let faction = FactionId(i % config.initial_faction_count);
```

**BEFORE:**
```rust
StatBlock::with_defaults(&[(0, 1.0)]),
```

**AFTER:**
```rust
StatBlock::with_defaults(&config.initial_stat_defaults),
```

### Step 3: Add test for configurable faction count

Add a new test in `spawning.rs`:

```rust
#[test]
fn test_initial_spawn_configurable_factions() {
    // Arrange
    let mut app = App::new();
    let mut config = SimulationConfig::default();
    config.world_width = 100.0;
    config.world_height = 100.0;
    config.initial_entity_count = 9;
    config.initial_faction_count = 3; // 3 factions instead of default 2
    app.insert_resource(config);
    app.insert_resource(NextEntityId(1));
    app.add_systems(Startup, initial_spawn_system);

    // Act
    app.update();

    // Assert — check that faction IDs 0, 1, 2 all appear
    let factions: Vec<u32> = app
        .world_mut()
        .query::<&FactionId>()
        .iter(app.world())
        .map(|f| f.0)
        .collect();
    assert!(factions.contains(&0), "Should have faction 0");
    assert!(factions.contains(&1), "Should have faction 1");
    assert!(factions.contains(&2), "Should have faction 2");
    assert_eq!(factions.iter().filter(|&&f| f == 0).count(), 3, "3 entities per faction");
}
```

### Step 4: Verify

```bash
cd micro-core && cargo test spawning && cargo test config && cargo clippy
```

## Verification_Strategy
  Test_Type: unit
  Acceptance_Criteria:
    - "SimulationConfig::default().initial_faction_count == 2"
    - "SimulationConfig::default().initial_stat_defaults == [(0, 1.0)]"
    - "initial_spawn_system uses config.initial_faction_count for faction assignment"
    - "initial_spawn_system uses config.initial_stat_defaults for stat initialization"
    - "cargo test passes with zero failures"
    - "cargo clippy passes with zero warnings"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test spawning"
    - "cd micro-core && cargo test config::simulation"
