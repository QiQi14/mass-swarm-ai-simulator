---
Task_ID: task_07_ipc_visualizer_upgrades
Execution_Phase: Phase 3 (Sequential)
Model_Tier: standard
Target_Files:
  - micro-core/src/bridges/ws_protocol.rs
  - micro-core/src/systems/ws_sync.rs
  - micro-core/src/systems/ws_command.rs
  - debug-visualizer/visualizer.js
Dependencies:
  - task_05_interaction_removal_systems
  - task_06_flow_field_movement_spawning
Context_Bindings:
  - context/conventions
  - context/ipc-protocol
  - skills/rust-code-standards
---

# STRICT INSTRUCTIONS

Extend the IPC protocol for stat broadcasting and entity removal. Upgrade the Debug Visualizer with health bars, death animations, and per-faction behavior toggles.

**Read `implementation_plan.md` Contracts 8 and 10.**

## 1. Update `micro-core/src/bridges/ws_protocol.rs` [MODIFY]

- Add `pub stats: Vec<f32>` field to `EntityState` (it should already have `faction_id: u32` from Task 01).
- Add `#[serde(default)] pub removed: Vec<u32>` field to `WsMessage::SyncDelta`.

## 2. Update `micro-core/src/systems/ws_sync.rs` [MODIFY]

- Add `&StatBlock` to the change-detection query.
- Populate `stats: stat_block.0.to_vec()` in each `EntityState`.
- Add `Res<RemovalEvents>` (NOT `ResMut` — read only) to system params. Note: removal_system clears events at start of its tick, so ws_sync reads the current tick's removals.
- Actually: `RemovalEvents` should be drained by ws_sync. Change to `ResMut<RemovalEvents>`. After reading `removed_ids`, call `events.removed_ids.clear()`.
- Populate `removed: events.removed_ids.clone()` in `SyncDelta`, then clear the events vec.

## 3. Update `micro-core/src/systems/ws_command.rs` [MODIFY]

Add `set_faction_mode` command handler:
- Parse `faction_id: u32` and `mode: String` from params.
- Add `ResMut<FactionBehaviorMode>` to `ws_command_system` params (import from `crate::rules::FactionBehaviorMode`).
- When `mode == "static"`: insert `faction_id` into `FactionBehaviorMode::static_factions`.
- When `mode == "brain"`: remove `faction_id` from `FactionBehaviorMode::static_factions`.
- Log the mode change.

## 4. Update `debug-visualizer/visualizer.js` [MODIFY]

### 4a. Entity Data Parsing
- Store `stats` array from moved entities alongside existing entity data.
- Parse `removed` array from SyncDelta — for each removed ID:
  - Add to a `deathAnimations` list with timestamp and position.
  - Delete from `entities` Map.

### 4b. Health Bars
- If `ADAPTER_CONFIG.stats[0]` exists and `display === "bar"`:
  - Draw a small horizontal bar (width ~20px, height ~3px) centered above each entity circle.
  - Color: lerp from `color_high` (green, full health) to `color_low` (red, zero health) based on `stat[0]` value.
  - Only draw if stat[0] < 1.0 (don't clutter fully healthy entities).

### 4c. Death Animation
- Maintain a `deathAnimations` array: `{ x, y, startTime, factionId }`.
- In render loop: for each death animation:
  - Calculate elapsed time since `startTime`.
  - If < 500ms: draw an expanding ring (radius grows from entity size to 3× entity size) with fading opacity (1.0 → 0.0). Use the entity's faction color.
  - If ≥ 500ms: remove from array.

### 4d. Per-Faction Behavior Toggle
- In the controls panel (`.controls` section in HTML), dynamically add toggle buttons for each faction in `ADAPTER_CONFIG.factions`:
  - Button text: `"[Faction Name]: Static"` or `"[Faction Name]: Brain"`.
  - Default state: faction 1 starts as "Static", faction 0 starts as "Brain" (matching `FactionBehaviorMode::default()`).
  - On click: toggle the mode and send WS command:
    ```javascript
    sendCommand("set_faction_mode", { faction_id: factionId, mode: newMode });
    ```
  - Update button text to reflect current mode.
  - Style: use the faction color as button accent color.

### 4e. Telemetry Updates
- Replace hardcoded "Swarm: N" / "Defender: N" with dynamic per-faction counts using `ADAPTER_CONFIG.factions` names.

---

# Verification_Strategy
Test_Type: unit + manual_steps
Test_Stack: cargo test (Rust), browser (JS)
Acceptance_Criteria:
  - "SyncDelta JSON contains 'stats' array and 'removed' array"
  - "Visualizer renders health bars above entities"
  - "Removed entities disappear with fade animation"
  - "Telemetry shows faction counts based on adapter config"
  - "Per-faction behavior toggle buttons render in control panel"
  - "Clicking toggle sends set_faction_mode command and changes entity behavior"
Suggested_Test_Commands:
  - "cd micro-core && cargo test ws_sync"
  - "cd micro-core && cargo test ws_command"
Manual_Steps:
  - "Run micro-core, open debug-visualizer"
  - "Verify health bars render in correct colors"
  - "Click 'Brain' toggle for faction 1 (Defender) — defenders should start navigating"
  - "Click 'Static' toggle for faction 0 (Swarm) — swarm should revert to random drift"
  - "Wait for combat — verify entities disappear when stat[0] reaches 0"
