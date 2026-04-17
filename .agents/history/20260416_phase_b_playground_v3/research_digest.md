# Research Digest: Action Space v3 + Runtime Tactical Overrides

## Relevant File Map

| File | Purpose | Key Exports / Types | Relevant Lines |
|------|---------|-------------------|----------------|
| `micro-core/src/systems/movement.rs` | Composite steering — flow + boids + tactical | `movement_system()` | L52-222, **L96-109 (waypoint bug)**, L139-156 (engagement range) |
| `micro-core/src/systems/flow_field_update.rs` | Recomputes flow fields at ~2 TPS | `flow_field_update_system()` | L37-169, L130-158 (waypoint FF computation) |
| `micro-core/src/systems/tactical_sensor.rs` | 10 Hz sharded behavior evaluator | `tactical_sensor_system()` | L50-177, **L78-86 (registry lookup — add override check here)** |
| `micro-core/src/systems/directive_executor/executor.rs` | Python directives → ECS mutations | `directive_executor_system()` | L36-250, **L151-210 (SplitFaction — add class_filter)**, L236-247 (SetAggroMask) |
| `micro-core/src/systems/flow_field_safety.rs` | Zone modifier overlay | `apply_zone_overlays()` | L12-62 |
| `micro-core/src/pathfinding/flow_field.rs` | Dijkstra flow field + gradient | `FlowField`, `FlowFieldRegistry` | L84-252, L260-262 (registry resource) |
| `micro-core/src/bridges/zmq_protocol/directives.rs` | Directive enum definitions | `MacroDirective`, `NavigationTarget` | L85-139 |
| `micro-core/src/bridges/zmq_protocol/payloads.rs` | Wire-format definitions | `TacticalBehaviorPayload`, `UnitTypeDefinition`, `SpawnConfig` | L150-210 |
| `micro-core/src/config/unit_registry.rs` | Unit type definitions per class_id | `UnitTypeRegistry`, `UnitTypeDef`, `TacticalBehavior` | L17-113 |
| `micro-core/src/components/unit_class.rs` | UnitClassId ECS component | `UnitClassId(pub u32)` | L23 |
| `micro-core/src/components/tactical.rs` | Per-entity tactical steering state | `TacticalState`, `CombatState` | L24-46 |
| `micro-core/src/rules/behavior.rs` | Per-faction static/brain mode | `FactionBehaviorMode` | L12-31 |
| `micro-core/src/systems/state_vectorizer.rs` | ZMQ snapshot builder | — | L31+ (sub-faction density) |
| `macro-brain/src/env/spaces.py` | Action/obs space definitions | `ACTION_*`, `make_action_space()` | L1-122 |
| `macro-brain/src/env/actions.py` | MultiDiscrete → directive conversion | `multidiscrete_to_directives()` | L87-226 |
| `macro-brain/src/env/swarm_env.py` | Gym env, masking, reset | `action_masks()` | L164-186 |
| `macro-brain/src/utils/vectorizer.py` | Snapshot → numpy observation | `vectorize_snapshot()` | L37-330 |
| `macro-brain/src/training/curriculum.py` | Stage configs, spawns, terrain | Various | L1-659 |

## Existing Contracts & Types

### SplitFaction Directive (add class_filter)

```rust
// From: micro-core/src/bridges/zmq_protocol/directives.rs:L122-128
SplitFaction {
    source_faction: u32,
    new_sub_faction: u32,
    percentage: f32,
    epicenter: [f32; 2],
    // PROPOSED: add here
    // class_filter: Option<u32>,  // None = all, Some(0) = class 0 only
}
```

### SplitFaction Executor (candidate query — add UnitClassId filter)

```rust
// From: executor.rs:L159-166
// Current: queries (Entity, &Position, &mut FactionId) — no class filter
let mut candidates: Vec<(Entity, f32)> = faction_query
    .iter()
    .filter(|(_, _, f)| f.0 == source_faction)
    // PROPOSED: add .filter(|(e, _, _)| class_filter.map_or(true, |cf| q_class.get(*e).map_or(false, |c| c.0 == cf)))
    .map(|(entity, pos, _)| {
        let dist_sq = Vec2::new(pos.x, pos.y).distance_squared(epi_vec);
        (entity, dist_sq)
    })
    .collect();
```

**Note:** The `faction_query` in `directive_executor_system` is `Query<(Entity, &Position, &mut FactionId)>`. To filter by class, either:
- Add `&UnitClassId` to the query tuple (simplest)
- Or use a separate `q_class: Query<&UnitClassId>` with `q_class.get(entity)`

### TacticalBehavior Enum (runtime overrides)

```rust
// From: micro-core/src/config/unit_registry.rs:L22-36
pub enum TacticalBehavior {
    Kite {
        trigger_radius: f32,
        weight: f32,
    },
    PeelForAlly {
        target_class: u32,
        search_radius: f32,
        require_recent_damage: bool,
        weight: f32,
    },
}
```

### TacticalState Component (movement system reads this)

```rust
// From: micro-core/src/components/tactical.rs:L24-32
#[derive(Component, Debug, Clone, Default)]
pub struct TacticalState {
    pub direction: Vec2,      // Tactical steering direction
    pub weight: f32,          // 0.0 = no tactical override
    pub engagement_range: f32, // Cached from UnitTypeRegistry
}
```

### Movement System 3-Vector Blend

```rust
// From: movement.rs:L158-163
// V_desired = (V_flow × W_flow) + (V_sep × W_sep) + (V_tactical × W_tactical)
let desired = (macro_dir * effective_flow_weight)
    + (separation_dir * mc.separation_weight)
    + (tactical.direction * tactical.weight);
let desired = desired.normalize_or_zero() * mc.max_speed;
```

### Tactical Sensor Registry Lookup (insert override check here)

```rust
// From: tactical_sensor.rs:L78-86
let unit_def = match registry.get(class_id.0) {
    Some(def) if !def.behaviors.is_empty() => def,
    _ => {
        tactical.direction = Vec2::ZERO;
        tactical.weight = 0.0;
        continue;
    }
};
// PROPOSED: Check FactionTacticalOverrides BEFORE this registry lookup
// let behaviors = overrides.get(faction.0).unwrap_or(&unit_def.behaviors);
```

### Waypoint Flow Field Key (movement.rs must use this)

```rust
// From: flow_field_update.rs:L153
let waypoint_key = follower + 100_000;
registry.fields.insert(waypoint_key, field);
// movement.rs must do: registry.fields.get(&(faction.0 + 100_000))
```

### SpawnConfig (already has unit_class_id)

```rust
// From: payloads.rs:L106-125
pub struct SpawnConfig {
    pub faction_id: u32,
    pub count: u32,
    pub x: f32,
    pub y: f32,
    pub spread: f32,
    pub stats: Vec<SpawnStatEntry>,
    pub unit_class_id: u32,        // ← Already exists! Default: 0
    pub movement: Option<MovementConfigPayload>,
}
```

### AggroMaskRegistry (used by SetAggroMask)

```rust
// From: executor.rs:L236-247
MacroDirective::SetAggroMask { source_faction, target_faction, allow_combat } => {
    aggro.masks.insert((source_faction, target_faction), allow_combat);
    aggro.masks.insert((target_faction, source_faction), allow_combat);
}
// Bidirectional — setting (a, b) also sets (b, a)
```

### Python Action Space (current → proposed)

```python
# Current: MultiDiscrete([8, 2500])
# PROPOSED: MultiDiscrete([8, 2500, 4])

# spaces.py constants (proposed rename):
ACTION_HOLD = 0
ACTION_ATTACK_COORD = 1
ACTION_ZONE_MODIFIER = 2   # was ACTION_DROP_PHEROMONE
# ACTION_DROP_REPELLENT = 3  → REMOVED (merged into ZoneModifier modifier=1)
ACTION_SPLIT_TO_COORD = 3  # was 4
ACTION_MERGE_BACK = 4      # was 5
ACTION_SET_PLAYSTYLE = 5   # NEW
ACTION_ACTIVATE_SKILL = 6  # same idx, now functional
ACTION_RETREAT = 7         # was missing
```

## Integration Points

```
[Fix 1: Waypoint Flow Field]
  Producer: flow_field_update_system (flow_field_update.rs:L130-158)
    → stores at key: follower + 100_000
  Consumer: movement_system (movement.rs:L96-109)
    → MUST read key: faction.0 + 100_000 for Waypoint targets
    → Fallback: if no field, use direct vector (first tick)

[Fix 2: Class-Aware SplitFaction]
  Wire: directives.rs → add class_filter: Option<u32> to SplitFaction
  Parse: zmq_bridge/systems.rs OR zmq_bridge/reset.rs deserialization
  Execute: executor.rs L159-166 → add UnitClassId filter to candidate query
  Python: actions.py → build_split_faction_directive() adds class_filter from modifier

[Fix 3: Runtime Kite (SetTacticalOverride)]
  New directive: directives.rs → SetTacticalOverride { faction, behavior }
  New resource: config/tactical_overrides.rs → FactionTacticalOverrides
  Executor: executor.rs → insert/remove override on directive
  Sensor: tactical_sensor.rs → check overrides before registry (L78)
  Cleanup: executor.rs MergeFaction block → remove override on merge
  Init: main.rs → init_resource::<FactionTacticalOverrides>()

[Fix 4: SetPlaystyle action (Python)]
  actions.py → multidiscrete_to_directives():
    mod=0 → SetAggroMask(sub, enemies, true) + SetTacticalOverride(sub, None)
    mod=1 → SetAggroMask(sub, enemies, false)
    mod=2 → SetTacticalOverride(sub, Kite { trigger: 80, weight: 5 })
    mod=3 → SetTacticalOverride(sub, None) + SetAggroMask(sub, enemies, true)

[Fix 5: Per-Class Observation Channels]
  Producer: state_vectorizer.rs → emit class-filtered density maps
  Consumer: vectorizer.py → populate ch6 (class_0 density), ch7 (class_1 density)
  Note: class_2 = ch0 - ch6 - ch7 (no need for separate channel)
```

## Code Patterns in Use

- **Parallel query safety**: movement.rs uses `par_iter_mut()`. All queries are `&` (immutable reads) except the entity's own `&mut Position`/`&mut Velocity`. The flow field fix only reads `FlowFieldRegistry` (immutable `Res`) and `FactionId` (immutable `&`). Safe for parallel execution.

- **Entity sharding (tactical sensor)**: `entity.index_u32() % 6 == tick % 6`. Processes 1/6th of entities per tick = 10 Hz effective rate. `FactionTacticalOverrides` is `Res` (immutable read) — no sharding conflict.

- **Directive deserialization**: `serde(tag = "directive")` discriminated union. New variant `SetTacticalOverride` needs `#[serde(tag = "directive")]` and matching arm in executor.

- **Resource cleanup on merge**: MergeFaction in executor.rs (L212-234) cleans up nav_rules, zones, buffs, aggro masks, and int_rules for the merged sub-faction. Must add `tactical_overrides.overrides.remove(&source_faction)` to this block.

- **Sub-faction ID convention**: `(brain_faction + 1) * 100 + offset`. Brain=0 → subs=100, 101. Brain=1 → subs=200, 201. Max 2 sub-factions (action mask blocks split when ≥2).

- **Serde for new fields with backward compat**: Use `#[serde(default)]` on `class_filter: Option<u32>` so old Python code that doesn't send it gets `None` (split all classes). Zero-cost backward compat.

## Gotchas & Constraints Discovered

1. **The `faction_query` in executor.rs does NOT include `UnitClassId`:** Current signature is `Query<(Entity, &Position, &mut FactionId)>`. Adding `&UnitClassId` changes the query tuple. Verify that all other directive handlers that use `faction_query` are compatible with the expanded tuple. Specifically: MergeFaction (L216) and Retreat (L111) only use `(Entity, _, &mut FactionId)` — they should be fine with an extra `&UnitClassId` in the tuple.

2. **Tactical override vs registry priority:** The tactical sensor MUST check `FactionTacticalOverrides` FIRST. If an override exists for `faction.0`, use override behaviors. Otherwise fall back to `UnitTypeRegistry.get(class_id.0)`. This means a kite override on faction 100 (sub-faction) applies to ALL classes in that sub-faction, regardless of their UnitClassId. This is intentional — the General controls sub-factions as atomic groups.

3. **SetPlaystyle targets "most recent sub-faction":** `actions.py` should use `active_sub_factions[-1]` (last created). If no sub-factions exist, SetPlaystyle degrades to Hold (no-op). The action mask should hide SetPlaystyle when `len(active_sub_factions) == 0`.

4. **Zone modifier faction scoping:** `SetZoneModifier.target_faction` must match the faction whose flow field is affected. When brain splits into sub-factions, the zone modifier only affects the main faction's flow field. Sub-factions (100, 101) use the main faction's flow field only if they share the same waypoint key. After the flow field fix, each faction/sub-faction has its own flow field at key `follower + 100_000`. Zone modifiers on the main faction's flow field do NOT propagate to sub-factions. **This is a pre-existing limitation — not introduced by this redesign.**

5. **ws_command.rs `spawn_wave` hardcodes `UnitClassId::default()`:** (Line 180). The playground's spawn_wave WS command ignores the `unit_class_id` field from SpawnConfig. To support class-aware splits in playground, `spawn_wave` must also accept and pass through `unit_class_id`. This is a known gap noted in `playground_strategy_brief.md` constraint #6.

6. **Kite trigger_radius and weight values for SetPlaystyle:** The Python action converter hardcodes `Kite { trigger_radius: 80, weight: 5.0 }` for modifier=2. These values should be configurable via the game profile's ability config (not hardcoded). Add `kite_override_trigger_radius` and `kite_override_weight` to `AbilityConfigPayload`.

7. **MultiDiscrete masking for 3 dimensions:** SB3-contrib's `MaskablePPO` supports `MultiDiscrete` action masking — it masks each sub-space independently. The mask shape for `[8, 2500, 4]` is `[8 + 2500 + 4] = [2512]` bits. The modifier mask must be dynamically generated per action type (e.g., ZoneModifier allows mod={0,1}, SplitToCoord allows mod={0,1,2,3}). Verify that SB3 applies the modifier mask conditional on the selected action type. **If not, we may need a custom wrapper that re-masks dim 2 after dim 0 is sampled.** This is a critical implementation detail.

8. **`FactionTacticalOverrides` must be added to `zmq_bridge/reset.rs`:** On `ResetEnvironment`, clear all tactical overrides (they're per-episode state).
