# Feature Ledger (Logic Ledger)

> A concise registry of implemented features. Each entry is 3-5 lines max.
> For deep context, follow the archive pointer.
>
> **Who updates this:** The Planner agent, at the START of each new planning session,
> summarizes the previous completed feature before planning the next one.

<!-- 
FORMAT for each entry:

### [Feature Name]
**Completed:** YYYY-MM-DD | **Archive:** `.agents/history/[folder]/`

[2-3 line summary: what it does, key design decisions, non-obvious behavior]

**Key files:** `path/to/file.ts`, `path/to/other.ts`  
**Depends on:** [other features, or "None"]
-->

---

### Phase 1 Micro-Phase 1: Minimal ECS Skeleton
**Completed:** 2026-04-03 | **Archive:** `.agents/history/20260403_171957_p1_mp1_rust_bevy_scaffold_minimal_ecs/`

Sets up headless Bevy 0.18 app running at 60 TPS with minimal ECS capabilities (Position, Velocity, Team) and basic movement/spawn logic. Serves as the foundation for bridges.

**Key files:** `micro-core/src/main.rs`, `micro-core/src/components/*.rs`, `micro-core/src/systems/*.rs`
**Depends on:** None

---

### Phase 1 Micro-Phase 2: WebSocket Bridge & Delta-Sync
**Completed:** 2026-04-03 | **Archive:** `.agents/history/20260404_095812_phase_1_micro_phase_2_websocket_bridge/`

Adds a tokio-powered WebSocket server (`ws_server.rs`) broadcasting entity delta-sync updates to connected browser clients. Introduces `BroadcastSender` resource, `ws_sync_system` (queries `Changed<Position>`), and `ws_protocol.rs` with `SyncDelta` message envelope. Non-blocking — runs in a background thread alongside the Bevy ECS loop.

**Key files:** `micro-core/src/bridges/ws_server.rs`, `micro-core/src/bridges/ws_protocol.rs`, `micro-core/src/systems/ws_sync.rs`
**Depends on:** Phase 1 MP1

---

### Phase 1 Micro-Phase 3: ZeroMQ Bridge + Stub AI Round-Trip
**Completed:** 2026-04-04 | **Archive:** `.agents/history/20260404_095812_phase_1_micro_phase_2_websocket_bridge/`

Adds the ZeroMQ REQ/REP AI bridge (`zmq_bridge/`) with a Bevy state machine (`SimState::Running`/`WaitingForAI`) to gate movement during AI inference. Background tokio thread handles async ZMQ I/O with timeout+fallback to HOLD. Python stub AI (`macro-brain/src/stub_ai.py`) proves the round-trip. `movement_system` is now gated behind `SimState::Running`.

**Key files:** `micro-core/src/bridges/zmq_bridge/`, `micro-core/src/bridges/zmq_protocol.rs`, `macro-brain/src/stub_ai.py`
**Depends on:** Phase 1 MP1, Phase 1 MP2

---

### Phase 1 Micro-Phase 4: Debug Visualizer + Bidirectional WS
**Completed:** 2026-04-04 | **Archive:** `.agents/history/20260404_115529_phase_1_micro_phase_4_debug_visualizer_bidirectional_ws/`

Browser-based debug dashboard (`debug-visualizer/`) with real-time entity rendering on HTML5 Canvas. Features: pan/zoom viewport with 100×100 grid, velocity vector overlay, click-to-spawn, Play/Pause toggle, step-mode (advance N ticks then auto-pause), speed multiplier. WS server upgraded for bidirectional communication — incoming commands parsed and executed on ECS via `ws_command_system`. Adds `SimPaused`, `SimSpeed`, `SimStepRemaining` resources. SyncDelta extended with velocity (`dx`/`dy`) data.

**Key files:** `debug-visualizer/index.html`, `debug-visualizer/style.css`, `debug-visualizer/visualizer.js`, `micro-core/src/systems/ws_command.rs`, `micro-core/src/bridges/ws_server.rs`
**Depends on:** Phase 1 MP1, Phase 1 MP2, Phase 1 MP3

---

### Phase 2 Cycle 1: Universal Core Algorithms (Tasks 01–08)
**Completed:** 2026-04-04 | **Archive:** `.agents/history/20260404_234812_phase_2_universal_core_algorithms/`

Context-agnostic refactor of all ECS components (FactionId replaces Team, StatBlock replaces Health). Spatial hash grid O(1) neighbor queries, Chamfer Dijkstra flow fields with FlowFieldRegistry, rule resources (InteractionRuleSet, NavigationRuleSet, RemovalRuleSet, FactionBehaviorMode), interaction/removal systems with zero-allocation disjoint queries, composite movement (flow field + Boids separation + wall-sliding), Fibonacci spiral spawning, IPC upgrades (ZmqBridgePlugin with SimState machine), integration stress test at 10K entities.

**Key files:** `micro-core/src/components/`, `micro-core/src/spatial/`, `micro-core/src/pathfinding/flow_field.rs`, `micro-core/src/rules/`, `micro-core/src/systems/`, `micro-core/src/bridges/zmq_bridge/`
**Depends on:** Phase 1

---

### Phase 2 Cycle 2: Debug Visualizer UX Refactor (Tasks 09–15)
**Completed:** 2026-04-05 | **Archive:** `.agents/history/20260405_223900_phase_2_debug_visualizer_ux_refactor/`

TerrainGrid resource with inverted integer cost model (hard costs for pathfinding, soft costs for movement speed). FactionVisibility resource with bit-packed fog of war (explored/visible grids per faction, wall-aware BFS). Terrain-aware flow field integration. Visibility IPC (WS streams + ZMQ filtering by fog). WS commands: Fibonacci wave spawning, batch terrain editing, scenario persistence, fog faction toggling. Visualizer UI: spawn tools, terrain paint mode, fog renderer. Final integration with SimState gating fixes.

**Key files:** `micro-core/src/terrain.rs`, `micro-core/src/visibility.rs`, `micro-core/src/systems/visibility.rs`, `micro-core/src/systems/flow_field_update.rs`, `debug-visualizer/visualizer.js`
**Depends on:** Phase 2 Cycle 1

---

### Phase 3: Multi-Master Arbitration & RL Training
**Completed:** 2026-04-06 | **Archive:** `.agents/history/20260406_181600_phase_3_multi_master_arbitration_rl_training/`

Multi-Master Arbitration pattern with 3 authority tiers (Engine > AI > Rules). `MacroDirective` enum for 8 strategic actions over ZMQ. `SwarmEnv` Gymnasium environment with `MaskablePPO` (sb3-contrib) training pipeline. 5-stage curriculum with mastery-based transitions, demotion safety net, and progressive action masking. Frenzy is a dual speed+damage buff with cooldown. 8 safety patches (Vaporization Guard, Moses Effect, Ghost State, f32 Sort Panic, Pacifist Flank, Dynamic Epicenter, Sub-Faction Desync, ZMQ Deadlock Guard).

**Key files:** `micro-core/src/bridges/zmq_protocol.rs`, `micro-core/src/systems/directive_executor.rs`, `micro-core/src/config.rs`, `macro-brain/src/env/swarm_env.py`, `macro-brain/src/training/curriculum.py`, `macro-brain/src/training/callbacks.py`, `macro-brain/src/env/rewards.py`
**Depends on:** Phase 2

---

### Decouple Game Mechanics (Context-Agnostic Refactor)
**Completed:** 2026-04-07 | **Archive:** `.agents/history/20260407_133007_decouple_game_mechanics/`

Refactored FactionId from string-based "swarm"/"defender" to numeric u32. Health replaced with anonymous StatBlock[8]. All game semantics (combat rules, removal thresholds, navigation targets) moved to config-driven rule resources loaded at runtime via the GameProfile JSON contract. Micro-Core now has zero knowledge of what games it runs.

**Key files:** `micro-core/src/components/faction.rs`, `micro-core/src/components/stat_block.rs`, `micro-core/src/rules/`, `macro-brain/src/config/game_profile.py`, `macro-brain/src/config/definitions.py`
**Depends on:** Phase 3

---

### File Splitting Refactor (Maintainability)
**Completed:** 2026-04-07 | **Archive:** `.agents/history/20260407_150245_unnamed_feature/`

Split all oversized source files to comply with 300-line convention. Rust: zmq_bridge/systems.rs (1098→3 files), zmq_protocol.rs (562→directory), directive_executor.rs (507→directory), config.rs (301→directory), flow_field_update.rs safety extraction. Python: game_profile.py definitions extraction, swarm_env.py actions extraction, curriculum.py callbacks split. JS/CSS: draw.js, controls.js, style.css all split into modular directories. Doc tests migrated for pure functions.

**Key files:** `micro-core/src/bridges/zmq_bridge/`, `micro-core/src/bridges/zmq_protocol/`, `micro-core/src/systems/directive_executor/`, `micro-core/src/config/`, `debug-visualizer/js/`, `debug-visualizer/css/`
**Depends on:** Decouple Game Mechanics

---

### Contextless Audit & Debug Visualizer Contract
**Completed:** 2026-04-07 | **Archive:** `.agents/history/20260407_172000_contextless_audit_debug_visualizer/`

Finalized decouple refactoring by removing hardcoded legacy fallback logic (navigation bidirectional chase and stat HP defaults) from Micro-Core. Spawning configurable via `SimulationConfig`. Python `GameProfile` now constructs rule sets dynamically during ZMQ resets. Debug visualizer extended with an 'Algorithm Test' panel (Presets, Manual Rules overriding via WS commands) for standalone UI testing minus Python logic.

**Key files:** `micro-core/src/rules/navigation.rs`, `micro-core/src/config/simulation.rs`, `micro-core/src/bridges/zmq_bridge/reset.rs`, `macro-brain/src/config/game_profile.py`, `debug-visualizer/js/controls/algorithm-test.js`
**Depends on:** File Splitting Refactor

---

### Phase 3.5: Training Pipeline Readiness
**Completed:** 2026-04-08 | **Archive:** `.agents/history/20260408_150643_unnamed_feature/`

Extracted bot strategy logic entirely into Python (BotController) to enforce context-agnostic Rust core. Implemented ZMQ Batch directive protocol. Built Training Run Manager, Profile Validator CLI, and train.sh for standardized logging. Established 5-stage curriculum with randomized procedural terrain and mixed bot heuristics.

**Key files:** `macro-brain/src/env/bot_controller.py`, `micro-core/src/systems/directive_executor/`, `train.sh`
**Depends on:** Contextless Audit & Debug Visualizer Contract

---

### Stage 1 Training (Initial Curriculum)
**Completed:** 2026-04-08 | **Archive:** `.agents/history/20260408_165805_start_training_stage_1/`

First training run with Stage 1 target-selection curriculum using old `Discrete(3)` action space (Hold/AttackNearest/AttackFurthest). Identified the oscillation bug where AttackFurthest causes swarm to get stuck between two groups. Superseded by the tactical curriculum.

**Key files:** `macro-brain/profiles/stage1_tactical.json` (deleted)
**Depends on:** Phase 3.5

---

### Tactical Decision-Making Training Curriculum
**Completed:** 2026-04-10 | **Archive:** `.agents/history/20260410_113140_tactical_decision_making_training_curriculum/`

Complete rewrite of the RL training pipeline for tactical intelligence. `MultiDiscrete([8, 2500])` action space with flattened spatial coordinate (no Frankenstein bug). 8-action vocabulary: Hold, AttackCoord, DropPheromone, DropRepellent, SplitToCoord, MergeBack, Retreat, Scout. All actions are **atomic primitives** — the model composes them into tactics (see "The General" principle in conventions.md). 8-stage curriculum: target selection → fog scouting → wall navigation → pheromone flow → flanking → scout+retreat → combined → randomized. Custom `TacticalExtractor` CNN+MLP feature extractor for mixed Dict observations. `LKPBuffer` for fog-of-war memory (decaying last-known enemy positions). Fixed 50×50 observation tensor with center-padding for variable map sizes. Fog-of-war grids added to Rust ZMQ state snapshot.

**Key files:** `macro-brain/src/env/spaces.py`, `macro-brain/src/env/actions.py`, `macro-brain/src/env/swarm_env.py`, `macro-brain/src/env/rewards.py`, `macro-brain/src/utils/vectorizer.py`, `macro-brain/src/utils/lkp_buffer.py`, `macro-brain/src/models/feature_extractor.py`, `macro-brain/src/training/curriculum.py`, `macro-brain/src/training/callbacks.py`, `macro-brain/src/training/train.py`, `macro-brain/profiles/tactical_curriculum.json`, `micro-core/src/bridges/zmq_protocol/types.rs`
**Depends on:** Phase 3.5

---

### Tactical Swarm ECP Observation Hardening
**Completed:** 2026-04-10 | **Archive:** `.agents/history/20260410_170700_tactical_ecp_hardening/`

Refactored Rust micro-core to compute HP/DPS-weighted threat density maps via the `FactionBuffs` system using `combat_damage_stat` multipliers. Python macro-brain upgraded to ingest `ch7` (Threat Density) instead of raw enemy count, and `LKPBuffer` tracks 2 memory channels. Summary vectors stripped out targeted absolute faction counts replacing them with normalized HP totals to prevent identification exploits. The MaskablePPO CNN inherently learns complex tactical scenarios (high DPS threat vs. low DPS tank bait).

**Key files:** `micro-core/src/systems/state_vectorizer.rs`, `macro-brain/src/utils/vectorizer.py`, `macro-brain/src/env/swarm_env.py`, `micro-core/src/bridges/zmq_bridge/systems.rs`
**Depends on:** Tactical Decision-Making Training Curriculum

---

### Randomized Faction Roles
**Completed:** 2026-04-10 | **Archive:** `.agents/history/20260410_222800_randomized_faction_roles/`

Randomizes Trap/Target faction IDs each episode (50% chance) to prevent the model from learning a static faction ID bias. Maintains 3 distinct factions for debuff mechanics, while relying on the faction-blind ECP heatmap to drive target selection.

**Key files:** `macro-brain/profiles/tactical_curriculum.json`, `macro-brain/src/training/curriculum.py`, `macro-brain/src/env/swarm_env.py`
**Depends on:** Tactical Swarm ECP Observation Hardening
