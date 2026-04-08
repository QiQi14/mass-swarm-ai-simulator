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
