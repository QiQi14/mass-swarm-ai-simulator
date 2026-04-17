# Strategy Brief v3: Action Space Redesign — Final

## Design Constraints (from user)

1. **3 general unit lines:** Frontline (tanky), Midline (maneuver/support), Backline (range/DPS). But the system is context-agnostic — production can have any number of classes per game profile.
2. **Sub-faction targeting:** Playground already uses `inject_directive` + `SplitFaction` + `set_aggro_mask` for player control (see `playground_strategy_brief.md`). Brain must have parity with what human players can do.
3. **Kite at runtime:** Dynamic `TacticalBehavior::Kite` injection — not just aggro-off+waypoint. The tactical sensor already evaluates Kite behaviors from `UnitTypeRegistry` at 10 Hz.

---

## Engine Capability Inventory

### What exists today

| Capability | Mechanism | Runtime Mutable? | Via Directive? |
|-----------|-----------|:---:|:---:|
| Split by proximity | `SplitFaction { epicenter, percentage }` | ✅ | ✅ |
| Split by class | — | ❌ **missing** | ❌ |
| Passive (no combat) | `SetAggroMask { allow_combat: false }` | ✅ | ✅ |
| Aggressive (fight) | `SetAggroMask { allow_combat: true }` (default) | ✅ | ✅ |
| Kite (flee enemies) | `TacticalBehavior::Kite` in `UnitTypeRegistry` | ❌ spawn-time only | ❌ |
| PeelForAlly | `TacticalBehavior::PeelForAlly` in registry | ❌ spawn-time only | ❌ |
| Hold position | `FactionBehaviorMode.static_factions` | ✅ via WS | ❌ |
| Engagement range hold | `TacticalState.engagement_range` from UnitTypeRegistry | ❌ spawn-time only | ❌ |
| Retreat | `MacroDirective::Retreat` → Waypoint target | ✅ | ✅ partially |
| Zone modifier (attract/repel) | `SetZoneModifier { cost_modifier }` | ✅ | ✅ |
| Buff/skill activation | `ActivateBuff { modifiers, duration }` | ✅ | ✅ |

### What needs to be added

| Capability | Required Engine Change | Effort |
|-----------|----------------------|--------|
| Split by class | Add `class_filter: Option<u32>` to `SplitFaction` | 15 lines Rust |
| Runtime Kite | New directive: `SetTacticalBehavior { faction, behavior }` → mutates `UnitTypeRegistry` per-faction override | ~80 lines Rust |
| Runtime engagement range | Same directive as Kite — set class def's engagement_range at runtime | Included above |
| Waypoint → flow field | Fix `movement.rs` L102-108 | 10 lines Rust |

### How Runtime Kite Works

Currently, `TacticalBehavior::Kite` is configured at episode start via `UnitTypeDefinition.tactical_behaviors` and stored in the immutable `UnitTypeRegistry`. The `tactical_sensor_system` reads it every tick.

**The runtime injection path:**

```
New Directive:
    SetTacticalOverride {
        faction: u32,             // which faction/sub-faction to affect
        behavior: TacticalBehaviorPayload,  // Kite | PeelForAlly | None
    }

Executor:
    → Insert into new resource: FactionTacticalOverrides { HashMap<u32, Vec<TacticalBehavior>> }
    
Tactical Sensor System (modified lookup):
    1. Check FactionTacticalOverrides.get(entity.faction) first
    2. If override exists → use override behaviors
    3. If no override → fall back to UnitTypeRegistry behaviors (current logic)
    
MergeFaction cleanup:
    → FactionTacticalOverrides.remove(source_faction)
```

This is cleaner than mutating `UnitTypeRegistry` because:
- UnitTypeRegistry stays immutable (class definitions don't change mid-episode)
- Overrides are faction-scoped (only a sub-faction kites, not ALL class-1 globally)
- Cleanup is automatic on merge

The tactical sensor already does subsumption (highest weight wins). A `Kite { weight: 5.0 }` override on a sub-faction overrides any spawn-time behavior.

---

## Action Space v3 — The "General" Vocabulary

### Core Design Principle

The brain is "The General" — it must have **parity with what a human player can do in the Playground**. The playground brief shows that a human player can:

1. Set navigation targets (via Navigation nodes)
2. Split factions into sub-groups (via `split_faction` WS command)
3. Set aggro masks between factions (via `set_aggro_mask`)
4. Place zone modifiers (via `place_zone_modifier`)
5. Inject any `MacroDirective` (via `inject_directive`)

The action space must express all of these through a compact `MultiDiscrete` encoding.

### Encoding: `MultiDiscrete([N_actions, 2500, M_modifier])`

The key innovation: a **3rd modifier dimension** that carries context-dependent meaning per action type. This avoids burning action slots for variants (attract vs repel, class selection, playstyle).

> [!IMPORTANT]
> **How many modifier values?** The modifier dimension must support the largest variant set. With 3 unit classes + "all" = 4 split options, and 3 playstyles + "clear" = 4 playstyle options, **M = 4** is the minimum. Going to **M = 5** gives room for 1 future expansion with minimal RL overhead. I recommend **M = 4** for now — tighter is better for RL.

### Action Table

| Idx | Name | Spatial? | Modifier Meaning | Unlock | What it Does |
|-----|------|:---:|:---:|:---:|---|
| 0 | **Hold** | ❌ | — | 0 | Stop, suppress flow field |
| 1 | **AttackCoord** | ✅ | — | 0 | Navigate main force to coordinate via flow field |
| 2 | **ZoneModifier** | ✅ | 0=attract, 1=repel | 2 | Bias pathfinding cost map (merged Pheromone+Repellent) |
| 3 | **SplitToCoord** | ✅ | 0=all, 1=frontline, 2=midline, 3=backline | 5 | Class-filtered split + navigate to coord |
| 4 | **MergeBack** | ❌ | — | 5 | Recombine first sub-faction |
| 5 | **SetPlaystyle** | ❌ | 0=aggressive, 1=passive, 2=kite, 3=clear | 5 | Set sub-faction tactical behavior at runtime |
| 6 | **ActivateSkill** | ✅ | skill_index | 7+ | Trigger buff/ability from profile |
| 7 | **Retreat** | ✅ | — | 6 | Tactical withdrawal to coordinate (flee direction) |

### Modifier Detail

```
MultiDiscrete([8, 2500, 4])
              │   │     │
              │   │     └── dim 2: modifier (0-3, context-dependent)
              │   └── dim 1: spatial coordinate (50×50 grid, active cells only)
              └── dim 0: action type (8 actions)
```

**Modifier masking per action type:**

| Action | Valid Modifier Values | Semantic |
|--------|:---:|---|
| Hold | {0} | No modifier |
| AttackCoord | {0} | No modifier |
| ZoneModifier | {0, 1} | 0 = attract (cost −50), 1 = repel (cost +200) |
| SplitToCoord | {0, 1, 2, 3} | 0 = all classes, 1/2/3 = specific class line |
| MergeBack | {0} | No modifier |
| SetPlaystyle | {0, 1, 2, 3} | 0 = aggressive (default), 1 = passive (aggro off), 2 = kite, 3 = clear override |
| ActivateSkill | {0, …, min(3, N_skills-1)} | Skill index from profile |
| Retreat | {0} | No modifier |

### Action → Directive Mapping

```python
# ACTION 0: Hold
→ Hold { faction_id: brain_faction }

# ACTION 1: AttackCoord(x, y)
→ UpdateNavigation { follower: brain_faction, target: Waypoint(x, y) }
# NOTE: After flow field fix, this routes around walls via Dijkstra

# ACTION 2: ZoneModifier(x, y, modifier)
→ SetZoneModifier { target_faction: brain_faction, x, y, radius: 100,
                    cost_modifier: -50 if mod=0 else +200 }
# + replay last AttackCoord (navigation persistence)

# ACTION 3: SplitToCoord(x, y, modifier)
→ SplitFaction { source: brain, sub: next_sub_id, percentage: 0.3,
                 epicenter: (x, y), class_filter: None|Some(mod-1) }
→ UpdateNavigation { follower: sub_id, target: Waypoint(x, y) }

# ACTION 4: MergeBack
→ MergeFaction { source: first_active_sub, target: brain_faction }

# ACTION 5: SetPlaystyle(modifier)
→ if mod == 0: SetAggroMask { sub, enemies, allow: true }
               + SetTacticalOverride { sub, behavior: None }  // clear kite
→ if mod == 1: SetAggroMask { sub, enemies, allow: false }    // passive
→ if mod == 2: SetTacticalOverride { sub, behavior: Kite(trigger_radius=80, weight=5) }
→ if mod == 3: SetTacticalOverride { sub, behavior: None }    // clear override
               + SetAggroMask { sub, enemies, allow: true }

# ACTION 6: ActivateSkill(x, y, modifier)
→ ActivateBuff { faction: brain, modifiers: skills[mod], duration }

# ACTION 7: Retreat(x, y)
→ Retreat { faction: brain, retreat_x: x, retreat_y: y }
```

---

## Context-Agnostic Class Mapping

The brain sees modifier values 1/2/3 as "class line 0/1/2". The **game profile** (not the brain) defines what each class IS:

```json
// Profile A: Medieval
{ "class_0": "Knight",  "line": "frontline", "engagement_range": 0 }
{ "class_1": "Archer",  "line": "backline",  "engagement_range": 150 }
{ "class_2": "Cavalry", "line": "midline",   "engagement_range": 0 }

// Profile B: Sci-Fi  
{ "class_0": "Heavy Mech", "line": "frontline", "engagement_range": 0 }
{ "class_1": "Sniper Drone","line": "backline",  "engagement_range": 200 }
{ "class_2": "Scout Bike",  "line": "midline",   "engagement_range": 30 }
```

The brain doesn't need to know "frontline" vs "backline" as concepts — it learns from observation channels which class blob is WHERE and how STRONG it is (ch6/ch7 per-class density), then learns which modifier value = which blob through trial and error. This preserves context-agnosticism.

### Per-Class Observation Channels

The brain needs to SEE its classes separately to make class-aware split decisions:

| Channel | Content | Active | Padding |
|---------|---------|--------|---------|
| ch6 | **Friendly class_0 density** | Stage 5+ | 0.0 |
| ch7 | **Friendly class_1 density** | Stage 5+ | 0.0 |

Why only 2 class channels instead of 3? Because `ch0 - ch6 - ch7` = class_2 density (the remainder). The brain can infer the third class from the first two. This saves a channel slot.

If more than 3 classes exist in future profiles, we'd expand the observation or use a different encoding. But for the 3-line design, 2 additional channels suffice.

---

## How the Brain Composes Tactics

With this action vocabulary, here's how complex tactics emerge from action composition:

### "Ranger Kite" (Stage 7+, heterogeneous swarm)

```
Step 1: SplitToCoord(flank_point, mod=3)     → split all backline (rangers) to flank
Step 2: SetPlaystyle(mod=2)                   → kite mode on ranger sub-faction
Step 3: AttackCoord(enemy_center)             → main body charges frontline + midline
Step 4: (Rangers auto-kite: flee when enemies close, dealing DPS from range)
Step 5: MergeBack                              → recombine after enemy routed
```

### "Tank Screen + Ranged DPS" (Stage 7+)

```
Step 1: SplitToCoord(front_line, mod=1)       → split frontline (tanks) forward
Step 2: SetPlaystyle(mod=0)                   → aggressive (tanks charge)
Step 3: AttackCoord(behind_tanks)             → main body (ranged) holds behind tank line
Step 4: (Tanks absorb damage, ranged deals DPS from behind)
```

### "Passive Recon" (Stage 4+, fog)

```
Step 1: SplitToCoord(fog_area, mod=2)         → split midline (scouts) into fog
Step 2: SetPlaystyle(mod=1)                   → passive (scouts don't fight)
Step 3: (Wait for scouts to reveal fog → brain sees enemies on ch1/ch3)
Step 4: AttackCoord(revealed_target)          → main body attacks discovered target
Step 5: MergeBack                              → recombine scouts
```

### "Pheromone Path" (Stage 2)

```
Step 1: AttackCoord(ranger_position)          → flow field routes toward rangers
Step 2: ZoneModifier(safe_path, mod=0)        → attract pheromone on mud path
Step 3: (Flow field recalculates → routes through mud path, avoiding tank corridor)
Step 4: (Brain kills rangers from mud path)
```

---

## Implementation Impact

### New Rust Code Required

| # | Component | What Changes | Lines (est.) |
|---|-----------|-------------|:---:|
| 1 | `movement.rs` | Waypoint → flow field lookup | ~15 |
| 2 | `directives.rs` | Add `class_filter` to `SplitFaction` | ~5 |
| 3 | `directives.rs` | Add `SetTacticalOverride` variant | ~10 |
| 4 | `executor.rs` | `SplitFaction`: filter by `UnitClassId` in candidate query | ~15 |
| 5 | `executor.rs` | `SetTacticalOverride`: insert into new resource | ~20 |
| 6 | New resource | `FactionTacticalOverrides { HashMap<u32, Vec<TacticalBehavior>> }` | ~30 |
| 7 | `tactical_sensor.rs` | Check `FactionTacticalOverrides` before `UnitTypeRegistry` | ~15 |
| 8 | `executor.rs` | Cleanup: MergeFaction removes tactical overrides | ~3 |
| 9 | `state_vectorizer.rs` | Emit per-class density maps in ZMQ snapshot | ~40 |

**Total: ~153 lines of Rust** (small, well-scoped changes across existing systems)

### Python Code Required

| # | Component | What Changes |
|---|-----------|-------------|
| 10 | `spaces.py` | `MultiDiscrete([8, 2500, 4])`, rename actions |
| 11 | `actions.py` | Full rewrite of `multidiscrete_to_directives()` |
| 12 | `swarm_env.py` | Modifier-aware action masking |
| 13 | `vectorizer.py` | Per-class density channels (ch6/ch7) |
| 14 | `tactical_extractor.py` | Handle 3rd action dimension output |
| 15 | `curriculum.py` | Stage unlock table, action names |
| 16 | `rewards.py` | No change (rewards are action-agnostic) |

### Playground Alignment

The playground's General node (from `playground_strategy_brief.md`) will use the same 8-action vocabulary via `inject_directive`. The node's inference loop decodes `[action_type, coord, modifier]` → builds the same directives. Full parity between brain-in-training and brain-in-playground.

### Training Impact

> [!WARNING]
> **Full retrain required.** Action space changes from `[8, 2500]` → `[8, 2500, 4]`, observation ch6/ch7 semantics change, and actions 2-7 have different meanings. All checkpoints are invalidated.

Acceptable since current model can't solve Stage 2 (pheromone is non-functional due to Waypoint bug).

---

## Stage Unlock Order (Revised)

| Stage | New Actions Unlocked | Modifier Used |
|:---:|---|---|
| 0 | Hold, AttackCoord | — |
| 1 | — | — |
| 2 | **ZoneModifier** | attract/repel (mod 0/1) |
| 3 | — | — |
| 4 | — (fog only, no new actions) | — |
| 5 | **SplitToCoord**, **MergeBack**, **SetPlaystyle** | class filter (mod 0-3), playstyle (mod 0-3) |
| 6 | **Retreat** | — |
| 7+ | **ActivateSkill** | skill index |

---

## Summary of Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Pheromone + Repellent merge? | **✅ Yes → ZoneModifier** | Same directive, polarity via modifier. Frees 1 action slot. |
| Class-aware split? | **✅ Yes, via modifier dim** | `class_filter: Option<u32>` on SplitFaction. Modifier 0=all, 1/2/3=class line. |
| Playstyle control? | **✅ New action: SetPlaystyle** | 4 modes: aggressive, passive, kite, clear. Separate from SplitToCoord for recomposability. |
| Kite mechanism? | **✅ Runtime injection** | New `FactionTacticalOverrides` resource + `SetTacticalOverride` directive. Temporal sensor system checks overrides first. |
| Scout action? | **❌ Removed** | Replaced by SplitToCoord(midline) + SetPlaystyle(passive). Strictly more expressive. |
| How many classes in modifier? | **3 + "all" = 4 values** | Matches frontline/midline/backline paradigm. Context-agnostic via profile mapping. |
| Sub-faction targeting for SetPlaystyle? | **Targets most recent sub-faction** | With max 2 subs (current limit), unambiguous. Extend later if needed. |
| Action space dims? | **`MultiDiscrete([8, 2500, 4])`** | 8 actions × 50×50 grid × 4 modifiers. Clean, compact, maskable. |

---

## Ready for Planner

This strategy brief is complete. All three user questions answered, all engine code traced, and all design decisions documented with evidence. The next step is `/planner` to generate the implementation task DAG.
