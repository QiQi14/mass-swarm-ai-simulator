# Bot Behaviors

## 6. Bot Behavior System

**File:** `macro-brain/src/env/bot_controller.py`

Bot factions (trap, target, patrol) are controlled by Python heuristics, NOT by the RL model.

### Strategies

| Strategy | Behavior |
|----------|----------|
| `HoldPosition` | Stay at spawn (sends `Idle`). Switches to `Charge` if debuff is applied. |
| `Charge` | Navigate toward target faction each step |
| `Patrol` | Alternate between waypoint list (with threshold proximity check) |
| `Adaptive` | Charge when healthy, retreat when losing (with hysteresis) |
| `Mixed` | Randomly pick one strategy per episode (anti-memorization) |

### Debuff-Aware Behavior

When Python's `_apply_trap_debuff()` fires in SwarmEnv:
1. `ActivateBuff` directive sent to Rust (reduces trap damage to 25%)
2. Trap's `BotController._debuff_applied = True`
3. On next `compute_directive()`, HoldPosition strategy detects flag → switches to `Charge`
4. Trap charges toward brain faction → guarantees engagement without brain retargeting

---