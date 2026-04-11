# Task 04: Rust ZMQ Fog of War Payload

```yaml
Task_ID: task_04_rust_fog_zmq
Execution_Phase: 1
Model_Tier: standard
Dependencies: []
Target_Files:
  - micro-core/src/bridges/zmq_protocol/types.rs
  - micro-core/src/bridges/zmq_bridge/systems.rs
Context_Bindings:
  - context/architecture
  - context/ipc-protocol
  - skills/rust-code-standards
```

## Objective

Add the brain faction's fog-of-war grids (`fog_explored`, `fog_visible`) to the ZMQ state snapshot payload so Python can build fog-aware observations.

## Background

The Micro-Core already has:
- `FactionVisibility` resource with bit-packed `explored[]` and `visible[]` Vec per faction
- Wall-aware BFS visibility system in `micro-core/src/visibility.rs`
- The ZMQ state snapshot already includes `density_maps`, `terrain_hard`, `summary`

What's missing: the snapshot does NOT include the explored/visible grids. Python needs these to build the `ch5` (fog explored) and `ch6` (fog visible) observation channels.

## Strict Instructions

### 1. Add fog fields to `StateSnapshot` in `types.rs`

Find the `StateSnapshot` struct. Add two new optional fields:

```rust
/// Fog-of-war explored grid for the brain faction.
/// Flattened row-major (grid_h * grid_w). 
/// Values: 0 = unexplored, 1 = explored.
/// None when fog of war is disabled.
#[serde(skip_serializing_if = "Option::is_none")]
pub fog_explored: Option<Vec<u8>>,

/// Fog-of-war currently-visible grid for the brain faction.
/// Flattened row-major. Values: 0 = hidden, 1 = visible now.
/// None when fog of war is disabled.
#[serde(skip_serializing_if = "Option::is_none")]
pub fog_visible: Option<Vec<u8>>,
```

### 2. Populate fog data in `systems.rs`

Find the function that builds the `StateSnapshot` for ZMQ (likely `build_state_snapshot` or similar in the ZMQ bridge systems).

Add fog grid extraction:

```rust
// Read the FactionVisibility resource
let fog_data = if let Some(visibility) = world.get_resource::<FactionVisibility>() {
    // brain_faction_id comes from the reset config or is faction 0 by default
    let brain_faction = 0u32; // TODO: read from config if available
    
    let explored = visibility.explored.get(&brain_faction)
        .map(|bits| bits.iter().map(|b| if *b { 1u8 } else { 0u8 }).collect::<Vec<u8>>());
    let visible = visibility.visible.get(&brain_faction)
        .map(|bits| bits.iter().map(|b| if *b { 1u8 } else { 0u8 }).collect::<Vec<u8>>());
    
    (explored, visible)
} else {
    (None, None)
};
```

Then include in the snapshot:

```rust
StateSnapshot {
    // ... existing fields ...
    fog_explored: fog_data.0,
    fog_visible: fog_data.1,
}
```

### 3. Handle the FactionVisibility data format

Check `micro-core/src/visibility.rs` for how `explored` and `visible` are stored. They may be:
- `Vec<bool>` — straightforward conversion to `Vec<u8>`
- Bit-packed `Vec<u64>` — need to unpack bits to individual `u8` values
- `HashSet<(usize, usize)>` — need to convert to flat grid

Adapt the extraction code to match the actual data structure. The output must be a flat `Vec<u8>` of length `grid_h * grid_w` in row-major order.

### 4. Ensure backward compatibility

When `FactionVisibility` doesn't exist (fog disabled), both fields are `None` and will be omitted from the JSON via `skip_serializing_if`. Python handles `None` by defaulting to fully explored/visible.

### 5. Update any existing tests

If there are existing tests for `StateSnapshot` serialization, update them to include the new optional fields. Add a test that verifies the fields serialize correctly when present and are omitted when `None`.

## Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: unit
  Test_Stack: cargo test (micro-core)
  Acceptance_Criteria:
    - "StateSnapshot serializes fog_explored and fog_visible when present"
    - "StateSnapshot omits fog fields when None (backward compat)"
    - "Fog grids are flat Vec<u8> of correct length (grid_h * grid_w)"
    - "Values are 0 or 1 only"
    - "Existing tests still pass (no regressions)"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test"
```
