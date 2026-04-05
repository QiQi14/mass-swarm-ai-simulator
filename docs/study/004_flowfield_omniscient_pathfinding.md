# Bug Study: Omniscient Flow Field Ignores Fog of War

**Date:** 2026-04-05  
**Severity:** High (breaks information asymmetry — core gameplay mechanic)  
**System:** `micro-core/src/systems/flow_field_update.rs`  
**Tags:** `pathfinding`, `fog-of-war`, `game-design`, `information-asymmetry`

---

## 1. Symptom

Swarm entities (faction 0) moved toward Defender entities (faction 1) even when
the defenders were in unexplored/fogged areas. When all visible defenders were
killed, the swarm continued pursuing invisible ones instead of idling.

The FoW toggle confirmed defenders were in completely dark (unvisited) cells,
yet the swarm had flow field arrows pointing directly at them.

## 2. Investigation Process

### Step 1: Trace the flow field goal collection

```rust
// flow_field_update_system — THE BUG
let mut faction_goals: HashMap<u32, Vec<Vec2>> = HashMap::default();
for (pos, faction) in query.iter() {
    if target_factions.contains(&faction.0) {
        faction_goals.entry(faction.0)
            .or_default()
            .push(Vec2::new(pos.x, pos.y));  // ← Uses ALL enemies
    }
}
```

The system iterated ALL entities of the target faction and used their positions
as flow field goals. No visibility check whatsoever.

### Step 2: Understand the navigation data flow

```
NavigationRuleSet: { follower: 0, target: 1 }
                        ↓
flow_field_update_system:
  1. Collect ALL faction 1 positions as goals
  2. Run Dijkstra on 50×50 grid
  3. Store flow field in FlowFieldRegistry keyed by target faction (1)
                        ↓
movement_system:
  follow_map[faction 0] → target faction 1
  registry.fields[1].sample(current_pos) → direction toward ANY faction 1 entity
```

The flow field acts as a "god's eye view" — it knows where every enemy is,
regardless of fog state.

### Step 3: Design the fix

The flow field for target faction 1 should only include faction 1 entities that
are in the **follower faction 0's visible cells**. The visibility check is on the
FOLLOWER's grid, not the target's.

```
Corrected data flow:
  1. For each target faction entity, check if its cell is in the follower's visible grid
  2. Only include visible entities as goals
  3. If no goals → remove flow field → entities idle
```

## 3. Root Cause

The `flow_field_update_system` was designed before the fog of war system (Task 10)
existed. When FoW was added, the flow field was never updated to respect it. This is
a classic **cross-cutting concern** problem — adding FoW affects multiple systems
but the dependency wasn't tracked.

## 4. Fix

```rust
pub fn flow_field_update_system(
    // ... existing params ...
    visibility: Res<FactionVisibility>,   // ← NEW
) {
    // Build follower → target mapping
    let mut followers_by_target: HashMap<u32, Vec<u32>> = HashMap::default();
    for &(follower, target) in &follower_to_target {
        followers_by_target.entry(target).or_default().push(follower);
    }

    // Gather fog-filtered goals
    for (pos, faction) in query.iter() {
        if !target_factions.contains(&faction.0) { continue; }

        let cell_idx = pos_to_cell(pos);

        // Check if visible to ANY follower faction that targets this faction
        if let Some(followers) = followers_by_target.get(&faction.0) {
            let is_visible = followers.iter().any(|follower_fid| {
                visibility.visible.get(follower_fid)
                    .map_or(false, |grid| FactionVisibility::get_bit(grid, cell_idx))
            });
            if is_visible {
                faction_goals.entry(faction.0).or_default().push(pos);
            }
        }
    }

    // No visible goals → remove flow field (entities idle)
    for &target in &target_factions {
        if faction_goals.get(&target).map_or(true, |g| g.is_empty()) {
            registry.fields.remove(&target);
        }
    }
}
```

**Test added:**
```rust
#[test]
fn test_fog_of_war_filters_invisible_targets() {
    // Target at (500, 500), NOT marked visible for follower faction 0
    // → Flow field should NOT exist
    assert!(!reg.fields.contains_key(&1));
}
```

## 5. Lessons Learned

1. **Fog of War is a cross-cutting concern.** When adding FoW to a system, you must
   audit ALL systems that consume entity positions:
   - Flow field calculation ← this bug
   - ZMQ state snapshot (already filtered)
   - Interaction system (should entities interact through fog?)
   - Any future targeting/selection systems

2. **The follower's vision determines the flow field.** It's tempting to check the
   target's visibility, but that's backwards. The question is: "Can faction 0 SEE
   faction 1 entity X?" → check faction 0's visible grid at entity X's cell.

3. **"No goals" must actively remove the flow field.** An empty goals list should
   not leave a stale flow field from the previous calculation. Active removal
   (`registry.fields.remove()`) is needed so movement system gets `macro_dir = ZERO`.

4. **This is the difference between "works" and "correct."** The flow field worked
   perfectly — entities navigated around obstacles and reached targets. But it broke
   the game design contract by providing information that should be hidden.

## 6. Gameplay Impact

| Scenario | Before (Omniscient) | After (FoW-Aware) |
|----------|--------------------|--------------------|
| Enemies in fog | Swarm hunts them | Swarm idles |
| All visible enemies killed | Swarm chases hidden ones | Swarm stops, waits |
| Enemy enters vision | Already targeting | Flow field recalculates |
| No enemies at all | Zero-vector (correct) | Zero-vector (correct) |

This change is essential for training the ML macro-brain. The whole point of
information asymmetry is that the AI must make decisions under uncertainty —
exploring vs. exploiting. An omniscient flow field would make the exploration
problem trivially solvable.
