# Task B2: Rust Tactical Sensor Override + Per-Class Density Maps

- **Task_ID:** `B2_rust_sensor_vectorizer`
- **Execution_Phase:** 1 (Brain Phase B — parallel with B1)
- **Model_Tier:** `standard`
- **Live_System_Impact:** `destructive` — modifies tactical sensor behavior

## Target_Files
- `micro-core/src/systems/tactical_sensor.rs` — MODIFY
- `micro-core/src/systems/state_vectorizer.rs` — MODIFY

## Dependencies
- **Contract from B1:** `FactionTacticalOverrides` resource type (defined in `config/tactical_overrides.rs`). If running in parallel with B1, the resource struct is trivial — code it inline or use the type from the plan contract.

## Context_Bindings
- `research_digest.md` — §Tactical Sensor Registry Lookup (L78-86), §Code Patterns (sharding, parallel safety)
- `implementation_plan_brain_v3.md` — Contract 3 (per-class density snapshot format)
- `.agents/skills/rust-code-standards/SKILL.md`

## Strict_Instructions

### 1. Tactical Sensor Override Check (tactical_sensor.rs)

At the current registry lookup (approximately line 78-86), insert a check for `FactionTacticalOverrides` BEFORE the `UnitTypeRegistry` lookup:

```rust
// BEFORE (current):
let unit_def = match registry.get(class_id.0) { ... };

// AFTER:
// Check faction-level tactical override first
let behaviors: &[TacticalBehavior] = if let Some(override_behaviors) = 
    tactical_overrides.overrides.get(&faction.0) 
{
    override_behaviors.as_slice()
} else {
    match registry.get(class_id.0) {
        Some(def) if !def.behaviors.is_empty() => &def.behaviors,
        _ => {
            tactical.direction = Vec2::ZERO;
            tactical.weight = 0.0;
            continue;
        }
    }
};
```

**Add `Res<FactionTacticalOverrides>` to the system's params.** The resource is `Res` (immutable read) — safe for `par_iter_mut()`.

**Important:** The rest of the subsumption logic (highest weight wins) stays unchanged — just swap which `behaviors` slice it iterates.

### 2. Per-Class Density Maps (state_vectorizer.rs)

Add a `class_density_maps` field to the ZMQ snapshot JSON. This provides per-class spatial density for the brain faction only.

In the vectorizer's existing density-map loop, add a secondary pass for the brain faction that filters by `UnitClassId`:

```rust
// After building density_maps, add class-filtered density for brain faction
let mut class_density_maps: HashMap<u32, Vec<f32>> = HashMap::new();
for class_id in 0..2 {  // Only emit class_0 and class_1 (class_2 = remainder)
    let mut density = vec![0.0f32; (grid_w * grid_h) as usize];
    for (pos, faction, unit_class) in class_density_query.iter() {
        if faction.0 == brain_faction && unit_class.0 == class_id {
            let gx = (pos.x / cell_size) as usize;
            let gy = (pos.y / cell_size) as usize;
            if gx < grid_w as usize && gy < grid_h as usize {
                density[gy * grid_w as usize + gx] += 1.0;
            }
        }
    }
    // Normalize same as other density maps
    let max_density = config.max_density;
    for v in density.iter_mut() {
        *v = (*v / max_density).min(1.0);
    }
    class_density_maps.insert(class_id, density);
}
```

Add a new query if needed: `Query<(&Position, &FactionId, &UnitClassId)>`.

Serialize into the snapshot JSON as:
```json
"class_density_maps": { "0": [...], "1": [...] }
```

## Verification_Strategy
```
Test_Type: unit + compilation
Acceptance_Criteria:
  - "When FactionTacticalOverrides has an entry for faction X, tactical sensor uses override behaviors"
  - "When no override exists, tactical sensor falls back to UnitTypeRegistry (unchanged behavior)"
  - "class_density_maps contains keys '0' and '1' for brain faction"
  - "Density values are normalized to [0, 1]"
  - "cargo check passes"
  - "cargo test passes"
Suggested_Test_Commands:
  - "cd micro-core && cargo check"
  - "cd micro-core && cargo test"
```
