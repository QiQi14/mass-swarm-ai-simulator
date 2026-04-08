# Redesigning Stage 1 Curriculum for Strategic Consistency

Based on your feedback, it makes perfect sense to explicitly separate the concept of "skipping a turn" from "halting movement." By introducing both `Idle` and `Hold` as explicit standalone actions, the agent can actively choose whether to coast on its existing momentum or aggressively hit the brakes to re-group.

## Phase 1: Splitting `Idle` and `Hold` Directives

We will expand the game's action space from 8 to 9 total actions, shifting the action indices to permanently decouple the mechanics.

**1. `Idle` (The "Skip Turn" Action)**
- **Behavior:** Complete no-op. The swarm continues executing whatever flow field or navigation rule is already active without interruption.
- **Implementation:** Rust maps `MacroDirective::Idle` to `{ /* no-op */ }`.

**2. `Hold` (The "Brake/Halt" Action)**
- **Behavior:** Aggressively clears all active Navigation rules, forcing the swarm to hold its ground.
- **Implementation:** Rust maps `MacroDirective::Hold { faction_id: u32 }` to forcibly call `nav_rules.rules.remove(&FactionId(*faction_id))`.

**Required Code Patches:**
- Update `macro-brain/profiles/default_swarm_combat.json` to insert `Idle` at index 0 and shift all other actions up (total 9 actions).
- Update `macro-brain/src/env/actions.py` and `swarm_env.py` to map the expanded action space and produce `build_idle_directive()` and `build_hold_directive(faction_id)`.
- Update `micro-core/src/bridges/zmq_protocol/directives.rs` and `executor.rs` to support the new enum variants.
- Update `bot_controller.py` to correctly map its fallbacks.

## Phase 2: "Defeat in Detail" Stage 1 Curriculum

With `Hold` and `Navigate` fully functional, we will reconfigure the Stage 1 spawning map to implicitly teach Lanchester's Square Law (Defeat in Detail).

#### [MODIFY] macro-brain/src/training/curriculum.py
We will split the opponent count into two clusters with staggered Y-axis values:
- **Agent Swarm (50 units):** Spawns centrally `(X=250, Y=500)`
- **Enemy Bot (25 units):** Spawns in upper corner `(X=750, Y=200)` 
- **Enemy Bot (25 units):** Spawns in lower corner `(X=750, Y=800)`

**Outcome Matrix:**
1. **Agent strictly relies on `Idle` (Passive):** Both enemy groups charge straight in, smashing the Agent simultaneously. Symmetric 50v50 bloodbath, ~50% win rate. Agent fails to graduate.
2. **Agent actively forms a battle line using `Hold`:** Agent stands its ground, letting enemies collapse in uncoordinated waves.
3. **Agent actively intercepts using `Navigate` (Proactive):** The Agent steers its 50 units directly at the 25-unit upper cluster. The lower cluster is outmaneuvered and forced to chase. The Agent dynamically crushes the 25 bots, then violently wheels around to annihilate the stragglers. Near 100% win rate!

## User Review Required
> [!IMPORTANT]
> Acknowledged! I have updated the plan to officially partition and install `Idle` as the new baseline "skip turn" mechanic, turning `Hold` into the much-needed "Halt" command. If you approve this structure and the Stage 1 geometry, I will rewrite the stack and hit the launch sequence!
