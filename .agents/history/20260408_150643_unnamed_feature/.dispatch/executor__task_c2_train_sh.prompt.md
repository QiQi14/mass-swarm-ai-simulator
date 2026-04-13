# AGENT ROLE: EXECUTION SPECIALIST

You are an **Execution Specialist** in a multi-agent DAG workflow.
You have been assigned ONE specific task. You implement it with surgical precision.

---

## Your Assignment

| Field   | Value |
|---------|-------|
| Task ID | `task_c2_train_sh` |
| Feature | Unnamed Feature |
| Tier    | basic |

---

## ⛔ MANDATORY PROCESS — ALL TIERS (DO NOT SKIP)

> **These rules apply to EVERY executor, regardless of tier. Violating them
> causes an automatic QA FAIL and project BLOCK.**

### Rule 1: Scope Isolation
- You may ONLY create or modify files listed in `Target_Files` in your Task Brief.
- If a file must be changed but is NOT in `Target_Files`, **STOP and report the gap** — do NOT modify it.
- NEVER edit `task_state.json`, `implementation_plan.md`, or any file outside your scope.

### Rule 2: Changelog (Handoff Documentation)
After ALL code is written and BEFORE calling `./task_tool.sh done`, you MUST:

1. **Create** `tasks_pending/task_c2_train_sh_changelog.md`
2. **Include in the changelog:**
   - **Touched Files:** A bulleted list of every file you created or modified.
   - **Contract Fulfillment:** Brief confirmation of the interfaces/DTOs you implemented.
   - **Deviations/Notes:** Any edge cases you handled or deviations from the brief the QA agent should verify.
3. **Then and only then** run:
   ```bash
   ./task_tool.sh done task_c2_train_sh
   ```

> **⚠️ Calling `./task_tool.sh done` without creating the changelog file is FORBIDDEN.**

### Rule 3: No Placeholders
- Do not use `// TODO`, `/* FIXME */`, or stub implementations.
- Output fully functional, production-ready code.

### Rule 4: Human Intervention Protocol
During execution, a human may intercept your work and propose changes, provide code snippets, or redirect your approach. When this happens:

1. **ADOPT the concept, VERIFY the details.** Humans are exceptional at architectural vision but make detail mistakes (wrong API, typos, outdated syntax). Independently verify all human-provided code against the actual framework version and project contracts.
2. **TRACK every human intervention in the changelog.** Add a dedicated `## Human Interventions` section to your changelog documenting:
   - What the human proposed (1-2 sentence summary)
   - What you adopted vs. what you corrected
   - Any deviations from the original task brief caused by the intervention
3. **DO NOT silently incorporate changes.** The QA agent and Architect must be able to trace exactly what came from the spec vs. what came from a human mid-flight. Untracked changes are invisible to the verification pipeline.

---

## Context Loading (Tier-Dependent)

**If your tier is `standard` or `advanced`:**

> **CRITICAL FIRST STEP:** The Planner might omit critical skills or knowledge in your `Context_Bindings`. It is YOUR responsibility to self-heal missing context.
1. Read `.agents/skills/index.md` (Skills Catalog)
2. Read `.agents/knowledge/README.md` (Master Knowledge Index)
   *(If you discover a skill or knowledge domain relevant to your task that isn't in your `Context_Bindings`, **read it immediately** before starting.)*
3. Read `.agents/context.md` — Thin index pointing to context sub-files
4. Load ONLY the `context/*` sub-files listed in your `Context_Bindings` below
5. Scan `.agents/knowledge/` — Lessons from previous sessions relevant to your task
6. Read `.agents/workflows/execution-lifecycle.md` — Your 4-step execution loop
7. Read `.agents/rules/execution-boundary.md` — Scope and contract constraints

- `./implementation_plan_feature_2.md`
- `CLI arguments parsed without failure` _(not found — verify path)_
- `ZMQ Wait loop detects port correctly` _(not found — verify path)_
- `Ctrl+C cleanly exits spawned Rust process` _(not found — verify path)_
- `./train.sh --help` _(not found — verify path)_
- `./train.sh --no-visualizer --timesteps 0` _(not found — verify path)_

---

## Task Brief

Task_ID: C2
Execution_Phase: 3
Model_Tier: basic
Target_Files:
  - train.sh
Dependencies: C1
Context_Bindings:
  - implementation_plan_feature_2.md
Strict_Instructions:
  1. Create `train.sh` explicitly mapping the shell script defined in the spec `implementation_plan_feature_2.md`.
  2. Implement trap for clean shutdown of processes.
  3. Ensure wait blocks correctly poll ports 5555 and 8080.
  4. Make the script executable.
Verification_Strategy:
  Test_Type: manual_steps
  Test_Stack: bash
  Acceptance_Criteria:
    - CLI arguments parsed without failure
    - ZMQ Wait loop detects port correctly
    - Ctrl+C cleanly exits spawned Rust process
  Suggested_Test_Commands:
    - ./train.sh --help
    - ./train.sh --no-visualizer --timesteps 0

---

## Shared Contracts

# Phase 3.5: Training Pipeline Readiness

> **Goal:** Prepare the training pipeline for production runs — configurable bot opponent, 5-stage curriculum, one-command launch, validated profiles, and accurate documentation.

## Research Conclusions

### Reward Function: Keep Exploit-Proof Zero-Sum ✅

After analyzing the current `rewards.py` and researching RL reward best practices, **the current exploit-proof zero-sum reward is sufficient for this phase.** Rationale:

| Factor | Assessment |
|--------|-----------|
| **Gradient clarity** | Clean Win > Bloody Win > Timeout > Loss — no ambiguity |
| **Exploit resistance** | Anti-coward (time pressure), anti-drip-feed (kill trading only), anti-pyrrhic (survival bonus) |
| **Simplicity** | Fewer hyperparameters → fewer tuning failures |
| **Reward hacking risk** | Adding territory/flanking as step rewards risks the agent optimizing shaped signals instead of winning |
| **Monitoring** | Flanking score is already tracked in `info` dict for TensorBoard — we can ADD it as a reward component later if training plateaus |

**Enhancement for later stages:** The profile already supports per-stage reward weights. If Stage 4+ training plateaus, we can add an `optional_shaping` section to the profile with flanking/territory bonuses — without touching `rewards.py` core logic.

### Bot Behavior: Python-Side Controller (Context-Agnostic)

The bot needs different behaviors per curriculum stage, not just "charge at brain." The correct approach is a **Python-side `BotController`** that:
1. Lives entirely in `macro-brain/src/env/bot_controller.py`
2. Reads strategy config from the `GameProfile`'s `bot_stage_behaviors`
3. Computes a bot directive each step based on the state snapshot
4. Sends the bot directive alongside the brain directive via ZMQ

The **Micro-Core stays context-agnostic** — it only receives a list of `MacroDirective`s and executes them all. It has NO knowledge of which directive came from the brain vs the bot.

**Rust change is minimal:** `LatestDirective` holds `Vec<MacroDirective>` instead of `Option`, and `directive_executor_system` loops over the list. Zero game logic added.

---

## DAG Execution Graph

```
Phase 1 (Parallel — no file collisions):
├── A1: Python BotController          [Python: new files]
├── A2: Profile Validator CLI          [Python: new files]
└── A3: Training Run Manager           [Python: new files]

Phase 2 (Parallel — depends on A1):
├── B1: Bot Config + 5-Stage Profile   [Python: modify profile/curriculum/JSON]
├── B2: ZMQ Multi-Directive Protocol   [Rust: modify executor, zmq parser]
└── B3: Stage 5 Terrain + Spawns       [Python: modify curriculum.py, terrain_generator.py]

Phase 3 (Sequential — depends on all Phase 2):
├── C1: train.py Pre-Flight          [Python: modify train.py]
├── C2: Launch Script                [Shell: new train.sh]
└── C3: TRAINING_STATUS Rewrite      [Markdown: rewrite TRAINING_STATUS.md]
```

---

## 5-Stage Curriculum Design

| Stage | Map | Bot Behavior | Actions Unlocked | Graduation Condition |
|-------|-----|-------------|------------------|---------------------|
| **1** | Flat 1000×1000 | **Charge** — straight rush at brain | Hold, Navigate, ActivateBuff (0-2) | WR ≥ 80%, survivors ≥ 10, 100 eps |
| **2** | Flat 1000×1000 | **Charge** — scattered 2-3 groups | +Retreat (0-3) | WR ≥ 85%, survivors ≥ 15, Retreat ≥ 5%, 100 eps |
| **3** | Simple (1-2 walls) | **HoldPosition** — defends near spawn | +ZoneModifier, +SplitFaction (0-5) | WR ≥ 75%, Split ≥ 5%, 150 eps |
| **4** | Complex (procedural) | **Adaptive** — retreats when losing, pushes when winning | +MergeFaction, +SetAggroMask (0-7) | WR ≥ 80%, timeout ≤ 5%, 250 eps |
| **5** | Complex (procedural) | **Mixed** — random strategy each episode from pool | All 8 | Final validation stage (no graduation) |

**Why this progression teaches strategy:**
- **S1-2:** Brain learns basic combat. Bot charges → brain must learn to fight and win, then retreat.
- **S3:** Bot HOLDS position → brain can't just wait. Must navigate terrain, split army to flank.
- **S4:** Bot RETREATS when losing → brain must chase decisively. Bot PUSHES when winning → brain must retreat itself.
- **S5:** Bot uses RANDOM strategy → brain must generalize. Can't memorize one counter-strategy.

---

## Shared Contracts

### Contract 1: ZMQ Directive Batch (Breaking Change)

> [!CAUTION]
> **PATCH 1 — Serde Parsing Trap:** The legacy single-directive format (`{"type": "macro_directive", ...}`) is **dropped entirely**. ALL code (Python sender + Rust parser) MUST use the batch format below. No backward compatibility — the old format would crash the serde parser when it hits the array wrapper.

```json
// THE ONLY SUPPORTED FORMAT — always a batch, even for 1 directive
{
  "type": "macro_directives",
  "directives": [
    { "directive": "Hold" },
    { "directive": "UpdateNavigation",
      "follower_faction": 1, "target": { "type": "Faction", "faction_id": 0 } }
  ]
}
```

**Migration:** All existing code that sends `{"type": "macro_directive", ...}` must be updated to wrap in the batch format. This includes `SwarmEnv.step()`, any debug/test scripts, and the visualizer's ML Brain panel (if it sends directives).

### Contract 2: Rust `LatestDirective` (Vec)

```rust
// ONLY change in Rust — no game logic
#[derive(Resource, Debug, Default)]
pub struct LatestDirective {
    pub directives: Vec<MacroDirective>,  // was: Option<MacroDirective>
    pub last_received_tick: u64,
    pub last_directive_json: Option<String>,
}
```

### Contract 3: Python `BotController` (with Hysteresis)

> [!CAUTION]
> **PATCH 3 — Bot State Jitter:** The Adaptive strategy MUST implement **hysteresis** — once a state transition occurs (charge→retreat or retreat→charge), the bot locks into that state for `min_lock_steps` evaluations before it can switch again. Without this, the bot oscillates every step during close battles, destroying training gradients.

```python
# macro-brain/src/env/bot_controller.py
class BotController:
    # Hysteresis state
    _current_mode: str        # "charge" or "retreat"
    _mode_lock_remaining: int  # steps remaining before mode can change
    MIN_LOCK_STEPS: int = 15  # ~7.5 seconds at 2 Hz eval rate

    def configure(self, behavior: BotStageBehaviorDef, target_faction: int,
                  starting_count: int, rng=None) -> None: ...
    def compute_directive(self, snapshot: dict) -> dict: ...
```

### Contract 4: `GameProfile` Bot Config Extension (Python)

```python
# New definitions in definitions.py

@dataclass(frozen=True)
class BotStrategyDef:
    type: str  # "Charge", "HoldPosition", "Adaptive", "Mixed"
    target_faction: int | None = None
    x: float | None = None
    y: float | None = None
    retreat_health_fraction: float | None = None
    retreat_x: float | None = None
    retreat_y: float | None = None
    strategies: list | None = None  # list of BotStrategyDef dicts for Mixed

@dataclass(frozen=True)
class BotStageBehaviorDef:
    stage: int
    faction_id: int
    strategy: BotStrategyDef
    eval_interval_ticks: int = 60
```

### Contract 5: Faction Security Gateway

> [!CAUTION]
> **PATCH 2 — Bot Hijacking:** Before merging brain + bot directives into the batch payload, `SwarmEnv` MUST validate that bot directives ONLY reference bot-owned factions. A misconfigured profile that tells the bot to control faction 0 (brain) would overwrite the RL agent's actions and destroy convergence.

```python
# In SwarmEnv.step(), BEFORE sending:
def _validate_bot_directive(self, directive: dict) -> dict:
    """Ensure bot directive only commands bot-owned factions.
    
    If the directive references the brain faction, replace with Hold.
    Logs a warning for debugging.
    """
    faction_fields = ["follower_faction", "faction", "source_faction", "target_faction"]
    brain_id = self.profile.brain_faction.id
    for field in faction_fields:
        if directive.get(field) == brain_id:
            logger.warning(
                f"Bot directive tried to control brain faction {brain_id} "
                f"via '{field}' — blocked. Directive: {directive}"
            )
            return {"directive": "Hold"}
    return directive
```

### Contract 6: `ValidationResult`

```python
# macro-brain/src/config/validator.py

@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]    # Fatal — prevent training
    warnings: list[str]  # Non-fatal — log and continue
```

---

## Feature Details

- [Feature 1: Bot Behavior System](./implementation_plan_feature_1.md) — Rust system + Python integration
- [Feature 2: Training Pipeline & Documentation](./implementation_plan_feature_2.md) — Validator, Run Manager, Launch Script, TRAINING_STATUS rewrite

---

## File Summary

| Task | File | Action | Domain |
|------|------|--------|--------|
| A1 | `macro-brain/src/env/bot_controller.py` | NEW | Python |
| A1 | `macro-brain/tests/test_bot_controller.py` | NEW | Python |
| A2 | `macro-brain/src/config/validator.py` | NEW | Python |
| A2 | `macro-brain/tests/test_validator.py` | NEW | Python |
| A3 | `macro-brain/src/training/run_manager.py` | NEW | Python |
| A3 | `macro-brain/tests/test_run_manager.py` | NEW | Python |
| B1 | `macro-brain/src/config/definitions.py` | MODIFY | Python |
| B1 | `macro-brain/src/config/parser.py` | MODIFY | Python |
| B1 | `macro-brain/src/config/game_profile.py` | MODIFY | Python |
| B1 | `macro-brain/profiles/default_swarm_combat.json` | MODIFY | Python |
| B1 | `macro-brain/src/training/curriculum.py` | MODIFY | Python |
| B2 | `micro-core/src/systems/directive_executor/executor.rs` | MODIFY | Rust |
| B2 | `micro-core/src/systems/directive_executor/mod.rs` | MODIFY | Rust |
| B2 | `micro-core/src/bridges/zmq_bridge/systems.rs` | MODIFY | Rust |
| B1 | `macro-brain/src/env/swarm_env.py` | MODIFY | Python |
| B3 | `macro-brain/src/training/curriculum.py` | MODIFY | Python |
| B3 | `macro-brain/src/utils/terrain_generator.py` | MODIFY | Python |
| C1 | `macro-brain/src/training/train.py` | MODIFY | Python |
| C2 | `train.sh` | NEW | Shell |
| C3 | `TRAINING_STATUS.md` | REWRITE | Markdown |

> [!WARNING]
> **Collision note:** Tasks B1 and B3 both modify `curriculum.py`. B3 adds Stage 5 spawns; B1 adds bot behavior lookups. These changes are to DIFFERENT functions and can be merged cleanly, but they MUST run in the same phase or be assigned to the same executor. I've placed both in Phase 2 with B3 having a note to append to non-overlapping sections.

> [!IMPORTANT]
> **Architecture invariant:** ZERO game logic in Rust Micro-Core. The `bot_controller.py`, `bot_stage_behaviors` JSON config, and all strategy decisions live entirely in Python. Rust only knows `Vec<MacroDirective>` — it cannot distinguish brain from bot.

---

## Verification Plan

### Automated Tests
```bash
# Rust: existing + minimal multi-directive tests
cd micro-core && cargo test
# Expected: 181 existing + ~4 new = ~185 tests, 0 failures

# Python: existing + validator + run manager tests
cd macro-brain && python -m pytest tests/ -v
# Expected: 34 existing + ~12 new = ~46 tests, 0 failures

# Profile validation smoke test
cd macro-brain && python -m src.config.validator profiles/default_swarm_combat.json
# Expected: "✅ Profile valid" output
```

### Integration Test
```bash
# Launch script smoke test (requires Rust to compile)
./train.sh --profile profiles/default_swarm_combat.json --timesteps 0 --dry-run
# Expected: Builds Rust, validates profile, creates run directory, exits cleanly
```

### Manual Verification
- Review `TRAINING_STATUS.md` against actual reward code and profile JSON
- Inspect `runs/` directory structure after a test run
- Observe bot behavior in debug visualizer for each stage preset


---
<!-- Source: implementation_plan_feature_1.md -->

# Feature 1: Bot Behavior System (v3 — All Patches Applied)

> **Parent:** [implementation_plan.md](./implementation_plan.md)
> **Tasks:** A1 (Python BotController), B1 (Python profile + SwarmEnv integration), B2 (ZMQ batch directive)

> [!IMPORTANT]
> **Architecture Rule:** The Micro-Core is context-agnostic. It executes directives — it does NOT decide what those directives are. ALL bot strategy logic lives in Python. Rust receives `Vec<MacroDirective>` and loops — it cannot distinguish brain from bot.

## Pre-Flight Patches Applied

| # | Patch | Where | What |
|---|-------|-------|------|
| **P1** | Serde Parsing Trap | Rust B2 | Drop legacy single-directive format. `macro_directives` batch ONLY. |
| **P2** | Bot Hijacking | Python B1 | `SwarmEnv._validate_bot_directive()` blocks bot from commanding brain faction. |
| **P3** | Jitter Hysteresis | Python A1 | Adaptive bot locks mode for `MIN_LOCK_STEPS` before switching. |

---

## Revised Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  Python (Macro-Brain)                         │
│                                                               │
│  SwarmEnv.step(action)                                       │
│    ├── brain_directive = action_to_directive(action)          │
│    ├── bot_directive = bot_controller.compute(snapshot)       │
│    ├── bot_directive = _validate_bot_directive(bot_directive) │ ← PATCH 2
│    └── send({"type":"macro_directives",                      │
│              "directives":[brain, bot]})  ────────────────── │ ─┐ ← PATCH 1
│                                                               │  │
│  BotController (NEW — all strategy logic HERE)               │  │
│    ├── Charge: UpdateNavigation toward enemy                 │  │
│    ├── HoldPosition: Retreat to waypoint                     │  │
│    ├── Adaptive: charge OR retreat (with HYSTERESIS)         │  │ ← PATCH 3
│    └── Mixed: random from pool each episode                  │  │
└──────────────────────────────────────────────────────────────┘  │
                                                                  │
          ZMQ REP (always batch: macro_directives)                │
                                                                  │
┌──────────────────────────────────────────────────────────────┐  │
│              Rust Micro-Core (Context-Agnostic)               │  │
│                                                               │ ◄┘
│  ai_poll_system                                              │
│    └── serde_json::from_str → Vec<MacroDirective>            │ ← PATCH 1
│                                                               │
│  directive_executor_system                                   │
│    └── for directive in std::mem::take(&mut directives):     │
│        └── match directive { ... }    ← ZERO CHANGES         │
│                                                               │
│  (Zero game logic. Just executes vectors.)                   │
└──────────────────────────────────────────────────────────────┘
```

---

## Task A1: Python BotController (with Hysteresis)

**Model Tier:** `standard`
**Domain:** Python (pure logic, reads snapshot JSON)
**Dependencies:** None (Phase 1)

### Target Files
- **[NEW]** `macro-brain/src/env/bot_controller.py`
- **[NEW]** `macro-brain/tests/test_bot_controller.py`

### Context Bindings
- `context/conventions`
- `context/ipc-protocol`

### Contract: `BotController`

```python
# macro-brain/src/env/bot_controller.py

"""Heuristic bot controller for training opponents.

All bot decision-making lives here — NOT in the Rust Micro-Core.
The bot controller reads the state snapshot and produces MacroDirective
JSON dicts, identical in format to what the RL brain produces.

## PATCH 3: Hysteresis (Anti-Jitter)
The Adaptive strategy uses mode-locking to prevent oscillation.
Once the bot transitions (charge→retreat or retreat→charge), it locks
into that state for MIN_LOCK_STEPS evaluations. Without this, tied
battles cause frame-by-frame oscillation that destroys training gradients.

Strategies:
  Charge       — always navigate toward enemy faction
  HoldPosition — retreat to a fixed waypoint (defensive)
  Adaptive     — charge when healthy, retreat when losing (with hysteresis)
  Mixed        — randomly select one strategy per episode
"""

from __future__ import annotations

import random
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.config.definitions import BotStageBehaviorDef, BotStrategyDef


class BotController:
    """Stateful heuristic bot that produces directives each step.

    Created once per SwarmEnv. Reconfigured on reset() when
    the curriculum stage changes.
    """

    # ── PATCH 3: Hysteresis constant ────────────────────────
    # At 2 Hz AI eval rate (every 30 ticks), 15 steps = ~7.5 seconds
    # This prevents jitter during balanced battles.
    MIN_LOCK_STEPS: int = 15

    def __init__(self):
        self._faction_id: int = 1
        self._target_faction: int = 0
        self._strategy: BotStrategyDef | None = None
        self._starting_count: int = 50
        self._active_strategy: BotStrategyDef | None = None  # resolved for Mixed

        # ── PATCH 3: Hysteresis state ───────────────────────
        self._current_mode: str = "charge"     # "charge" or "retreat"
        self._mode_lock_remaining: int = 0     # steps until mode can change

    def configure(
        self,
        behavior: BotStageBehaviorDef,
        target_faction: int,
        starting_count: int,
        rng=None,
    ) -> None:
        """Reconfigure for a new episode. Called during SwarmEnv.reset().

        Resets ALL state including hysteresis lock.
        """
        self._faction_id = behavior.faction_id
        self._target_faction = target_faction
        self._strategy = behavior.strategy
        self._starting_count = starting_count

        # Reset hysteresis
        self._current_mode = "charge"
        self._mode_lock_remaining = 0

        # For Mixed: select one strategy at episode start
        if behavior.strategy.type == "Mixed" and behavior.strategy.strategies:
            if rng is None:
                rng = random
            idx = rng.randint(0, len(behavior.strategy.strategies) - 1)
            self._active_strategy = behavior.strategy.strategies[idx]
        else:
            self._active_strategy = behavior.strategy

    def compute_directive(self, snapshot: dict) -> dict[str, Any]:
        """Compute the bot's directive based on current game state.

        Returns a MacroDirective JSON dict (inner format, no "type" wrapper).
        The SwarmEnv wraps all directives in the batch payload.
        """
        if self._active_strategy is None:
            return _hold()

        strategy = self._active_strategy

        if strategy.type == "Charge":
            return _update_nav(
                self._faction_id,
                {"type": "Faction", "faction_id": strategy.target_faction},
            )

        elif strategy.type == "HoldPosition":
            return _retreat(self._faction_id, strategy.x, strategy.y)

        elif strategy.type == "Adaptive":
            return self._compute_adaptive(snapshot, strategy)

        # Fallback
        return _hold()

    # ── PATCH 3: Adaptive with Hysteresis ───────────────────

    def _compute_adaptive(self, snapshot: dict, strategy) -> dict:
        """Adaptive strategy with mode-locking to prevent jitter.

        State machine:
          1. If mode_lock_remaining > 0, stay in current mode
          2. Else, evaluate health fraction:
             - Below threshold → switch to retreat, lock for MIN_LOCK_STEPS
             - Above threshold → switch to charge, lock for MIN_LOCK_STEPS
          3. Only transitions lock; staying in the same mode does NOT reset lock
        """
        # Tick down lock
        if self._mode_lock_remaining > 0:
            self._mode_lock_remaining -= 1

        # Evaluate health
        current_count = _get_faction_count(snapshot, self._faction_id)
        fraction = current_count / max(self._starting_count, 1)
        desired_mode = (
            "retreat" if fraction < strategy.retreat_health_fraction
            else "charge"
        )

        # Only switch if lock has expired AND mode actually changes
        if self._mode_lock_remaining <= 0 and desired_mode != self._current_mode:
            self._current_mode = desired_mode
            self._mode_lock_remaining = self.MIN_LOCK_STEPS

        # Execute current mode
        if self._current_mode == "retreat":
            return _retreat(
                self._faction_id,
                strategy.retreat_x,
                strategy.retreat_y,
            )
        else:
            return _update_nav(
                self._faction_id,
                {"type": "Faction", "faction_id": strategy.target_faction},
            )


# ── Directive Builders ──────────────────────────────────────

def _hold() -> dict:
    return {"directive": "Hold"}


def _update_nav(follower_faction: int, target: dict) -> dict:
    return {
        "directive": "UpdateNavigation",
        "follower_faction": follower_faction,
        "target": target,
    }


def _retreat(faction: int, x: float, y: float) -> dict:
    return {
        "directive": "Retreat",
        "faction": faction,
        "retreat_x": float(x),
        "retreat_y": float(y),
    }


def _get_faction_count(snapshot: dict, faction_id: int) -> int:
    """Read faction entity count from snapshot summary."""
    counts = snapshot.get("summary", {}).get("faction_counts", {})
    return counts.get(str(faction_id), counts.get(faction_id, 0))
```

> [!IMPORTANT]
> Note the directive builders output the **inner format** (no `"type": "macro_directive"` wrapper). The batch envelope `{"type": "macro_directives", "directives": [...]}` is applied by SwarmEnv.

### Verification Strategy
```
Test_Type: unit
Test_Stack: pytest (macro-brain)
Acceptance_Criteria:
  - Charge strategy returns UpdateNavigation toward target faction
  - HoldPosition strategy returns Retreat to fixed waypoint
  - Adaptive charges when count > threshold, retreats when below
  - PATCH 3: Adaptive does NOT switch modes when lock is active
  - PATCH 3: After MIN_LOCK_STEPS, Adaptive CAN switch mode
  - PATCH 3: configure() resets hysteresis state
  - Mixed selects one strategy from pool during configure()
  - Directive builders produce correct inner-format JSON (no "type" wrapper)
  - _get_faction_count reads from snapshot correctly
Suggested_Test_Commands:
  - cd macro-brain && python -m pytest tests/test_bot_controller.py -v
```

---

## Task B2: ZMQ Batch Directive Protocol (Breaking Change)

**Model Tier:** `standard`
**Domain:** Rust (Micro-Core) — **MINIMAL changes, zero game logic**
**Dependencies:** A1 (BotController design)

### Target Files
- **[MODIFY]** `micro-core/src/bridges/zmq_bridge/systems.rs` — parse `macro_directives` batch ONLY
- **[MODIFY]** `micro-core/src/systems/directive_executor/executor.rs` — loop over vec
- **[MODIFY]** `micro-core/src/systems/directive_executor/mod.rs` — if LatestDirective is here

### Context Bindings
- `context/ipc-protocol`
- `context/conventions`
- `skills/rust-code-standards`

> [!CAUTION]
> **PATCH 1 — No Backward Compatibility.** The Rust ZMQ parser accepts ONLY `{"type": "macro_directives", "directives": [...]}`. The legacy `{"type": "macro_directive", ...}` is **NOT supported**. It would cause a serde mismatch and panic. All senders must be updated.

#### 1. `LatestDirective` — Vec instead of Option

```rust
#[derive(Resource, Debug, Default)]
pub struct LatestDirective {
    /// All directives received in the latest AI eval cycle.
    /// Always a batch: may contain 1 (brain only) or 2+ (brain + bots).
    pub directives: Vec<MacroDirective>,
    pub last_received_tick: u64,
    pub last_directive_json: Option<String>,
}
```

#### 2. `directive_executor_system` — iterate, not take

```rust
// BEFORE (single directive):
let Some(directive) = latest.directive.take() else { return; };
match directive { ... }

// AFTER (batch):
let directives: Vec<MacroDirective> = std::mem::take(&mut latest.directives);
if directives.is_empty() { return; }
for directive in directives {
    match directive {
        // ...exact same match arms as before, NO changes to any arm...
    }
}
```

#### 3. ZMQ response parser — batch format ONLY

```rust
/// Parse AI response from Python. Accepts ONLY the batch format.
///
/// ## PATCH 1: No Legacy Support
/// The old `"type": "macro_directive"` format is NOT accepted.
/// All responses MUST be `{"type": "macro_directives", "directives": [...]}`.
fn parse_ai_response(raw: &str) -> Vec<MacroDirective> {
    #[derive(Deserialize)]
    struct BatchResponse {
        #[serde(rename = "type")]
        msg_type: String,
        directives: Vec<MacroDirective>,
    }

    match serde_json::from_str::<BatchResponse>(raw) {
        Ok(batch) if batch.msg_type == "macro_directives" => batch.directives,
        Ok(_) => {
            eprintln!("[ZMQ] Unexpected message type (expected 'macro_directives')");
            vec![]
        }
        Err(e) => {
            eprintln!("[ZMQ] Failed to parse AI response: {e}");
            vec![]
        }
    }
}
```

#### 4. Migration: find all legacy senders

**Must update these files to use batch format:**
- `macro-brain/src/env/swarm_env.py` — `step()` method
- `debug-visualizer/js/controls/ml-brain.js` — if it sends directives via WS→ZMQ relay

> [!NOTE]
> The migration search command: `grep -rn '"macro_directive"' macro-brain/ debug-visualizer/`

### Verification Strategy
```
Test_Type: unit
Test_Stack: cargo test (micro-core)
Acceptance_Criteria:
  - Batch with 2 directives → both get executed in order
  - Batch with 1 directive → works correctly
  - Empty directives list → no-op, no crash
  - Malformed JSON → logged error, returns empty vec (no panic)
  - Existing executor tests still pass (update test fixtures to batch format)
Suggested_Test_Commands:
  - cd micro-core && cargo test directive_executor
  - cd micro-core && cargo test zmq
```

---

## SwarmEnv Integration (Part of Task B1)

### PATCH 2: Faction Security Gateway

```python
# In SwarmEnv — new method:

def _validate_bot_directive(self, directive: dict) -> dict:
    """PATCH 2: Prevent bot from hijacking brain faction.

    Checks all faction-referencing fields in the directive.
    If ANY field targets the brain faction, the entire directive
    is replaced with Hold and a warning is logged.

    This is a SECURITY boundary, not a convenience helper.
    A misconfigured profile must never corrupt training.
    """
    FACTION_FIELDS = [
        "follower_faction", "faction", "source_faction", "target_faction"
    ]
    brain_id = self.profile.brain_faction.id

    for field in FACTION_FIELDS:
        if directive.get(field) == brain_id:
            import logging
            logging.getLogger(__name__).warning(
                f"Bot directive tried to control brain faction {brain_id} "
                f"via '{field}' — BLOCKED. Directive: {directive}"
            )
            return {"directive": "Hold"}

    return directive
```

### Updated `SwarmEnv.step()` — Batch Directive Builder

```python
# In SwarmEnv.step(), replace the single-directive send with:

brain_directive = self._action_to_directive(action)
bot_directive = self._bot_controller.compute_directive(snapshot)
bot_directive = self._validate_bot_directive(bot_directive)  # PATCH 2

# PATCH 1: Always use batch format
batch = {
    "type": "macro_directives",
    "directives": [brain_directive, bot_directive],
}
self._socket.send_string(json.dumps(batch))

# For tick swallowing, send Hold for BOTH:
hold_batch = {
    "type": "macro_directives",
    "directives": [{"directive": "Hold"}, {"directive": "Hold"}],
}
```

### Updated `SwarmEnv.reset()` — BotController Configuration

```python
# In SwarmEnv.reset(), after loading curriculum stage:

bot_behavior = self.profile.get_bot_behavior_for_stage(
    self.enemy_faction, self.curriculum_stage
)
self._bot_controller.configure(
    behavior=bot_behavior,
    target_faction=self.brain_faction,
    starting_count=int(self.profile.bot_factions[0].default_count),
    rng=self.np_random,
)
```

---

## Updated File Summary (Feature 1 only)

| Task | File | Action | Domain | Patch |
|------|------|--------|--------|-------|
| A1 | `macro-brain/src/env/bot_controller.py` | NEW | Python | P3 |
| A1 | `macro-brain/tests/test_bot_controller.py` | NEW | Python | P3 |
| B2 | `micro-core/src/systems/directive_executor/executor.rs` | MODIFY | Rust | P1 |
| B2 | `micro-core/src/systems/directive_executor/mod.rs` | MODIFY | Rust | P1 |
| B2 | `micro-core/src/bridges/zmq_bridge/systems.rs` | MODIFY | Rust | P1 |
| B1 | `macro-brain/src/env/swarm_env.py` | MODIFY | Python | P1, P2 |

> [!NOTE]
> **Removed from Rust:** No `bot_behavior.rs`, no `bot_heuristic.rs`, no `BotBehaviorConfig`, no `BotHeuristicState`. All bot logic is Python-side. Rust just loops over `Vec<MacroDirective>`.


---
<!-- Source: implementation_plan_feature_2.md -->

# Feature 2: Training Pipeline & Documentation

> **Parent:** [implementation_plan.md](./implementation_plan.md)
> **Tasks:** A2, A3, B1, B3, C1, C2, C3

---

## Task A2: Profile Validator CLI

**Model Tier:** `standard`
**Domain:** Python (pure logic, no IPC)
**Dependencies:** None (Phase 1)

### Target Files
- **[NEW]** `macro-brain/src/config/validator.py`
- **[NEW]** `macro-brain/tests/test_validator.py`

### Context Bindings
- `context/conventions`
- `context/tech-stack`

### Strict Instructions

Create `validator.py` with:

1. `ValidationResult` dataclass (see Contract 4 in index plan)
2. `validate_profile(profile: GameProfile) -> ValidationResult` function
3. CLI entry point: `if __name__ == "__main__"` that loads + validates + prints result

**Validation rules (all must pass for `valid=True`):**

| # | Rule | Severity |
|---|------|----------|
| V1 | Faction ID uniqueness — no duplicates in `factions[].id` | Error |
| V2 | Exactly one faction with `role == "brain"` | Error |
| V3 | At least one faction with `role == "bot"` | Error |
| V4 | Combat rule faction IDs exist in `factions[].id` | Error |
| V5 | Action indices 0..N-1 contiguous, no gaps | Error |
| V6 | Curriculum stages sequential (1, 2, 3, ...) | Error |
| V7 | Graduation `action_usage` keys match action names | Warning |
| V8 | No action `unlock_stage` exceeds max curriculum stage | Warning |
| V9 | `cell_size * grid_width ≈ width` (within 10% tolerance) | Warning |

**CLI output format:**
```
$ python -m src.config.validator profiles/default_swarm_combat.json
📋 Validating: Swarm Combat 50v50 v1.0.0
  ✅ V1: Faction IDs unique
  ✅ V2: Brain faction found (id=0)
  ✅ V3: Bot factions found (1)
  ✅ V4: Combat rules reference valid factions
  ✅ V5: Action indices contiguous (0-7)
  ✅ V6: Curriculum stages sequential (1-5)
  ✅ V7: Graduation action keys valid
  ✅ V8: Unlock stages within bounds
  ✅ V9: Grid dimensions consistent
✅ Profile valid (0 errors, 0 warnings)
```

### Verification Strategy
```
Test_Type: unit
Test_Stack: pytest (macro-brain)
Acceptance_Criteria:
  - Valid profile returns ValidationResult(valid=True, errors=[], warnings=[])
  - Profile with 2 brain factions returns error in V2
  - Profile with duplicate faction IDs returns error in V1
  - Combat rule with non-existent faction returns error in V4
  - Non-contiguous action indices (0,1,3) returns error in V5
  - action_usage key "NonExistent" returns warning in V7
Suggested_Test_Commands:
  - cd macro-brain && python -m pytest tests/test_validator.py -v
```

---

## Task A3: Training Run Manager

**Model Tier:** `standard`
**Domain:** Python (file I/O, no IPC)
**Dependencies:** None (Phase 1)

### Target Files
- **[NEW]** `macro-brain/src/training/run_manager.py`
- **[NEW]** `macro-brain/tests/test_run_manager.py`

### Context Bindings
- `context/conventions`

### Strict Instructions

Each training run gets a unique directory under `macro-brain/runs/`:

```
runs/
└── run_20260408_100500/
    ├── checkpoints/        ← model snapshots
    ├── tb_logs/            ← TensorBoard logs
    ├── profile_snapshot.json  ← copy of the profile used
    └── episode_log.csv     ← created by EpisodeLogCallback
```

**Implementation:**

```python
# macro-brain/src/training/run_manager.py

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class RunConfig:
    """Metadata and paths for a single training run."""
    run_id: str
    profile_name: str
    profile_path: str
    base_dir: Path

    @property
    def checkpoint_dir(self) -> Path:
        return self.base_dir / "checkpoints"

    @property
    def tensorboard_dir(self) -> Path:
        return self.base_dir / "tb_logs"

    @property
    def episode_log_path(self) -> Path:
        return self.base_dir / "episode_log.csv"

    @property
    def profile_snapshot_path(self) -> Path:
        return self.base_dir / "profile_snapshot.json"


def create_run(
    profile_path: str,
    profile_name: str,
    runs_dir: str = "./runs",
) -> RunConfig:
    """Create a new run directory with timestamped ID.

    Args:
        profile_path: Path to the game profile JSON.
        profile_name: Human-readable name from profile.meta.name.
        runs_dir: Base directory for all runs.

    Returns:
        RunConfig with all paths set and directories created.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"run_{timestamp}"
    base_dir = Path(runs_dir) / run_id

    config = RunConfig(
        run_id=run_id,
        profile_name=profile_name,
        profile_path=profile_path,
        base_dir=base_dir,
    )

    # Create directory structure
    config.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    config.tensorboard_dir.mkdir(parents=True, exist_ok=True)

    # Snapshot the profile (reproducibility)
    shutil.copy2(profile_path, config.profile_snapshot_path)

    return config
```

### Verification Strategy
```
Test_Type: unit
Test_Stack: pytest (macro-brain)
Acceptance_Criteria:
  - create_run returns RunConfig with correct paths
  - Directories are created on disk (use tmp_path fixture)
  - Profile JSON is copied to run directory
  - Run IDs contain timestamp
  - Multiple calls produce different run IDs
Suggested_Test_Commands:
  - cd macro-brain && python -m pytest tests/test_run_manager.py -v
```

---

## Task B1: Bot Config + 5-Stage Profile Update

**Model Tier:** `advanced`
**Domain:** Python (multiple files, cross-cutting concern)
**Dependencies:** A1 (Rust BotBehaviorConfig must be designed)

### Target Files
- **[MODIFY]** `macro-brain/src/config/definitions.py` — add `BotStrategyDef`, `BotStageBehaviorDef`
- **[MODIFY]** `macro-brain/src/config/parser.py` — parse `bot_stage_behaviors` from JSON
- **[MODIFY]** `macro-brain/src/config/game_profile.py` — add `bot_behaviors_payload()`, `get_bot_behavior_for_stage()`
- **[MODIFY]** `macro-brain/profiles/default_swarm_combat.json` — add 5th stage + bot behaviors
- **[MODIFY]** `macro-brain/src/env/swarm_env.py` — add `bot_behaviors` to reset payload
- **[NEW]** `macro-brain/tests/test_bot_behavior.py`

### Context Bindings
- `context/conventions`
- `context/ipc-protocol`

### 1. New Definitions

Add to `definitions.py`:

```python
@dataclass(frozen=True)
class BotStrategyDef:
    """Abstract bot strategy — maps to Rust BotStrategy enum."""
    type: str  # "Charge", "HoldPosition", "Adaptive", "Mixed"
    target_faction: int | None = None
    x: float | None = None
    y: float | None = None
    retreat_health_fraction: float | None = None
    retreat_x: float | None = None
    retreat_y: float | None = None
    strategies: list | None = None  # list of BotStrategyDef dicts for Mixed

    def to_dict(self) -> dict:
        """Serialize to ZMQ payload format matching Rust serde(tag='type')."""
        d = {"type": self.type}
        if self.type == "Charge":
            d["target_faction"] = self.target_faction
        elif self.type == "HoldPosition":
            d["x"] = self.x
            d["y"] = self.y
        elif self.type == "Adaptive":
            d["target_faction"] = self.target_faction
            d["retreat_health_fraction"] = self.retreat_health_fraction
            d["retreat_x"] = self.retreat_x
            d["retreat_y"] = self.retreat_y
        elif self.type == "Mixed":
            d["strategies"] = [s.to_dict() if isinstance(s, BotStrategyDef)
                               else s for s in (self.strategies or [])]
        return d


@dataclass(frozen=True)
class BotStageBehaviorDef:
    """Bot behavior config for a specific curriculum stage."""
    stage: int
    faction_id: int
    strategy: BotStrategyDef
    eval_interval_ticks: int = 60
```

### 2. Profile JSON Update

Add `bot_stage_behaviors` to `default_swarm_combat.json` and add Stage 5:

```json
{
  "training": {
    "curriculum": [
      // ...existing stages 1-4...,
      {
        "stage": 5,
        "description": "Generalization: full 8 actions, mixed bot strategies, complex terrain",
        "graduation": {
          "win_rate": 0.85,
          "min_episodes": 300,
          "timeout_rate_max": 0.05
        },
        "demotion": { "win_rate_floor": 0.20, "window": 100 }
      }
    ]
  },

  "bot_stage_behaviors": [
    {
      "stage": 1,
      "faction_id": 1,
      "strategy": { "type": "Charge", "target_faction": 0 },
      "eval_interval_ticks": 60
    },
    {
      "stage": 2,
      "faction_id": 1,
      "strategy": { "type": "Charge", "target_faction": 0 },
      "eval_interval_ticks": 60
    },
    {
      "stage": 3,
      "faction_id": 1,
      "strategy": { "type": "HoldPosition", "x": 650.0, "y": 500.0 },
      "eval_interval_ticks": 60
    },
    {
      "stage": 4,
      "faction_id": 1,
      "strategy": {
        "type": "Adaptive",
        "target_faction": 0,
        "retreat_health_fraction": 0.3,
        "retreat_x": 900.0,
        "retreat_y": 500.0
      },
      "eval_interval_ticks": 60
    },
    {
      "stage": 5,
      "faction_id": 1,
      "strategy": {
        "type": "Mixed",
        "strategies": [
          { "type": "Charge", "target_faction": 0 },
          { "type": "HoldPosition", "x": 650.0, "y": 500.0 },
          {
            "type": "Adaptive",
            "target_faction": 0,
            "retreat_health_fraction": 0.3,
            "retreat_x": 900.0,
            "retreat_y": 500.0
          }
        ]
      },
      "eval_interval_ticks": 60
    }
  ]
}
```

### 3. GameProfile Methods

Add to `game_profile.py`:

```python
def get_bot_behavior_for_stage(
    self, faction_id: int, stage: int
) -> BotStageBehaviorDef:
    """Find bot behavior config for this faction at this stage.

    Falls back to Charge if no config found (backward compatible).
    """
    for b in self.bot_stage_behaviors:
        if b.faction_id == faction_id and b.stage == stage:
            return b
    # Fallback: charge toward brain
    return BotStageBehaviorDef(
        stage=stage,
        faction_id=faction_id,
        strategy=BotStrategyDef(type="Charge", target_faction=self.brain_faction.id),
    )

def bot_behaviors_payload(self, stage: int) -> list[dict]:
    """Serialize bot behavior config for ZMQ ResetEnvironment payload."""
    behaviors = []
    for bot in self.bot_factions:
        b = self.get_bot_behavior_for_stage(bot.id, stage)
        behaviors.append({
            "faction_id": b.faction_id,
            "strategy": b.strategy.to_dict(),
            "eval_interval_ticks": b.eval_interval_ticks,
        })
    return behaviors
```

### 4. SwarmEnv.reset() Change

In `swarm_env.py`, add `bot_behaviors` to the reset payload:

```python
# Line ~149 in the reset JSON dict:
"bot_behaviors": self.profile.bot_behaviors_payload(self.curriculum_stage),
```

### Verification Strategy
```
Test_Type: unit
Test_Stack: pytest (macro-brain)
Acceptance_Criteria:
  - BotStrategyDef.to_dict() produces correct JSON for each type
  - Profile with bot_stage_behaviors loads without error
  - bot_behaviors_payload(1) returns Charge strategy
  - bot_behaviors_payload(3) returns HoldPosition strategy
  - bot_behaviors_payload(5) returns Mixed strategy with 3 sub-strategies
  - Missing bot_stage_behaviors falls back to Charge (backward compatible)
  - Profile JSON validates after 5th stage addition
Suggested_Test_Commands:
  - cd macro-brain && python -m pytest tests/test_bot_behavior.py -v
  - cd macro-brain && python -m pytest tests/test_game_profile.py -v
```

---

## Task B3: Stage 5 Terrain + Spawns

**Model Tier:** `basic`
**Domain:** Python
**Dependencies:** None (Phase 2, parallel with B1)

### Target Files
- **[MODIFY]** `macro-brain/src/training/curriculum.py` — add `get_stage5_spawns()`
- **[MODIFY]** `macro-brain/src/utils/terrain_generator.py` — update `generate_terrain_for_stage()` for stage 5

### Context Bindings
- `context/conventions`

### Strict Instructions

**Stage 5 spawns** — fully randomized for both factions. Both can spawn anywhere on the map:

```python
def get_stage5_spawns(rng=None, profile=None):
    """Stage 5: Fully random spawns for both factions.

    Both factions can appear anywhere. Multiple groups per faction.
    Forces the agent to handle arbitrary starting conditions.
    """
    if rng is None:
        rng = random

    brain_count = _faction_count(profile, 0)
    bot_count = _faction_count(profile, 1)

    # Brain: 1-2 spawn groups, random positions
    brain_groups = rng.choice([1, 2])
    brain_counts = _split_count(brain_count, brain_groups)
    spawns = []
    for count in brain_counts:
        spawns.append({
            "faction_id": 0,
            "count": count,
            "x": rng.uniform(100.0, 900.0),
            "y": rng.uniform(100.0, 900.0),
            "spread": 60.0,
            "stats": _faction_stats(profile, 0),
        })

    # Bot: 2-4 spawn groups, random positions
    bot_groups = rng.choice([2, 3, 4])
    bot_counts = _split_count(bot_count, bot_groups)
    positions = _generate_scattered_positions(bot_groups, rng)
    for count, (px, py) in zip(bot_counts, positions):
        spawns.append({
            "faction_id": 1, "count": count,
            "x": px, "y": py, "spread": 40.0,
            "stats": _faction_stats(profile, 1),
        })

    return spawns
```

**Update dispatchers:**

```python
# In get_spawns_for_stage():
def get_spawns_for_stage(stage, rng=None, profile=None):
    if stage <= 1:
        return get_stage1_spawns(profile=profile)
    elif stage == 2:
        return get_stage2_spawns(rng=rng, profile=profile)
    elif stage == 3:
        return get_stage3_spawns(rng=rng, profile=profile)
    elif stage == 4:
        return get_stage4_spawns(rng=rng, profile=profile)
    else:  # Stage 5+
        return get_stage5_spawns(rng=rng, profile=profile)

# In generate_terrain_for_stage():
# Stage 5 uses complex terrain (same as stage 4)
# No change needed — the `else` branch already covers stage 5+
```

### Verification Strategy
```
Test_Type: unit
Test_Stack: pytest (macro-brain)
Acceptance_Criteria:
  - get_stage5_spawns returns spawns for both factions
  - Spawn positions are within world bounds (100-900)
  - get_spawns_for_stage(5) dispatches to get_stage5_spawns
  - generate_terrain_for_stage(5) returns complex terrain (not None)
Suggested_Test_Commands:
  - cd macro-brain && python -m pytest tests/test_training.py -v
```

---

## Task C1: train.py Pre-Flight Integration

**Model Tier:** `basic`
**Domain:** Python
**Dependencies:** A2 (validator), A3 (run manager)

### Target Files
- **[MODIFY]** `macro-brain/src/training/train.py`

### Strict Instructions

Update `main()` flow to:

```python
def main():
    parser = argparse.ArgumentParser(description="Mass-Swarm AI Training")
    parser.add_argument("--profile", type=str,
        default="profiles/default_swarm_combat.json")
    parser.add_argument("--timesteps", type=int, default=100_000)
    parser.add_argument("--runs-dir", default="./runs")
    args = parser.parse_args()

    # 1. Load and VALIDATE profile
    from src.config.validator import validate_profile
    profile = load_profile(args.profile)
    result = validate_profile(profile)
    if not result.valid:
        print("❌ Profile validation failed:")
        for e in result.errors:
            print(f"  ERROR: {e}")
        sys.exit(1)
    for w in result.warnings:
        print(f"  ⚠️  {w}")

    # 2. Create run directory
    from src.training.run_manager import create_run
    run = create_run(
        profile_path=args.profile,
        profile_name=profile.meta.name,
        runs_dir=args.runs_dir,
    )

    # 3. Print banner
    print(f"{'='*60}")
    print(f"🚀 Training Run: {run.run_id}")
    print(f"   Profile:     {profile.meta.name} v{profile.meta.version}")
    print(f"   Factions:    {', '.join(f.name for f in profile.factions)}")
    print(f"   Actions:     {profile.num_actions}")
    print(f"   Stages:      {len(profile.training.curriculum)}")
    print(f"   Output:      {run.base_dir}")
    print(f"{'='*60}")

    # 4. Setup env, model, callbacks with run paths
    vec_env = DummyVecEnv([make_env(profile, args)])

    model = MaskablePPO(
        "MultiInputPolicy", vec_env,
        verbose=1,
        tensorboard_log=str(run.tensorboard_dir),
    )

    episode_logger = EpisodeLogCallback(log_path=str(run.episode_log_path))

    callbacks = [
        CheckpointCallback(
            save_freq=10000,
            save_path=str(run.checkpoint_dir),
            name_prefix="ppo_swarm",
        ),
        EnvStatCallback(),
        episode_logger,
        CurriculumCallback(
            episode_logger=episode_logger,
            profile=profile,
            verbose=1,
        ),
    ]

    model.learn(total_timesteps=args.timesteps, callback=callbacks)
```

### Verification Strategy
```
Test_Type: manual_steps
Manual_Steps:
  - Create an invalid profile (duplicate faction IDs) and run training → should abort
  - Run with --timesteps 0 → should create run directory and exit cleanly
Suggested_Test_Commands:
  - cd macro-brain && python -m src.training.train --help
```

---

## Task C2: Launch Script

**Model Tier:** `basic`
**Domain:** Shell
**Dependencies:** C1

### Target Files
- **[NEW]** `train.sh` (project root)

### Strict Instructions

```bash
#!/usr/bin/env bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════
# Mass-Swarm AI Simulator — Training Launch Script
#
# Starts three components in order:
#   1. Debug Visualizer (opens browser)
#   2. Rust Micro-Core (background, waits for ZMQ ready)
#   3. Python ML Training (foreground)
#
# Usage:
#   ./train.sh
#   ./train.sh --profile profiles/custom.json --timesteps 500000
#   ./train.sh --no-visualizer  # skip opening browser
#
# Ctrl+C stops training and kills all background processes.
# ═══════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROFILE="profiles/default_swarm_combat.json"
TIMESTEPS=100000
OPEN_VIZ=true
EXTRA_ARGS=""

# Parse known flags, forward unknown to Python
while [[ $# -gt 0 ]]; do
    case "$1" in
        --profile) PROFILE="$2"; shift 2 ;;
        --timesteps) TIMESTEPS="$2"; shift 2 ;;
        --no-visualizer) OPEN_VIZ=false; shift ;;
        *) EXTRA_ARGS+=" $1"; shift ;;
    esac
done

RUST_PID=""
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    if [[ -n "$RUST_PID" ]]; then
        kill "$RUST_PID" 2>/dev/null || true
        wait "$RUST_PID" 2>/dev/null || true
        echo "   Rust Micro-Core stopped"
    fi
    echo "   Done."
}
trap cleanup EXIT INT TERM

# 1. Open Debug Visualizer
if $OPEN_VIZ; then
    echo "🌐 Opening Debug Visualizer..."
    open "$SCRIPT_DIR/debug-visualizer/index.html" 2>/dev/null || \
    xdg-open "$SCRIPT_DIR/debug-visualizer/index.html" 2>/dev/null || \
    echo "   (Could not auto-open browser — open debug-visualizer/index.html manually)"
fi

# 2. Build and start Rust Micro-Core
echo "⚙️  Building Rust Micro-Core..."
(cd "$SCRIPT_DIR/micro-core" && cargo build --release 2>&1)
echo "🦀 Starting Rust Micro-Core (background)..."
(cd "$SCRIPT_DIR/micro-core" && cargo run --release 2>&1 | sed 's/^/   [rust] /') &
RUST_PID=$!

# Wait for ZMQ port to be ready
echo "⏳ Waiting for ZMQ port 5555..."
for i in $(seq 1 30); do
    if lsof -i :5555 >/dev/null 2>&1; then
        echo "   ✅ ZMQ ready"
        break
    fi
    sleep 1
    if [[ $i -eq 30 ]]; then
        echo "   ❌ ZMQ port 5555 not ready after 30s — aborting"
        exit 1
    fi
done

# Wait for WS port too
echo "⏳ Waiting for WebSocket port 8080..."
for i in $(seq 1 10); do
    if lsof -i :8080 >/dev/null 2>&1; then
        echo "   ✅ WebSocket ready"
        break
    fi
    sleep 1
done

# 3. Start Python training
echo "🧠 Starting ML Training..."
echo "   Profile:   $PROFILE"
echo "   Timesteps: $TIMESTEPS"
echo ""
cd "$SCRIPT_DIR/macro-brain"
source venv/bin/activate 2>/dev/null || true
python -m src.training.train \
    --profile "$PROFILE" \
    --timesteps "$TIMESTEPS" \
    $EXTRA_ARGS
```

Mark as executable: `chmod +x train.sh`

### Verification Strategy
```
Test_Type: manual_steps
Manual_Steps:
  - ./train.sh --help → should show usage (from Python argparse)
  - ./train.sh --no-visualizer --timesteps 0 → should build Rust, start it,
    create run dir, and exit cleanly after 0 timesteps
  - Ctrl+C during training → Rust process should be killed cleanly
```

---

## Task C3: TRAINING_STATUS.md Rewrite

**Model Tier:** `basic`
**Domain:** Markdown
**Dependencies:** B1 (5-stage curriculum must be finalized)

### Target Files
- **[REWRITE]** `TRAINING_STATUS.md`

### Strict Instructions

Completely rewrite `TRAINING_STATUS.md` to reflect the actual codebase. Key sections:

1. **Architecture** — Keep existing diagram but update entity counts to 50v50
2. **Completed Phases** — Keep Phases 1-3, add Phase 3.5 (Training Pipeline Readiness)
3. **5-Stage Curriculum** — Table with Map, Bot Behavior, Actions, Graduation for all 5 stages
4. **Bot Behavior System** — Explain the 4 strategies (Charge, HoldPosition, Adaptive, Mixed)
5. **Reward Function** — Replace stale 5-component formula with actual exploit-proof zero-sum:
   ```
   reward = time_penalty + kill_trading + terminal_bonus + survival_bonus
   ```
   Document each component with weights from the profile
6. **How to Train** — Reference `train.sh`, document profile flag, run directory structure
7. **Training Runs** — Empty table with correct column headers for logging runs
8. **Safety Patches** — Keep existing 8 patches
9. **Test Health** — Update counts to reflect new tests

**Critical: every constant MUST be cross-referenced against:**
- `profiles/default_swarm_combat.json` for game parameters
- `src/env/rewards.py` for reward formula
- `src/training/curriculum.py` for spawn configs
- `src/training/callbacks.py` for curriculum transitions

### Verification Strategy
```
Test_Type: manual_steps
Manual_Steps:
  - Every number in the document matches the source code or profile JSON
  - Reward formula matches rewards.py exactly
  - Curriculum stages match the profile's training.curriculum array
  - Bot strategies match bot_stage_behaviors in profile
  - No references to "300v300" or the old 5-component reward
```

