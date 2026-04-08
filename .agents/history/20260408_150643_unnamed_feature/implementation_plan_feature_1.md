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
