# Rule: Flow Field Must Respect Fog of War Visibility

**Category:** Architecture, FlowField, Fog of War

## Context
The `flow_field_update_system` collected ALL entities of the target faction as
flow field goals — including enemies hidden in unvisited/fogged cells. This gave
the follower faction "omniscient" pathfinding, allowing them to navigate toward
enemies they couldn't see.

When all visible enemies were killed, entities continued pursuing invisible ones
instead of idling.

## Strict Directive
1. The flow field must ONLY use target entity positions that are in the **follower
   faction's visible cells** (from `FactionVisibility.visible`).
2. If no target entities are visible, the flow field must be **removed** from the
   registry (not left stale). This causes `macro_dir = Vec2::ZERO` in the movement
   system → entities idle.
3. The visibility check uses the follower→target mapping to determine WHOSE
   visibility grid to check (check the follower faction, not the target faction).

## Example
- **❌ Anti-pattern:** (omniscient flow field)
```rust
for (pos, faction) in query.iter() {
    if target_factions.contains(&faction.0) {
        goals.push(pos);  // Uses ALL enemies regardless of FoW
    }
}
```
- **✅ Best Practice:** (fog-filtered flow field)
```rust
for (pos, faction) in query.iter() {
    if !target_factions.contains(&faction.0) { continue; }
    let cell_idx = pos_to_cell(pos);
    let is_visible = followers.iter().any(|f| get_bit(visible[f], cell_idx));
    if is_visible {
        goals.push(pos);
    }
}
// No visible goals → remove flow field
if goals.is_empty() { registry.fields.remove(&target); }
```
