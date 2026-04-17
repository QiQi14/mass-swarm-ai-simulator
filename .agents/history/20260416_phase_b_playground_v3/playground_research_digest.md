# Research Digest: Playground Dual-Builder Node System

## Relevant File Map

### Layout & Bootstrap (Training Reference Pattern)
| File | Purpose | Key Exports / Types | Relevant Lines |
|------|---------|-------------------|----------------|
| `debug-visualizer/training.html` | Training page HTML — **reference layout** | `#overlay-root`, `#overlay-bottom-wrapper`, `.overlay-left-cluster`, `.overlay-right-cluster` | L23-43 (overlay DOM) |
| `debug-visualizer/src/training-main.js` | Training bootstrap — **reference for card groups** | `PANEL_LAYOUT`, `renderOverlayCards()`, `buildLayersBar()`, `initOverlayToggle()` | L37-44 (layout map), L66-121 (card render), L320-344 (minimize toggle) |
| `debug-visualizer/src/styles/overlay.css` | Overlay card styles — **must reuse** | `.overlay-card`, `.overlay-top-bar`, `.overlay-layout-wrapper`, `pointer-events: none/auto` pattern | L81-92 (card), L219-231 (layout wrapper) |

### Current Playground (Files to Replace)
| File | Purpose | Key Exports / Types | Relevant Lines |
|------|---------|-------------------|----------------|
| `debug-visualizer/index.html` | Playground entry — **needs layout restructure** | `#app`, `#canvas-area`, `#sidebar`, `#panel-scroll` | L1-52 (entire) |
| `debug-visualizer/src/main.js` | Playground bootstrap — **needs overhaul** | Panel imports, `renderAllPanels()`, render loop | L1-71 (entire) |
| `debug-visualizer/src/panels/playground/game-setup.js` | **PRIMARY REPLACEMENT TARGET** | Wizard tabs, preset buttons, advanced controls | L1-411 (entire) |
| `debug-visualizer/src/controls/algorithm-test.js` | Preset definitions + rule senders — **keep & adapt** | `PRESETS`, `applyPreset()`, `sendNavRule()`, `sendInteractionRule()`, `sendRemovalRule()` | L1-179 (entire) |
| `debug-visualizer/src/panels/playground/spawn.js` | Spawn panel — **absorbed into Faction Node** | Spawn mode, faction, amount, spread | L1-147 |
| `debug-visualizer/src/panels/playground/aggro.js` | Aggro panel — **absorbed into Relationship Node** | Aggro mask matrix | L1-102 |
| `debug-visualizer/src/panels/playground/behavior.js` | Behavior panel — **absorbed into Tactical Node** | Faction + behavior type | L1-65 |
| `debug-visualizer/src/panels/playground/zones.js` | Zone panel — **keep for v2** | Zone modifiers | L1-110 |
| `debug-visualizer/src/panels/playground/terrain.js` | Terrain panel — **keep as paint mode** | Paint mode toggle, brush | L1-117 |
| `debug-visualizer/src/panels/playground/splitter.js` | Splitter panel — **defer to v2** | Faction split | L1-99 |

### Engine: ECS Components (Entity Properties)
| File | Purpose | Key Types | Relevant Lines |
|------|---------|-----------|----------------|
| `micro-core/src/components/stat_block.rs` | Anonymous stat array | `StatBlock([f32; 8])`, `MAX_STATS = 8`, `with_defaults(&[(usize, f32)])` | L17-43 |
| `micro-core/src/components/unit_class.rs` | Unit class identifier | `UnitClassId(u32)` — used for class-filtered InteractionRules | L22-29 |
| `micro-core/src/components/movement_config.rs` | Per-entity movement | `MovementConfig { max_speed, steering_factor, separation_radius, separation_weight, flow_weight }` | L14-26 |
| `micro-core/src/components/faction.rs` | Faction membership | `FactionId(u32)` | L1-30 |
| `micro-core/src/components/tactical.rs` | Tactical steering state | `TacticalState { direction, weight, engagement_range }`, `CombatState { last_damaged_tick }` | L23-46 |
| `micro-core/src/components/vision_radius.rs` | Vision range | `VisionRadius(f32)` — default 1000.0 | L3-10 |

### Engine: Rule Resources
| File | Purpose | Key Types | Relevant Lines |
|------|---------|-----------|----------------|
| `micro-core/src/rules/interaction.rs` | Combat rules | `InteractionRule { source_faction, target_faction, range, effects, source_class, target_class, range_stat_index, mitigation, cooldown_ticks, aoe, penetration }` | L22-73 |
| `micro-core/src/rules/interaction.rs` | Stat modifications | `StatEffect { stat_index, delta_per_second }` | L76-83 |
| `micro-core/src/rules/interaction.rs` | Damage mitigation | `MitigationRule { stat_index, mode: PercentReduction|FlatReduction }` | L88-104 |
| `micro-core/src/rules/navigation.rs` | Movement orders | `NavigationRule { follower_faction, target: NavigationTarget }` | L22-27 |
| `micro-core/src/rules/removal.rs` | Death conditions | `RemovalRule { stat_index, threshold, condition: LessOrEqual|GreaterOrEqual }` | L20-36 |
| `micro-core/src/rules/behavior.rs` | Faction behavior toggle | `FactionBehaviorMode { static_factions: HashSet<u32> }` | L17-22 |
| `micro-core/src/rules/aoe.rs` | AoE damage shapes | `AoeConfig { shape: Circle|Ellipse|ConvexPolygon, falloff: None|Linear|Quadratic }` | L20-76 |
| `micro-core/src/rules/aoe.rs` | Penetration | `PenetrationConfig { ray_width, max_targets, energy_model: Kinetic|Beam, absorption_stat_index }` | L226-265 |

### Engine: Configuration Resources
| File | Purpose | Key Types | Relevant Lines |
|------|---------|-----------|----------------|
| `micro-core/src/config/simulation.rs` | World settings | `SimulationConfig { world_width, world_height, initial_entity_count, flow_field_cell_size, initial_faction_count }` | L5-23 |
| `micro-core/src/config/buff.rs` | Buff system | `BuffConfig { movement_speed_stat, combat_damage_stat }`, `FactionBuffs { buffs: HashMap<u32, Vec<ActiveBuffGroup>> }`, `ActiveModifier { stat_index, modifier_type: Multiplier|FlatAdd, value }` | L8-20 (config), L38-44 (buffs), L167-182 (modifier) |
| `micro-core/src/config/zones.rs` | Zones + aggro | `AggroMaskRegistry { masks: HashMap<(u32,u32), bool> }`, `ZoneModifier { target_faction, x, y, radius, cost_modifier, ticks_remaining }` | L27-29 (aggro), L10-17 (zone) |
| `micro-core/src/config/unit_registry.rs` | Unit type defs | `UnitTypeRegistry { types: HashMap<u32, UnitTypeDef> }`, `UnitTypeDef { engagement_range, movement, behaviors: Vec<TacticalBehavior> }` | L58-61 (registry), L39-48 (typedef) |
| `micro-core/src/config/cooldown.rs` | Attack cooldowns | `CooldownTracker { cooldowns: HashMap<(u32, usize), u32> }` | L22-25 |

## Existing Contracts & Types

### Entity Spawn Bundle (what gets created per entity)
```rust
// From: micro-core/src/systems/ws_command.rs:L166-183
commands.spawn((
    EntityId { id: next_id.0 },
    Position { x, y },
    Velocity { dx, dy },
    FactionId(faction_id),
    StatBlock::with_defaults(&stats),
    VisionRadius::default(),
    default_mc,            // MovementConfig — hardcoded in spawn_wave handler!
    UnitClassId::default(), // Always 0 — no class assignment via WS yet!
    TacticalState::default(),
    CombatState::default(),
));
```

### InteractionRule — Full Shape
```rust
// From: micro-core/src/rules/interaction.rs:L22-73
pub struct InteractionRule {
    pub source_faction: u32,
    pub target_faction: u32,
    pub range: f32,
    pub effects: Vec<StatEffect>,
    pub source_class: Option<u32>,     // Filter by source unit class
    pub target_class: Option<u32>,     // Filter by target unit class
    pub range_stat_index: Option<usize>, // Dynamic range from stat
    pub mitigation: Option<MitigationRule>,
    pub cooldown_ticks: Option<u32>,
    pub aoe: Option<AoeConfig>,
    pub penetration: Option<PenetrationConfig>,
}
```

### NavigationTarget — Two Variants
```rust
// From: micro-core/src/bridges/zmq_protocol.rs (referenced by navigation.rs:L9)
pub enum NavigationTarget {
    Faction { faction_id: u32 },
    Waypoint { x: f32, y: f32 },
}
```

### AggroMask — Directional
```rust
// From: micro-core/src/config/zones.rs:L43-45
pub fn is_combat_allowed(&self, source: u32, target: u32) -> bool {
    *self.masks.get(&(source, target)).unwrap_or(&true) // default: combat allowed
}
```

## Integration Points

```
[Graph Compilation] Node Editor → compile()
    → generates: nav rules, interaction rules, removal rules, aggro masks, spawn configs
    → calls: sendCommand('kill_all') × N factions (via algorithm-test.js pattern)
    → calls: sendCommand('set_navigation', { rules })
    → calls: sendCommand('set_interaction', { rules })
    → calls: sendCommand('set_removal', { rules })
    → calls: sendCommand('set_aggro_mask', { ... }) × N pairs
    → 100ms delay
    → calls: sendCommand('spawn_wave', { ... }) × N factions × M unit types

[Preset Loading] PresetGallery → select preset
    → loads: Drawflow JSON graph (converted from PRESETS object)
    → OR calls: editor.import(presetGraph)
    → populates: node editor with pre-wired nodes

[Layout Bootstrap] playground-main.js::init()
    → replaces: sidebar pattern with overlay pattern (training.html reference)
    → creates: #node-editor-container (Drawflow mount point)
    → creates: #overlay-bottom-toolbar (node palette + sim controls)
    → creates: #overlay-side-cards (telemetry, inspector)

[CSS Integration] playground-overlay.css
    → extends: overlay.css (reuses .overlay-card, .overlay-top-bar, etc.)
    → adds: .node-editor-container, .drawflow-node overrides
    → drawflow base CSS overridden for glassmorphic theme
```

## Code Patterns in Use

- **Training overlay pattern:** `pointer-events: none` on wrapper, `auto` on cards. Fixed positioning at bottom corners. Glassmorphic `overlay-card` with blur(12px). Entry animation `overlaySlideIn`. Minimize/expand toggle via class swap (`overlay--expanded` ↔ `overlay--minimized`).

- **Panel registration (legacy):** Sidebar-bound `registerPanel() → renderAllPanels(container)`. The node editor **should NOT use this pattern** — it needs its own Drawflow-based initialization. Telemetry and Inspector panels can be ported to overlay cards.

- **Rule compilation pattern:** `applyPreset()` in algorithm-test.js: `kill_all` × N → `set_rules` → 100ms delay → `spawn_wave` × N. The node editor's `compile()` function should follow this exact sequence.

## Gotchas & Constraints Discovered

1. **`spawn_wave` doesn't support `class_id` or custom `MovementConfig`.** The WS handler hardcodes `UnitClassId::default()` and a fixed `MovementConfig { max_speed: 60, steering: 5, sep: 6, sep_weight: 1.5, flow: 1.0 }`. **To support the Unit Builder's Movement and Class nodes, the `spawn_wave` handler in `ws_command.rs` must be extended** to accept optional `class_id` and `movement` fields. This is a Rust-side change.

2. **`set_interaction` doesn't forward `source_class`, `target_class`, `mitigation`, `cooldown_ticks`, `aoe`, or `penetration` from WS.** The WS handler at L554-566 constructs InteractionRule with all optional fields set to `None`. **To support the Combat node's advanced features, the handler must deserialize these optional fields from the JSON payload.** This is another Rust-side gap.

3. **StatBlock indices are hard-wired in presets.** All existing presets use `stat_index: 0` for HP damage and death. If a Stat Node assigns a different index to HP, the death + interaction rules must use the matching index. The compiler must trace wires, not assume index 0 = HP.

4. **Drawflow CSS will conflict with project CSS.** Drawflow's default styles (`.drawflow`, `.drawflow-node`, `.drawflow .connection`) must be overridden to match the glassmorphic theme. The `drawflow.min.css` should be imported first, then project overrides applied. Key conflict areas: node backgrounds, connection line colors, port circle styles.

5. **Faction IDs must be stable across graph edits.** The engine uses `u32` faction IDs. If a user deletes and re-creates a faction node, the ID must not collide with IDs still in use by the engine (stale entities). Use `S.bumpNextFactionId()` pattern from state.js — monotonically increasing, never reused.

6. **Mobile UX requires a fallback.** Drawflow supports touch but node editing on small screens is poor UX. The mobile layout should show a **simplified list view** of the compiled rules (read-only summary), with the preset gallery for scenario selection. Full node editing is desktop-only.

7. **Aggro mask direction matters.** `AggroMaskRegistry.masks` uses `(u32, u32)` keys where `(0,1)` ≠ `(1,0)`. The Relationship node should set both directions (`a→b` AND `b→a`) for symmetric relationships. The `set_aggro_mask` command only sets one direction per call — the compiler needs to emit two commands per relationship.
