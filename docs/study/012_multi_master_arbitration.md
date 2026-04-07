# Study Notes: Multi-Master Arbitration

> **Problem:** When both a human (Debug Visualizer) and an AI (Python Macro-Brain) can modify the same simulation state, how do you prevent conflicts and ensure deterministic behavior?

---

## Authority Tiers

The system uses a strict 2-tier authority model:

| Tier | Source | Priority | Scope |
|------|--------|----------|-------|
| **Tier 1** (Engine Override) | Python AI via ZMQ | HIGH | Per-entity velocity override, zone modifiers, faction splits |
| **Tier 2** (Rule Modification) | Human via WebSocket | LOW | Navigation rules, spawn commands, terrain editing |

### Conflict Resolution
- **Same entity, same tick:** Tier 1 wins. Engine Override forces velocity regardless of rule-based movement.
- **Different scope:** No conflict. Human can paint terrain while AI directs entities — they operate on orthogonal state.

---

## The 8-Action Directive Vocabulary

The Python AI issues exactly one `MacroDirective` per evaluation cycle (~2 Hz):

| # | Action | Parameters | Effect |
|---|--------|-----------|--------|
| 0 | `Hold` | — | No-op: maintain current rules |
| 1 | `UpdateNavigation` | `follower_faction`, `target` (Faction or Waypoint) | Redirect a faction's flow field target |
| 2 | `TriggerFrenzy` | `faction`, `speed_multiplier`, `duration_ticks` | Temporary speed buff |
| 3 | `Retreat` | `faction`, `retreat_x`, `retreat_y` | Set waypoint to safe position |
| 4 | `SetZoneModifier` | `target_faction`, `x`, `y`, `radius`, `cost_modifier` | Attract/repel entities via cost overlay |
| 5 | `SplitFaction` | `source_faction`, `new_sub_faction`, `percentage`, `epicenter` | Divide faction for pincer maneuvers |
| 6 | `MergeFaction` | `source_faction`, `target_faction` | Reunite split sub-factions |
| 7 | `SetAggroMask` | `source_faction`, `target_faction`, `allow_combat` | Toggle combat between factions |

---

## Safety Patches

8 safety patches prevent RL exploitation and simulation corruption:

### P1: Vaporization Guard
**Problem:** If a directive persists across ticks, the executor applies it 60 times/second instead of once.
**Fix:** `latest_directive.take()` — consumed once, then `None`.

### P2: Moses Effect
**Problem:** Zone modifiers could delete permanent walls, breaking map geometry.
**Fix:** Cells with `hard_cost == u16::MAX` are skipped by all cost overlays.

### P3: Ghost State Cleanup
**Problem:** After `MergeFaction`, orphaned zone modifiers and speed buffs for the deleted sub-faction persist.
**Fix:** `MergeFaction` purges all state entries referencing the source faction.

### P4: f32 Sort Panic
**Problem:** `select_nth_unstable_by` with `partial_cmp` panics on NaN distances.
**Fix:** Use `partial_cmp().unwrap_or(Ordering::Equal)` — NaN treated as equal, preventing panic.

### P5: Pacifist Flank Block
**Problem:** Agent sends sub-faction to map corner for free flanking reward.
**Fix:** Distance cutoff + attenuation. See `docs/study/010_rl_training_methodology.md`.

### P6: Dynamic Epicenter
**Problem:** Hardcoded SplitFaction epicenter ignores actual entity positions.
**Fix:** Epicenter computed from density grid centroid of the source faction.

### P7: Sub-Faction Desync
**Problem:** Python tracks sub-factions in local state, desyncs from Rust ground truth.
**Fix:** Read `active_sub_factions` from Rust's `StateSnapshot` on every tick.

### P8: ZMQ Deadlock / Tick Swallowing
**Problem:** ZMQ timeout leaves socket in wrong state; missed ticks accumulate.
**Fix:** Timeout → disconnect/reconnect cycle + episode truncation.

---

## AiResponse Envelope

The ZMQ protocol uses a discriminated union for Python's response:

```json
// Normal directive
{
    "type": "directive",
    "directive": { "Hold": null }
}

// Environment reset (at episode start)
{
    "type": "reset_environment",
    "terrain": { "hard_costs": [...], "soft_costs": [...], "width": 50, "height": 50, "cell_size": 20.0 },
    "spawns": [{ "faction": 0, "count": 50, "x": 200.0, "y": 500.0 }]
}
```

### Legacy Fallback
If the JSON doesn't match `AiResponse`, the system attempts to parse it as a legacy `MacroAction`. This prevents breaking the bridge during incremental upgrades.

---

## Engine Override System

When the AI issues directives that require per-entity control (e.g., `Retreat` sets waypoints), the system inserts an `EngineOverride` component on affected entities:

```rust
#[derive(Component)]
pub struct EngineOverride {
    pub forced_velocity: Vec2,
    pub remaining_ticks: u32,
}
```

The `movement_system` uses `Without<EngineOverride>` in its query filter, ensuring overridden entities are excluded from normal steering. The `engine_override_system` handles them separately, counting down ticks and removing the component when expired.
