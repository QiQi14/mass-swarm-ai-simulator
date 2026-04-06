# Changelog for Task 05: Directive Executor & Engine Override Systems

## Work Completed
1. **Directive Executor System (`micro-core/src/systems/directive_executor.rs`)**:
   - Built the main `directive_executor_system` to consume `LatestDirective`.
   - Handled variants: `UpdateNavigation`, `TriggerFrenzy`, `Retreat`, `SetZoneModifier`, `SplitFaction`, `MergeFaction`, `SetAggroMask`.
   - Enforced Patch 1: Vaporization Guard via `latest.directive.take()`.
   - Enforced Patch 3: Ghost State Cleanup inside `MergeFaction` logic to purge dependent registries.
   - Enforced Patch 4: Quickselect with f32 sort `select_nth_unstable_by` for safe `SplitFaction` selection.
   - Included 22 unit tests meeting TDD requirements.

2. **Engine Override System (`micro-core/src/systems/engine_override.rs`)**:
   - Created isolated system for `EngineOverride` that applies pure velocity overriding.
   - Enforced countdown to removal, toggling `InterventionTracker.active`.
   - Integrated unit tests.

3. **Interaction Blinders (`micro-core/src/systems/interaction.rs`)**:
   - Pulled in `AggroMaskRegistry` resource and applied it in `interaction_system` to optionally block combat.

4. **Navigation Upgrade (`micro-core/src/rules/navigation.rs` & `micro-core/src/systems/movement.rs`)**:
   - Modernized `NavigationRule` enum to hold `NavigationTarget` enum instead of a rigid `u32` target.
   - Configured `movement_system` to fetch flow fields only when the target is `Faction`, resolving a direct vector toward `Waypoint` if the target is a coordinate.
   - Integrated `FactionSpeedBuffs` modifier to `mc.max_speed`.

5. **Moses Effect Guard (`micro-core/src/systems/flow_field_update.rs`)**:
   - Updated pathfinding flow core to inject active `ZoneModifiers` dynamically per rule onto the terrain map, routing around unit-added impassable terrain.
   - Added Patch 2: Moses Effect safeguard to prevent active modifiers from scaling or removing fully impassable areas (`current_cost == u16::MAX`).

## Validation
- Ran `cargo test` - **157 / 157 Tests Pass**, confirming all new logic is functional and correctly guards invariants.
