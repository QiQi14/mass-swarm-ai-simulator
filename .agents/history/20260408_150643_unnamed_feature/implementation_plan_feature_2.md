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
