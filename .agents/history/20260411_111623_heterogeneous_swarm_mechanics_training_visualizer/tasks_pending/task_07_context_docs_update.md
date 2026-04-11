# Task 07: Context Documentation Update

**Task_ID:** `task_07_context_docs_update`
**Feature:** Heterogeneous Swarm Mechanics
**Execution_Phase:** 3 (Sequential — after T03 and T04)
**Model_Tier:** `basic`

## Target_Files
- `.agents/context/engine-mechanics.md` [MODIFY]
- `.agents/context/ipc-protocol.md` [MODIFY]

## Dependencies
- T03: Interaction system upgrade is complete
- T04: Spawn/reset wiring is complete

## Context_Bindings
None (documentation task)

## Strict_Instructions

### 1. Update `.agents/context/engine-mechanics.md`

#### 1a. Add New Section: "Unit Classes"

Add a new section after the existing "Components" section (or wherever the component documentation is):

```markdown
### Unit Classes

Entities carry a `UnitClassId(u32)` component. Default: 0 (generic).

The engine is **context-agnostic** — it doesn't know what class 0 or class 1 means.
The game profile defines the mapping (e.g., class 0 = "Infantry", class 1 = "Sniper").

UnitClassId is used by `InteractionRule` for class-specific combat targeting:
- `source_class: Option<u32>` — only fire from entities of this class
- `target_class: Option<u32>` — only hit entities of this class
- When `None`, the rule matches any class (backward compatible)
```

#### 1b. Update Combat System Section

Document the new mechanics:

**Dynamic Range:**
```markdown
### Dynamic Range

InteractionRules can use a stat from the source entity as the combat range:
- `range_stat_index: Option<usize>` — if set, `range = source.StatBlock[idx]`
- Falls back to the fixed `range` field if stat is missing
- Use case: Snipers (class with high stat[3]=200.0) vs Infantry (stat[3]=15.0)
```

**Mitigation:**
```markdown
### Stat-Driven Mitigation

InteractionRules can specify target-side damage mitigation:
- `mitigation.stat_index` — which stat on the TARGET provides mitigation
- `mitigation.mode`:
  - `PercentReduction`: `damage = base * (1.0 - target_stat.clamp(0..1))`
  - `FlatReduction`: `damage = (base.abs() - target_stat).max(0) * base.signum()`
- Use case: Tanks (stat[4]=0.5 → 50% damage reduction)
```

**Cooldowns:**
```markdown
### Interaction Cooldowns

InteractionRules can have per-entity cooldowns:
- `cooldown_ticks: Option<u32>` — after firing, entity waits N ticks before firing again
- Tracked by `CooldownTracker` resource (keyed by entity_id + rule_index)
- Cleared on environment reset
- Use case: Heavy artillery (fires every 120 ticks = 2 seconds)
```

#### 1c. Add Combat Math Example

```markdown
### Example: Heterogeneous Combat

Given game profile:
- Class 0 (Infantry): HP=100, Range=15, no mitigation
- Class 1 (Sniper): HP=40, Range(stat[3])=200, cooldown=120 ticks
- Class 2 (Tank): HP=300, Armor(stat[4])=0.5 (50% reduction)

Rules:
1. Infantry→Any: range=15, damage=-10/s, no class filter
2. Sniper→Any: range_stat=3, damage=-50/s, cooldown=120, source_class=1
3. Any→Tank: range=15, damage=-10/s, mitigation={stat:4, mode:PercentReduction}

Result: Sniper hits from 200 units away, deals 50 damage burst every 2 sec.
Tank takes 50% less damage from everything. Infantry is baseline.
```

### 2. Update `.agents/context/ipc-protocol.md`

#### 2a. Update Spawn Config

Document the new `unit_class_id` field in the spawn config:

```markdown
### SpawnConfig (expanded)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| faction_id | u32 | yes | — | Faction ownership |
| count | u32 | yes | — | Number to spawn |
| x, y | f32 | yes | — | Spawn center |
| spread | f32 | yes | — | Spawn radius |
| stats | SpawnStatEntry[] | no | [] | Initial stat values |
| unit_class_id | u32 | no | 0 | Unit class (0 = generic) |
```

#### 2b. Update Combat Rule Payload

Document the new optional fields:

```markdown
### CombatRulePayload (expanded)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| source_faction | u32 | yes | — | Who attacks |
| target_faction | u32 | yes | — | Who gets hit |
| range | f32 | yes | — | Fixed combat range |
| effects | StatEffect[] | yes | — | Stat modifications |
| source_class | u32? | no | null | Filter: source must be this class |
| target_class | u32? | no | null | Filter: target must be this class |
| range_stat_index | usize? | no | null | Source stat index for dynamic range |
| mitigation | MitigationPayload? | no | null | Target damage mitigation |
| cooldown_ticks | u32? | no | null | Per-entity cooldown between fires |

### MitigationPayload

| Field | Type | Description |
|-------|------|-------------|
| stat_index | usize | Target stat providing mitigation value |
| mode | string | "PercentReduction" or "FlatReduction" |
```

## Anti-Patterns
- ❌ Do NOT remove existing documentation — add to it
- ❌ Do NOT document Playground features — those are deferred
- ❌ Do NOT include code snippets from the implementation — document the contracts and behavior

## Verification_Strategy

```yaml
Test_Type: manual_steps
Acceptance_Criteria:
  - "engine-mechanics.md documents UnitClassId, dynamic range, mitigation, cooldowns"
  - "ipc-protocol.md documents expanded SpawnConfig and CombatRulePayload"
  - "No stale references to old-format-only rules"
  - "Example combat math is correct and matches the engine implementation"
  - "All sections use consistent formatting with existing docs"
```
