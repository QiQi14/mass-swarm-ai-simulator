# STRATEGY BRIEF: Real-World Adaptation & Mechanics Overhaul

## 1. Problem Classification
**Type:** Design, Architecture, and Engine Upgrade Diagnosis
**Goal:** Prepare the Tri-Node stack (Visualizer & Rust Micro-Core) for real-world application, playground interaction, and heterogeneous swarm mechanics (Stages 5-6 features).

---

## 2. Analysis & Recommendations

### A. Debug Visualizer Split: Training vs. Playground
The current visualizer is a single HTML canvas optimized for raw debugging. To support both ML researchers and Game Designers/QA, we must split it into two decoupled modes.

**Problem:** Mixed concerns clutter the UI and limit usability for non-developers.
**Solution:** Refactor into a tabbed layout or two separate routes (e.g., `index.html` and `playground.html`), backed by a modern lightweight framework (Vite/React or pure JS Modules) for better UI state management.

1. **Training Mode (View-Only / Analytics UI)**
   - **Focus:** Metrics, telemetry, and debugging.
   - **Capabilities:** Hide interactive spawn/control tools. Expose real-time data received from Python via WebSocket overlays.
   - **New Visuals:** Episode counters, rolling win rates, loss streaks, real-time reward charts. Flow-field vector rendering and fog-of-war memory (LKP) visualization.

2. **Playground Mode (Sandbox / Simulator)**
   - **Focus:** Demonstrations, QA testing, and tactical validation.
   - **Capabilities:** 
     - **Profile Loader:** UI to upload and parse `tactical_curriculum.json` and hot-reload the Rust core.
     - **Manual Control:** Allow a human player to take over `Faction 0`. Provide UI tools to select troops (drag box) and issue primitives (`AttackCoord`, `DropPheromone`, `Retreat` via mouse inputs).
     - **Web-Inference:** Integration of `onnxruntime-web` (Phase 5 goal) to load `.onnx` model checkpoints. A designer can play as Faction 1 against the Swarm ML model playing as Faction 0 entirely in-browser.

---

### B. Rust Micro-Core: Supporting Multiple Unit Types
Currently, the Rust ECS relies on **"Faction = Unit Type."** Interaction rules (`InteractionRuleSet`) dictate combat purely between `source_faction` and `target_faction`, using fixed ranges and flat DPS. 

**Problem:** We cannot natively support "Tanks" and "Snipers" in the same faction behaving differently without complex architectural hacks.
1. **Context-Agnostic Unit Types (`UnitClassId`)**
   - Introduce a `UnitClassId(u32)` component to entities.
   - The Rust Core will **not** know what a "Sniper" or "Tank" is. Instead, these classes are simply integers passed from the GameProfile JSON (via `UnitRegistry`) used to distinguish which interaction rules and movement configurations apply to which entity.

2. **Abstract Stat Math via `GameProfile`**
   - The engine uses `StatBlock([f32; 8])`, and it must remain completely ignorant of what these slots represent (HP, Energy Shield, Armor). 
   - Instead, we expand the `InteractionRule` payload in the GameProfile to allow complex abstract calculations. For instance, the profile can define a rule: `{"source_class": 1, "target_class": 2, "range_stat_index": 2, "mitigation_stat_index": 4, "effects": [...]}`. 

3. **`interaction.rs` Rule-Driven Overhaul**
   - **Dynamic Targeting:** The `InteractionRule` will carry an optional `range_stat_index`. If provided, `grid.query_radius` dynamically pulls the range from the specified index in the source entity's `StatBlock`.
   - **Abstract Mathematics:** Damage reduction (like Armor or Shields) isn't hardcoded as "subtract shielding first." Instead, we inject mathematical contracts (e.g., condition operators, multipliers) via the rules payload. The Rust core blindly executes the math operations on the requested stat indices.
   - **Timers/Cooldowns:** High-damage, slow-speed interactions will be handled by a generic `CooldownBlock` or `TickTimer` component. A given `UnitClassId` can have a specific rule dictating "apply effect only when timer reaches 0."

4. **Sub-Faction Automatic Micro-Control**
   - Since the RL model won't manually separate units, the Rust core's `DirectiveExecutor` must parse macro primitives (e.g. `AttackCoord`) and automatically assign unit classes to implicit behavior profiles based on their generic configuration properties defined in the Game Profile.

---

### C. Undiscovered Impact Areas (The Ripple Effect)
The shift to mixed unit swarms introduces side-effects across the broader Tri-Node architecture:

1. **Grand Tactical Focus & Observation Space**
   - **The Concern:** If the Brain faction introduces 4 unit types, does the RL model need density maps for *every* unit type (Observation Space Explosion)?
   - **The Correction:** NO. The RL model operates strictly at the **Grand Tactical** level. It does not micro-manage unit classes. 
   - **The Fix:** The Rust core will aggressively aggregate the dynamic unit stats (HP, DPS, Shield, Armor) into "stat brightness" (threat density) and project it onto the existing Observation Tensor channels (specifically ch7). The model just learns to match its "brightest blob" against the enemy's "brightest blob." Micro-control is delegated entirely to the Rust engine and predefined game logic.

2. **ZMQ Snapshot Size Limits**
   - Increasing the complexity of `state_snapshot` (more faction groups to separate out density maps) will strain the ZeroMQ JSON bridge limit. 
   - **The Fix:** It may necessitate accelerating the Phase 4 serialization upgrade (migrating from `serde_json` to `bincode` or `MessagePack`).

3. **Spatial Has Grid Bottleneck**
   - Currently `cell_size` is optimized for a uniform combat range (around 20-30 units). If an artillery unit has an attack range of 200 units, the query radius will span hundreds of cells, drastically hurting interaction O(K) performance. 
   - **The Fix:** A multi-layered spatial grid or a fallback spatial lookup approach for slow-firing long-range units.

---

## 3. Recommended Next Steps

1. **Action:** Approve the `UnitClassId` and `StatBlock` expansion in the Rust core as the foundational PR.
2. **Action:** Refactor `game_profile.json` (and `tactical_curriculum.json`) to define `unit_registry` rather than purely `faction_stats`.
3. **Action:** Transition the Debug Visualizer repository to a formal layout (e.g. Vite) to support the Playground tooling.

(User: Once reviewed, invoke `/planner` to convert this into implementation DAGs.)
