# Changelog: task_P13_squad_manager

## Touched Files
- `debug-visualizer/src/state.js` [MODIFIED] - Appended `squads` map registry and `activeSquadId` reference under `Selection State` and `Squad Registry`. Included `SquadInfo` typedef.
- `debug-visualizer/src/squads/squad-manager.js` [CREATED] - Full implementation of `createSquadFromSelection`, `disbandSquad`, `getSquadStats`, `setSquadOrder`, and `pruneDeadSquads`. Included `offsetColor` for dynamic sub-faction coloring.

## Contract Fulfillment
- Provided registry for tracking squad (sub-faction) information within the visualization state.
- Implemented squad creation from existing entity selections leveraging the engine's `split_faction` socket command, determining appropriate sub-faction epicenter and percentage mathematically.
- Extended disband capability via `merge_faction` back to the parent faction.
- Realtime `getSquadStats` computes dynamic sub-faction center of mass and health percentages directly iterating shared engine snapshot entities without server queries.
- Ensured automatic pruning of fully eliminated squads on update ticks via `pruneDeadSquads`.

## Deviations/Notes
- `offsetColor` is implemented locally in `squad-manager.js` using a purely local HSL calculation shifting color hue `(offsetIndex * 45) % 360` to provide consistent variance from the root without complex hex-conversion overhead handling.
- Requires `set_aggro_mask` or `inject_directive` hooks (expected in Task 14) for fully applying target interactions to newly segmented sub-factions.
