# Strategy Brief: Playground Redesign — Dual-Builder Node System

## Problem Statement

The current playground uses a **sidebar accordion panel** pattern with 8+ panels of raw numeric inputs. Non-technical users must manually configure `stat_index`, `delta_per_second`, `faction_id`, `threshold`, `condition`, etc. — all developer-oriented abstractions that don't map to how users think about army composition and battle rules.

The user requests:
1. A **node-based visual editor** (Blender/UE Blueprint style)
2. Split into **Faction Builder** and **Unit Builder** contexts
3. Replace the sidebar with a **floating overlay layout** matching the training page

---

## Layout Decision: Floating Overlay (Not Sidebar)

### Training Page Analysis

The refactored `training.html` uses a **fullscreen canvas + floating overlay card** architecture:

```
┌─────────────────────────────────────────────────────┐
│  [Top Bar]  SWARMCONTROL              Stage 3   [−] │
├─────────────────────────────────────────────────────┤
│                                                     │
│              FULLSCREEN CANVAS                      │
│         (fixed position, 100vw × 100vh)             │
│                                                     │
│                                                     │
│  ┌──────── overlay-left-cluster ──────────┐         │
│  │ ┌─────────────┐ ┌──────────┐ ┌──────┐│  ┌─────┐│
│  │ │  Dashboard   │ │ ML Brain │ │ Ch.  ││  │Insp.││
│  │ │  (bottom-row)│ │ Stage    │ │Toggles│  │Tele.││
│  │ └─────────────┘ └──────────┘ └──────┘│  └─────┘│
│  └───────────────────────────────────────┘         │
└─────────────────────────────────────────────────────┘
```

Key characteristics:
- Cards use **`pointer-events: none`** on the wrapper, re-enabled on individual cards → map pan/zoom works through gaps
- **`position: fixed; bottom: 24px; left: 24px; right: 24px;`** for overlay wrapper
- Cards are `overlay-card` with glassmorphic `backdrop-filter: blur(12px)`
- Inspector card **floats near the selected entity** (dynamically positioned)
- Minimizable to a compact strip via toggle
- Mobile: bottom sheet replaces overlay

### Playground Layout Decision

**The playground should adopt the same floating overlay pattern**, replacing the legacy sidebar. The layout adapts for the node editor:

```
┌─────────────────────────────────────────────────────────────────────┐
│  [Top Bar]  SWARMCONTROL  v0.3.0    [Presets ▾] [▶ Launch] [⚙] [−] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                      FULLSCREEN CANVAS                              │
│              (simulation preview, live entities)                    │
│                                                                     │
│  ┌─ Node Editor Overlay ──────────────────────────────────────────┐ │
│  │                                                                │ │
│  │   ┌──────────┐      ┌──────────┐      ┌──────────┐            │ │
│  │   │ Faction A ├──────┤ Attack   ├──────┤ Faction B │            │ │
│  │   └────┬─────┘      └──────────┘      └──────────┘            │ │
│  │        │                                                       │ │
│  │        │    ┌──────────┐      ┌──────────┐                     │ │
│  │        └────┤ Navigate ├──────┤ Waypoint │                     │ │
│  │             └──────────┘      └──────────┘                     │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─ Bottom Toolbar ─────────────────────────────────────────────┐   │
│  │ [+ Faction] [+ Unit] [+ Combat] [+ Navigate] [+ Death]      │   │
│  │ [Terrain 🖌] [Sim Controls ⏯]                 [📐 Mini-map] │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ Compact Strip ──────────────┐               ┌── Side Cards ──┐ │
│  │ TPS: 1201 │ Tick: 4499 │ 98⚡ │               │ Telemetry      │ │
│  └──────────────────────────────┘               │ Entity Inspector│ │
│                                                  └────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

The node editor sits **above the canvas** as a semi-transparent overlay region. Users design rules on the node canvas, then press **▶ Launch** to compile and execute.

---

## Dual-Builder Node Architecture

The user's core insight: **Factions and Units are separate concepts.** A faction is a team with relationships. A unit is a template with stats and combat mechanics. This mirrors real game design:

- **Faction** = Team/Army (has allegiances, traits that affect its members)
- **Unit** = Soldier Template (has HP, damage, range, speed, death conditions)

### Complete Node System — Mapped to Engine

I traced every ECS component, rule type, and WS command in the Rust micro-core. Here's the complete node taxonomy, with engine mapping evidence.

---

### FACTION BUILDER

These nodes define **who exists** and **how teams relate to each other**.

#### 1. Faction Node (Source Node)

| Property | UI Widget | Engine Target |
|----------|-----------|---------------|
| Name | Text input | `ADAPTER_CONFIG.factions[id].name` (display only) |
| Color | Color picker | `ADAPTER_CONFIG.factions[id].color` (display only) |
| Spawn Count | Slider (10–1000) | `spawn_wave.amount` |
| Spawn Position | Click-on-map / XY | `spawn_wave.x, y` |
| Spawn Spread | Slider (0–200) | `spawn_wave.spread` |

**Output Ports:**
- `units` → connects to Unit nodes (defines what type of soldiers this faction spawns)
- `relationship` → connects to Relationship edges (who they fight/ally with)
- `trait` → connects to Faction Trait nodes (buffs/debuffs affecting all members)
- `general` → connects to General (Brain) node (assigns a trained AI to command this faction)

**Engine Mapping:** `spawn_wave { faction_id, amount, x, y, spread, stats }` — stats come from the connected Unit node.

#### 2. Relationship Node (Edge Node)

This is a **bi-directional** visual relationship between two factions.

| Property | UI Widget | Engine Target |
|----------|-----------|---------------|
| Type | Dropdown: Hostile / Neutral / Allied | `set_aggro_mask { source, target, allow_combat }` |

**Input Ports:**
- `faction_a` ← from Faction node
- `faction_b` ← from Faction node

**Engine Mapping:**
- Hostile → `set_aggro_mask(a→b, true)` + `set_aggro_mask(b→a, true)`
- Neutral → `set_aggro_mask(a→b, false)` + `set_aggro_mask(b→a, false)`
- Allied → `set_aggro_mask(a→b, false)` + `set_aggro_mask(b→a, false)` + future formation bonuses


#### 3. Faction Trait Node (Modifier Node)

Represents a faction-wide buff/debuff that modifies connected units' stats.

| Property | UI Widget | Engine Target |
|----------|-----------|---------------|
| Trait Name | Text label | Display only |
| Modifier Type | Dropdown: Multiplier / FlatAdd | `BuffConfig → ModifierType` |
| Target Stat | Dropdown: HP / Speed / Damage / etc | `ActiveModifier.stat_index` |
| Value | Slider | `ActiveModifier.value` |
| Duration | Slider (ticks) or ∞ | `ActiveBuffGroup.remaining_ticks` |

**Input Port:** `applies-to` ← from Faction node
**Output Port:** `affects-unit` → to Unit node's stat (visual only — shows which stat is modified)

**Engine Mapping:** `FactionBuffs.buffs[faction_id].push(ActiveBuffGroup { modifiers, remaining_ticks, targets: Some(vec![]) })` — affects all units in faction.

#### 4. General Node (Brain / AI Commander)

Assigns a **trained ML brain** to command a faction's strategic decisions at runtime. This is the bridge between the Training page (where brains are trained) and the Playground (where they fight).

The engine architecture has three tiers of control:
1. **Manual rules** (Navigation/Combat/Death nodes) — static, set once at launch
2. **Trained brain** (General node) — dynamic, issues `MacroDirective` every N ticks
3. **Manual + brain hybrid** — brain overrides navigation/buffs while static combat rules remain

When a General node is connected, the brain **replaces manual Navigation nodes** for that faction. The brain dynamically issues `UpdateNavigation`, `Retreat`, `SetZoneModifier`, `SplitFaction`, `ActivateBuff` etc. — the same 8-action vocabulary used during training.

| Property | UI Widget | Engine Target |
|----------|-----------|---------------|
| Brain Model | File picker / dropdown of saved models | `.onnx` or `.pt` file path |
| Decision Interval | Slider (10–60 ticks, default: 30) | How often the brain observes + acts |
| Mode | Toggle: ONNX.js (client) / Python ZMQ (server) | Execution backend |

**Input Port:** `faction` ← from Faction node's `general` output

**How it works at runtime:**

```
Every N ticks:
  1. Build state snapshot for this faction (entity positions, stats, density maps)
  2. Run inference:
     - ONNX.js mode: model.run(observation) in browser → action tensor
     - Python mode: POST observation to local Python server → MacroDirective JSON
  3. Decode action → MacroDirective variant
  4. Execute via inject_directive WS command
```

**Engine Mapping:**
- Uses existing `inject_directive` WS command → `LatestDirective.directives`
- The `directive_executor_system` then processes the directive (same path as ZMQ Python brain)
- State observation reuses `build_state_snapshot()` output from `ws_sync` (`ml_brain` field in tick payload)

**Why inside Faction, not global?**
- The engine's `ai_trigger_system` currently hardcodes `brain_faction = 0` (only one brain, one faction)
- The General node unlocks **multi-brain scenarios**: Faction A has trained brain vs Faction B has different brain vs Faction C is manual
- Each General node runs its own inference loop independently, issuing `inject_directive` with faction-scoped directives

**UI Design:**
- The node visually shows a 🧠 brain icon with a model name label
- When connected, the Faction node shows a small brain badge
- A pulsing indicator shows when the brain is actively issuing directives
- If no model is loaded, the node shows "No Brain — Manual Mode" in muted text

**Model sources:**
- Exported from Training page → saved to `localStorage` or `IndexedDB`
- Uploaded `.onnx` file from disk
- Built-in demo models ("Aggressive", "Defensive", "Flanker") shipped with presets

#### 5. Navigation Node

Defines how a faction's units move. Simple drag-and-connect. **Ignored at runtime if a General node is connected** (the brain handles navigation dynamically).

| Property | UI Widget | Engine Target |
|----------|-----------|---------------|
| (auto-configured from connections) | — | — |

**Input Port:** `follower` ← from Faction node
**Target Port:** either `target_faction` ← from another Faction node, OR `waypoint` ← from Waypoint node

**Engine Mapping:** `set_navigation { rules: [{ follower_faction, target: { type: "Faction"|"Waypoint", ... } }] }`

#### 6. Waypoint Node (Positional Marker)

| Property | UI Widget | Engine Target |
|----------|-----------|---------------|
| Position | Click-on-map / XY | `NavigationTarget::Waypoint { x, y }` |
| Icon | Visual pin on canvas | Display only |

**Output Port:** `position` → connects to Navigation node's target

---

### UNIT BUILDER

These nodes define **what soldiers can do** — their stats, combat mechanics, and death conditions. The key conceptual mapping to the engine:

- **StatBlock**: An array of 8 floats (`[f32; 8]`). The engine doesn't know what each index means. The Unit Builder gives them names.
- **UnitClassId**: A `u32` identifier. Different classes can have different combat rules (`source_class`/`target_class` filtering on `InteractionRule`).
- **MovementConfig**: Per-entity speed, steering, separation. Different unit types move differently.

#### 7. Unit Node (Root Node)

| Property | UI Widget | Engine Target |
|----------|-----------|---------------|
| Name | Text input | Display only (maps to `class_id` label) |
| Class ID | Auto-assigned | `UnitClassId(u32)` |

**Input Ports:**
- `from-faction` ← from Faction node's `units` output (which faction spawns this unit)
- `stats` ← from Stat nodes
- `combat` ← from Combat nodes
- `death` ← from Death node

**Output:** Compiles into the complete entity spawn bundle: `(EntityId, Position, Velocity, FactionId, StatBlock, VisionRadius, MovementConfig, UnitClassId, TacticalState, CombatState)`

#### 8. Stat Node

Each Stat node defines ONE named stat in the StatBlock.

| Property | UI Widget | Engine Target |
|----------|-----------|---------------|
| Label | Text input: "HP", "Armor", "Mana" | Display only (user naming) |
| Stat Index | Auto-assigned (0–7) | `StatBlock[index]` |
| Initial Value | Slider | `spawn_wave.stats[{ index, value }]` |

**Output Port:** `value` → connects to:
- Unit node's `stats` input
- Combat node's `damage-stat` input (to use this stat for damage calculation)
- Death node's `check-stat` input (to use this stat for death threshold)
- Faction Trait node's `affects-unit` (visual feedback for what the trait modifies)

**Engine Mapping:**
- `spawn_wave.stats: [{ index: stat.stat_index, value: stat.initial_value }]`
- MAX_STATS = 8 → maximum 8 Stat nodes per unit

**Default presets:** "HP" (index 0, value 100), "Armor" (index 1, value 0), "Speed" (stat-driven movement)

#### 9. Combat Node

Defines how this unit attacks enemies. Maps to one `InteractionRule`.

| Property | UI Widget | Engine Target |
|----------|-----------|---------------|
| Attack Type | Preset: Melee / Ranged / Siege | Presets set range + damage |
| Damage | Slider or Preset (Light/Normal/Heavy) | `StatEffect.delta_per_second` |
| Range | Slider or Preset (Close/Mid/Far) | `InteractionRule.range` |
| Cooldown | Slider (0 = continuous) | `InteractionRule.cooldown_ticks` |

**Advanced sub-nodes (optional plugs on Combat node):**

| Sub-port | UI Widget | Engine Target |
|----------|-----------|---------------|
| `damage-stat` | ← from Stat node | `StatEffect.stat_index` (which stat takes damage) |
| `mitigation` | Toggle: % or Flat | `MitigationRule { stat_index, mode }` |
| `aoe` | Toggle + shape selector | `AoeConfig { shape, falloff }` |
| `penetration` | Toggle + energy slider | `PenetrationConfig { ray_width, energy_model }` |

**Input Ports:**
- `attacker` ← from Unit node (this unit's class becomes `source_class`)
- `target` ← from another Unit node or Faction node (becomes `target_faction` / `target_class`)

**Engine Mapping:** `set_interaction { rules: [{ source_faction, target_faction, range, effects, source_class, target_class, mitigation, cooldown_ticks, aoe, penetration }] }`

The UI hides the complexity: "Melee" preset = `{ range: 15, effects: [{ stat_index: 0, delta_per_second: -10 }], cooldown_ticks: null }`. The user just clicks "Melee" and wires things together.

#### 10. Movement Node

Per-unit-type movement configuration.

| Property | UI Widget | Engine Target |
|----------|-----------|---------------|
| Speed | Preset: Slow/Normal/Fast | `MovementConfig.max_speed` |
| Steering | Slider | `MovementConfig.steering_factor` |
| Separation | Slider | `MovementConfig.separation_radius + weight` |
| Engagement Range | Slider | `UnitTypeDef.engagement_range` |

**Input Port:** `unit` ← from Unit node

**Engine Mapping:** `MovementConfig` component on the spawned entity. Also feeds into `UnitTypeRegistry.types[class_id].engagement_range`.

#### 11. Death Node (End Node)

Defines when units are removed from simulation.

| Property | UI Widget | Engine Target |
|----------|-----------|---------------|
| Condition | Dropdown: ≤ / ≥ | `RemovalCondition::LessOrEqual` / `GreaterOrEqual` |
| Threshold | Slider (default: 0) | `RemovalRule.threshold` |

**Input Ports:**
- `check-stat` ← from Stat node (which stat triggers death) → `RemovalRule.stat_index`

**Engine Mapping:** `set_removal { rules: [{ stat_index, threshold, condition }] }`

Default: wire HP stat → Death node with ≤ 0 threshold. This means "die when HP reaches 0".

#### 12. Tactical Behavior Node (Advanced)

Optional per-class tactical override.

| Property | UI Widget | Engine Target |
|----------|-----------|---------------|
| Behavior | Dropdown: Kite / PeelForAlly | `TacticalBehavior` enum |
| Trigger Radius | Slider | `Kite.trigger_radius` or `PeelForAlly.search_radius` |
| Weight | Slider | Priority weight |

**Input Port:** `unit` ← from Unit node

**Engine Mapping:** `UnitTypeRegistry.types[class_id].behaviors`

---

## Missing Node Analysis

After tracing every WS command, ECS component, and Bevy resource, here are engine capabilities that **should** have nodes but aren't covered by the user's initial draft:

| Engine Capability | Node Needed? | Rationale |
|------------------|-------------|-----------|
| `set_faction_mode` (static/brain) | ❌ No | Training-only concept. Playground always uses flow fields |
| `set_engine_override` | ❌ No | Debug-only direct velocity injection |
| `set_fog_faction` | ❌ No | Observation layer, not a rule |
| `set_terrain` / `clear_terrain` | ❌ Keep as paint mode | Already well-designed for non-tech users |
| `place_zone_modifier` | Via General node | Brain issues `SetZoneModifier` directives autonomously |
| `split_faction` / `merge_faction` | Via General node | Brain issues `SplitFaction`/`MergeFaction` autonomously |
| `inject_directive` | ✅ Used by General node | The General node's runtime loop uses this to inject brain decisions |
| `set_speed` | ❌ No | Global sim speed, belongs in toolbar |
| `save_scenario` / `load_scenario` | Via Drawflow export/import | Free with library |
| `VisionRadius` | Later | All entities use default 1000.0. Add when Fog-of-War is exposed |

**Conclusion:** The 12 node types above fully cover the engine's playground-relevant capabilities. The General node unlocks the full `MacroDirective` vocabulary (zone modifiers, faction splitting, buffs) — these don't need separate manual nodes since the trained brain handles them autonomously.

---

## Library Recommendation: Drawflow

**Confirmed: Drawflow** remains the best fit.

- Zero dependencies → matches vanilla JS stack
- HTML-based nodes → reuse glassmorphic `overlay-card` CSS
- `df-*` attributes → auto-sync node data to model
- Export/Import JSON → free scenario save/load
- 4KB gzipped → negligible bundle impact

---

## Graph-to-Command Compilation

When user clicks **▶ Launch**, the node graph compiles into existing WS commands:

```
Phase 1: Collect
  ├── All Faction nodes → spawn configs
  ├── All Unit nodes → stat bundles per faction
  ├── All Combat nodes → InteractionRules
  ├── All Navigation nodes → NavigationRules (skip if General connected)
  ├── All Death nodes → RemovalRules
  ├── All Relationship nodes → AggroMasks
  ├── All Movement nodes → MovementConfigs
  └── All General nodes → brain configs (model path, interval, faction binding)

Phase 2: Clear
  ├── kill_all(faction_0)
  ├── kill_all(faction_1)
  └── kill_all(faction_2)

Phase 3: Rules
  ├── set_navigation({ rules })  ← only for factions WITHOUT General nodes
  ├── set_interaction({ rules })
  ├── set_removal({ rules })
  └── set_aggro_mask({ ... }) × N pairs

Phase 4: Spawn (100ms delay after rules)
  └── spawn_wave({ faction_id, amount, x, y, spread, stats }) × N factions

Phase 5: Brain Init
  └── For each General node:
      ├── Load ONNX model (or connect to Python ZMQ)
      ├── Start inference loop (setInterval every N ticks)
      └── First inference → inject_directive

Phase 6: Resume
  └── toggle_sim (if paused)
```

This extends the existing `applyPreset()` pipeline in `algorithm-test.js` with a brain initialization phase.

---

## Preset Gallery (Splash Overlay)

On first load (or via toolbar button), display a **fullscreen Blender-style splash** with preset scenario cards:

```
┌─────────────────────────────────────────────────────┐
│                   SELECT A SCENARIO                 │
│                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │    ⚔️        │  │    🔺       │  │    🎯       │ │
│  │  Swarm vs    │  │  3-Faction  │  │  Ranged vs  │ │
│  │  Defender    │  │  Melee      │  │  Melee      │ │
│  │             │  │             │  │             │ │
│  │ 500 vs 100  │  │ 3×100 FFAll │  │ 200 vs 200  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
│                                                     │
│  ┌─────────────┐  ┌─────────────┐                   │
│  │    🛡️       │  │    +++      │                   │
│  │  Tank Screen │  │  Blank      │                   │
│  │             │  │  Canvas     │                   │
│  │ 300+100+200 │  │             │                   │
│  └─────────────┘  └─────────────┘                   │
│                                                     │
│              [ Create from Scratch ]                │
└─────────────────────────────────────────────────────┘
```

- Each preset card loads a pre-built Drawflow JSON graph
- "Create from Scratch" opens blank node editor
- Uses `stage-modal` CSS from training page (glassmorphic dialog)

---

## Implementation Phasing

### Phase 1: Foundation (Core)
1. Install Drawflow, create node editor container
2. Implement Faction Node + Unit Node + Stat Node + Death Node
3. Basic graph-to-command compiler
4. Replace sidebar with floating overlay layout
5. Preset gallery splash

### Phase 2: Combat & Navigation
6. Combat Node with presets (Melee/Ranged/Siege)
7. Navigation Node + Waypoint Node
8. Relationship Node (aggro masks)
9. Movement Node

### Phase 3: Brain & Advanced
10. General (Brain) Node — ONNX.js client-side inference
11. Brain inference loop + `inject_directive` integration
12. Faction Trait Node (buff/debuff)
13. Tactical Behavior Node
14. Combat sub-nodes (AoE, Penetration, Mitigation)

---

## Key Constraints

1. **StatBlock is anonymous [f32; 8].** The node editor gives stats human names but serializes to index-based format. The Stat node must track its index (0–7) and ensure uniqueness per Unit.

2. **UnitClassId enables class-filtered rules.** When a Combat node links Unit-A → Unit-B, it generates `source_class: A.class_id, target_class: B.class_id` on the InteractionRule. This is how "snipers damage only infantry" works.

3. **Faction ≠ Unit.** One Faction can spawn multiple Unit types (e.g., Faction "Army" spawns both "Infantry" and "Sniper" units). The spawn_wave command needs to be called N times per faction, once per unit type.

4. **MovementConfig is per-entity, not per-faction.** Different unit types in the same faction can have different speeds. The Movement node attaches to the Unit node, not the Faction node.

5. **AggroMask is directional.** `is_combat_allowed(0, 1)` and `is_combat_allowed(1, 0)` are independent. The Relationship node should set both directions symmetrically in most cases, but advanced users might need asymmetric.

6. **The engine currently doesn't send class_id or movement config in spawn_wave.** The WS command handler uses `UnitClassId::default()` and a hardcoded `MovementConfig`. This is a gap — the node editor will need either: (a) enhanced spawn_wave to accept class + movement, or (b) a new WS command to register unit types. **This is a known limitation that must be resolved during implementation.**

7. **Brain is currently hardcoded to faction 0.** The engine's `ai_trigger_system` sends state snapshots only for faction 0 (`let brain_faction = 0u32;` in `systems.rs:L78`). The General node's client-side inference bypasses this limitation entirely — it reads the `ml_brain` observation data from the WS tick payload and runs its own inference. For multi-brain scenarios, the observation builder may need a Rust-side enhancement to support per-faction snapshots.

8. **General node supersedes Navigation nodes.** When a General node is wired to a faction, any connected Navigation nodes for that faction are **ignored at compile time**. The brain dynamically issues `UpdateNavigation` directives — static nav rules would conflict. The UI should visually dim/disable Navigation connections when a General is present.

9. **ONNX.js vs Python ZMQ tradeoff.** Client-side (ONNX.js) is zero-latency and works offline, ideal for playground demos. Python ZMQ mode reuses the training infrastructure but requires the Python server to be running. The General node should default to ONNX.js for simplicity, with a toggle for advanced users. Model export from Training page → ONNX format → IndexedDB storage is the pipeline.

10. **`inject_directive` is the integration point.** The General node injects decisions via `sendCommand('inject_directive', { directive: {...} })`. This feeds into `LatestDirective.directives` → `directive_executor_system`, the same execution path used by the Python ZMQ brain. No engine changes needed for basic brain support.
