# Feature 3: Python Gymnasium Environment & Training (v3 — Patched)

> **Tasks:** 04 (Project Scaffold), 06 (SwarmEnv), 08 (PPO Training), 09 (Reward Shaping)
> **Domain:** Python / PyTorch / Gymnasium
> **v3 Patches:** Pacifist Flank exploit, Static Epicenter, Sub-Faction Desync, ZMQ Deadlock, MDP Pollution

---

> [!CAUTION]
> ## Critical Vulnerability Patches (P5–P8)
> Four vulnerabilities were identified during RL stress-testing. All patches are **mandatory**.
>
> | # | Vulnerability | Severity | Fix |
> |---|--------------|----------|-----|
> | **P5** | **Pacifist Flank** — sub-faction runs to corner, gets infinite flanking reward | 🔴 Critical | Distance cutoff + attenuation in `flanking_bonus` |
> | **P6** | **Static Epicenter** — hardcoded split point misses the swarm | 🟠 High | Dynamic epicenter from density centroid |
> | **P7** | **Sub-Faction Desync** — Python tracks ghost sub-factions | 🟠 High | Read from Rust snapshot (single source of truth) |
> | **P8** | **ZMQ Deadlock + MDP Pollution** — timeout crashes SB3, interventions poison value estimates | 🔴 Critical | Timeout → truncate episode; Tick swallowing loop |

---

## Task 04: Python Project Scaffold

**Task_ID:** `task_04_python_scaffold`
**Execution_Phase:** 1 (parallel)
**Model_Tier:** `basic`
**Target_Files:**
  - `macro-brain/requirements.txt` (MODIFY)
  - `macro-brain/src/env/__init__.py` (NEW)
  - `macro-brain/src/env/spaces.py` (NEW)
  - `macro-brain/src/utils/__init__.py` (NEW)
  - `macro-brain/src/utils/vectorizer.py` (NEW)
  - `macro-brain/src/training/__init__.py` (NEW)
  - `macro-brain/tests/__init__.py` (NEW)
  - `macro-brain/tests/test_vectorizer.py` (NEW)
**Dependencies:** None

### Strict Instructions

#### 1. Update `requirements.txt`

```
pyzmq>=25.1.2
gymnasium>=1.2.0
numpy>=2.0.0
stable-baselines3>=2.6.0
torch>=2.11.0
tensorboard>=2.19.0
pytest>=8.0.0
```

#### 2. Create Package Structure (`__init__.py` files)

```python
# macro-brain/src/env/__init__.py
"""Gymnasium environment for the Mass-Swarm AI Simulator."""

# macro-brain/src/utils/__init__.py
"""Utility functions for state vectorization and data processing."""

# macro-brain/src/training/__init__.py
"""Training scripts and callbacks for PPO."""

# macro-brain/tests/__init__.py
"""Test suite for macro-brain."""
```

#### 3. Observation/Action Space Definitions (`spaces.py`)

```python
"""
Observation and Action space definitions for SwarmEnv.

Observation:
  4-channel density heatmaps (brain, enemy, sub-faction ×2)
  + terrain + summary stats

Action: Discrete(8) → MacroDirective mapping
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np

GRID_WIDTH = 50
GRID_HEIGHT = 50
NUM_DENSITY_CHANNELS = 4

# Action indices
ACTION_HOLD = 0
ACTION_UPDATE_NAV = 1
ACTION_FRENZY = 2
ACTION_RETREAT = 3
ACTION_ZONE_MODIFIER = 4
ACTION_SPLIT_FACTION = 5
ACTION_MERGE_FACTION = 6
ACTION_SET_AGGRO_MASK = 7

ACTION_NAMES = {
    ACTION_HOLD: "Hold",
    ACTION_UPDATE_NAV: "UpdateNavigation",
    ACTION_FRENZY: "TriggerFrenzy",
    ACTION_RETREAT: "Retreat",
    ACTION_ZONE_MODIFIER: "SetZoneModifier",
    ACTION_SPLIT_FACTION: "SplitFaction",
    ACTION_MERGE_FACTION: "MergeFaction",
    ACTION_SET_AGGRO_MASK: "SetAggroMask",
}

def make_observation_space() -> spaces.Dict:
    return spaces.Dict({
        "density_ch0": spaces.Box(0.0, 1.0, shape=(GRID_HEIGHT, GRID_WIDTH), dtype=np.float32),
        "density_ch1": spaces.Box(0.0, 1.0, shape=(GRID_HEIGHT, GRID_WIDTH), dtype=np.float32),
        "density_ch2": spaces.Box(0.0, 1.0, shape=(GRID_HEIGHT, GRID_WIDTH), dtype=np.float32),
        "density_ch3": spaces.Box(0.0, 1.0, shape=(GRID_HEIGHT, GRID_WIDTH), dtype=np.float32),
        "terrain": spaces.Box(0.0, 1.0, shape=(GRID_HEIGHT, GRID_WIDTH), dtype=np.float32),
        "summary": spaces.Box(0.0, 1.0, shape=(6,), dtype=np.float32),
    })

def make_action_space() -> spaces.Discrete:
    return spaces.Discrete(8)
```

#### 4. Vectorizer Utility (`vectorizer.py`)

*Channel packing is Python's responsibility (not Rust's — see Data Isolation principle).*

```python
"""State vectorization: JSON snapshot → numpy observation dict.

This is the SINGLE location where raw Rust density maps (HashMap<u32, Vec<f32>>)
are packed into fixed 4-channel tensors for the neural network.
Channel assignment:
  ch0 = brain_faction
  ch1 = primary enemy
  ch2 = first sub-faction (sorted by ID)
  ch3 = second sub-faction or overflow aggregation
"""

import numpy as np
from typing import Any

from macro_brain.src.env.spaces import GRID_WIDTH, GRID_HEIGHT, NUM_DENSITY_CHANNELS


def vectorize_snapshot(
    snapshot: dict[str, Any],
    brain_faction: int = 0,
    enemy_faction: int = 1,
) -> dict[str, np.ndarray]:
    """Convert Rust StateSnapshot → numpy observation dict."""
    density_maps = snapshot.get("density_maps", {})
    grid_size = GRID_HEIGHT * GRID_WIDTH

    channels = [np.zeros((GRID_HEIGHT, GRID_WIDTH), dtype=np.float32)
                for _ in range(NUM_DENSITY_CHANNELS)]

    # ch0: brain's own forces
    key = str(brain_faction)
    if key in density_maps:
        flat = np.array(density_maps[key], dtype=np.float32)
        if len(flat) == grid_size:
            channels[0] = flat.reshape(GRID_HEIGHT, GRID_WIDTH)

    # ch1: primary enemy
    key = str(enemy_faction)
    if key in density_maps:
        flat = np.array(density_maps[key], dtype=np.float32)
        if len(flat) == grid_size:
            channels[1] = flat.reshape(GRID_HEIGHT, GRID_WIDTH)

    # ch2-3: sub-factions (sorted by ID for determinism)
    sub_factions = sorted([
        int(k) for k in density_maps.keys()
        if int(k) != brain_faction and int(k) != enemy_faction
    ])
    for i, sf in enumerate(sub_factions):
        ch_idx = min(2 + i, NUM_DENSITY_CHANNELS - 1)
        flat = np.array(density_maps[str(sf)], dtype=np.float32)
        if len(flat) == grid_size:
            if i >= NUM_DENSITY_CHANNELS - 2:
                channels[ch_idx] += flat.reshape(GRID_HEIGHT, GRID_WIDTH)
            else:
                channels[ch_idx] = flat.reshape(GRID_HEIGHT, GRID_WIDTH)

    # Terrain
    terrain = np.ones((GRID_HEIGHT, GRID_WIDTH), dtype=np.float32) * 0.5
    terrain_hard = snapshot.get("terrain_hard", [])
    if len(terrain_hard) == grid_size:
        raw = np.array(terrain_hard, dtype=np.float32)
        terrain = np.clip(raw / 65535.0, 0.0, 1.0).reshape(GRID_HEIGHT, GRID_WIDTH)

    # Summary: 6 elements
    summary_data = snapshot.get("summary", {})
    faction_counts = summary_data.get("faction_counts", {})
    faction_avg = summary_data.get("faction_avg_stats", {})
    own_count = faction_counts.get(str(brain_faction), 0)
    enemy_count = faction_counts.get(str(enemy_faction), 0)
    max_entities = 10000.0

    own_health = 0.0
    if str(brain_faction) in faction_avg:
        h = faction_avg[str(brain_faction)]
        own_health = h[0] if h else 0.0

    enemy_health = 0.0
    if str(enemy_faction) in faction_avg:
        h = faction_avg[str(enemy_faction)]
        enemy_health = h[0] if h else 0.0

    sub_faction_count = len(snapshot.get("active_sub_factions", []))
    active_zones_count = len(snapshot.get("active_zones", []))

    summary = np.array([
        min(own_count / max_entities, 1.0),
        min(enemy_count / max_entities, 1.0),
        own_health,
        enemy_health,
        min(sub_faction_count / 5.0, 1.0),
        min(active_zones_count / 10.0, 1.0),
    ], dtype=np.float32)

    return {
        "density_ch0": channels[0],
        "density_ch1": channels[1],
        "density_ch2": channels[2],
        "density_ch3": channels[3],
        "terrain": terrain,
        "summary": summary,
    }
```

---

## Task 06: SwarmEnv Gymnasium Environment (Patched)

**Task_ID:** `task_06_swarm_env`
**Execution_Phase:** 2
**Model_Tier:** `advanced` *(upgraded from standard — tick swallowing + deadlock handling is complex)*
**Target_Files:**
  - `macro-brain/src/env/swarm_env.py` (NEW)
  - `macro-brain/tests/test_swarm_env.py` (NEW)
**Dependencies:** Task 04
**Context_Bindings:**
  - `context/ipc-protocol`
  - `context/tech-stack`
  - `context/conventions`

### Strict Instructions

> [!IMPORTANT]
> ## ZMQ Socket Protocol: REP (Python) ↔ REQ (Rust)
> Python uses `zmq.REP` (binds on `tcp://*:5555`).
> Rust uses `zmq.REQ` (connects to `tcp://127.0.0.1:5555`).
>
> **REP enforces strict `recv → send` alternation.  You CANNOT send before recv.**
>
> The flow per tick is:
> 1. Rust sends state snapshot (REQ.send)
> 2. Python receives it (REP.recv)
> 3. Python sends directive (REP.send)
> 4. Rust receives directive (REQ.recv)
>
> Every `recv` MUST be followed by exactly one `send`. No exceptions.

#### SwarmEnv Implementation

```python
"""
SwarmEnv — Gymnasium environment for Mass-Swarm AI Simulator.

Communicates with the Rust Micro-Core via ZMQ REP socket.

## SAFETY INVARIANTS (v3 Patches)
P6: Dynamic epicenter from density centroid (not hardcoded)
P7: Sub-faction state read from Rust snapshot (single source of truth)
P8: ZMQ timeout → episode truncation; Tick swallowing for interventions
"""

import json
import numpy as np
import zmq
import gymnasium as gym

from macro_brain.src.env.spaces import (
    make_observation_space, make_action_space,
    ACTION_HOLD, ACTION_UPDATE_NAV, ACTION_FRENZY, ACTION_RETREAT,
    ACTION_ZONE_MODIFIER, ACTION_SPLIT_FACTION, ACTION_MERGE_FACTION,
    ACTION_SET_AGGRO_MASK, GRID_WIDTH, GRID_HEIGHT,
)
from macro_brain.src.utils.vectorizer import vectorize_snapshot


class SwarmEnv(gym.Env):
    """Gymnasium environment wrapping the Rust simulation via ZMQ."""

    metadata = {"render_modes": []}

    def __init__(self, config: dict | None = None):
        super().__init__()
        config = config or {}
        self.bind_address = config.get("bind_address", "tcp://*:5555")
        self.max_steps = config.get("max_steps", 200)
        self.brain_faction = config.get("brain_faction", 0)
        self.enemy_faction = config.get("enemy_faction", 1)
        self.world_width = config.get("world_width", 1000.0)
        self.world_height = config.get("world_height", 1000.0)
        self.zmq_timeout_ms = config.get("zmq_timeout_ms", 10000)

        self.observation_space = make_observation_space()
        self.action_space = make_action_space()

        # ═══════════════════════════════════════════════════════════
        # PATCH 7: Sub-Faction State — Single Source of Truth
        # These are populated from the Rust snapshot, NEVER locally.
        # ═══════════════════════════════════════════════════════════
        self._active_sub_factions: list[int] = []
        self._last_aggro_state: bool = True
        self._last_snapshot: dict | None = None
        self._step_count: int = 0

        # ZMQ setup
        self._ctx = zmq.Context()
        self._socket: zmq.Socket | None = None
        self._connect()

    def _connect(self):
        """Create and bind the REP socket with timeout."""
        if self._socket is not None:
            self._socket.close()
        self._socket = self._ctx.socket(zmq.REP)
        self._socket.setsockopt(zmq.RCVTIMEO, self.zmq_timeout_ms)
        self._socket.setsockopt(zmq.SNDTIMEO, self.zmq_timeout_ms)
        self._socket.setsockopt(zmq.LINGER, 0)
        self._socket.bind(self.bind_address)

    def _disconnect(self):
        """Close and unbind the socket."""
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._step_count = 0
        self._active_sub_factions = []
        self._last_aggro_state = True
        self._last_snapshot = None

        # ═══════════════════════════════════════════════════════════
        # PATCH 8: ZMQ Deadlock Prevention (Reset)
        # REP socket flow: recv → send (mandatory alternation)
        # ═══════════════════════════════════════════════════════════
        try:
            raw = self._socket.recv_string()
        except zmq.error.Again:
            print("[SwarmEnv] ZMQ Timeout during reset. Rust not running.")
            self._disconnect()
            self._connect()
            return self.observation_space.sample(), {}

        snapshot = json.loads(raw)
        self._last_snapshot = snapshot

        # PATCH 7: Sync sub-factions from Rust truth
        self._active_sub_factions = snapshot.get("active_sub_factions", [])

        # Send Hold reply (balanced recv → send)
        self._socket.send_string(json.dumps(
            {"type": "macro_directive", "directive": "Hold"}
        ))

        obs = vectorize_snapshot(snapshot, self.brain_faction, self.enemy_faction)
        return obs, {}

    def step(self, action: int):
        self._step_count += 1

        # ═══════════════════════════════════════════════════════════
        # PATCH 8: Tick Swallowing Loop
        #
        # ZMQ REP flow: recv (state) → send (directive)
        # For intervention ticks: recv → send Hold (swallow the tick)
        # For normal ticks: recv → send action directive
        #
        # This completely hides engine interventions from SB3.
        # The MDP only sees physics frames — never scripted overrides.
        # ═══════════════════════════════════════════════════════════
        snapshot = None
        while True:
            try:
                raw = self._socket.recv_string()
            except zmq.error.Again:
                print("[SwarmEnv] ZMQ Timeout. Rust Core paused/crashed. Truncating episode.")
                # Reset socket state (mandatory after REP timeout)
                self._disconnect()
                self._connect()
                # Safely end episode without crashing SB3
                # truncated=True tells SB3 this isn't a natural episode end
                return (
                    self.observation_space.sample(),
                    0.0,
                    False,       # terminated
                    True,        # truncated
                    {"error": "ZMQ_TIMEOUT"},
                )

            snapshot = json.loads(raw)
            intervention = snapshot.get("intervention_active", False)

            if intervention:
                # ── TICK SWALLOWING ──
                # Engine is intervening (cutscene, player ability, etc.)
                # Reply Hold to keep Rust moving, but DON'T return to SB3.
                # SB3 never sees this tick → MDP stays clean.
                self._socket.send_string(json.dumps(
                    {"type": "macro_directive", "directive": "Hold"}
                ))
                continue  # Loop back to recv next tick
            else:
                break  # Normal physics frame — proceed to RL

        # ─── Normal Frame Processing ──────────────────────────────

        # PATCH 7: Sync sub-factions from Rust truth (every step)
        self._active_sub_factions = snapshot.get("active_sub_factions", [])
        self._last_snapshot = snapshot

        # Build and send directive (REP.send — completes recv→send)
        directive = self._action_to_directive(action)
        self._socket.send_string(json.dumps(directive))

        # Vectorize observation
        obs = vectorize_snapshot(snapshot, self.brain_faction, self.enemy_faction)

        # Compute reward (delegate to rewards.py)
        reward = self._compute_reward(snapshot)

        # Termination conditions
        own_count = snapshot.get("summary", {}).get("faction_counts", {}).get(
            str(self.brain_faction), 0
        )
        enemy_count = snapshot.get("summary", {}).get("faction_counts", {}).get(
            str(self.enemy_faction), 0
        )
        terminated = own_count == 0 or enemy_count == 0
        truncated = self._step_count >= self.max_steps

        info = {
            "tick": snapshot.get("tick", 0),
            "own_count": own_count,
            "enemy_count": enemy_count,
            "sub_factions": len(self._active_sub_factions),
        }

        return obs, reward, terminated, truncated, info

    # ─── Action Mapping ───────────────────────────────────────────

    def _action_to_directive(self, action: int) -> dict:
        """Map discrete action index to MacroDirective JSON."""
        if action == ACTION_HOLD:
            return {"type": "macro_directive", "directive": "Hold"}

        elif action == ACTION_UPDATE_NAV:
            return {
                "type": "macro_directive",
                "directive": "UpdateNavigation",
                "follower_faction": self.brain_faction,
                "target": {"type": "Faction", "faction_id": self.enemy_faction},
            }

        elif action == ACTION_FRENZY:
            return {
                "type": "macro_directive",
                "directive": "TriggerFrenzy",
                "faction": self.brain_faction,
                "speed_multiplier": 1.5,
                "duration_ticks": 120,
            }

        elif action == ACTION_RETREAT:
            return {
                "type": "macro_directive",
                "directive": "Retreat",
                "faction": self.brain_faction,
                "retreat_x": 50.0,
                "retreat_y": 50.0,
            }

        elif action == ACTION_ZONE_MODIFIER:
            # ═══ PATCH 6: Dynamic Center ═══
            # Use density centroid instead of hardcoded coordinates
            cx, cy = self._get_density_centroid(self.brain_faction)
            return {
                "type": "macro_directive",
                "directive": "SetZoneModifier",
                "target_faction": self.brain_faction,
                "x": cx,
                "y": cy,
                "radius": 100.0,
                "cost_modifier": -50.0,
            }

        elif action == ACTION_SPLIT_FACTION:
            # ═══════════════════════════════════════════════════════
            # PATCH 6: Context-Aware Epicenter
            #
            # The epicenter MUST be relative to where the swarm
            # actually IS, not a hardcoded map coordinate.
            # Otherwise, if the swarm is fighting at (200, 200),
            # a split at (800, 500) captures zero entities and
            # the agent learns "SplitFaction is useless."
            # ═══════════════════════════════════════════════════════
            cx, cy = self._get_density_centroid(self.brain_faction)

            # ═══════════════════════════════════════════════════════
            # PATCH 7: Safe Sub-Faction ID from Ground Truth
            # Don't use a local counter — use Rust's active list.
            # ═══════════════════════════════════════════════════════
            next_id = (max(self._active_sub_factions) + 1
                       if self._active_sub_factions else 101)

            return {
                "type": "macro_directive",
                "directive": "SplitFaction",
                "source_faction": self.brain_faction,
                "new_sub_faction": next_id,
                "percentage": 0.3,
                # Offset epicenter to naturally encourage flanking
                "epicenter": [cx + 100.0, cy + 100.0],
            }

        elif action == ACTION_MERGE_FACTION:
            # Merge the most recently created sub-faction
            if self._active_sub_factions:
                sf = self._active_sub_factions[-1]
                return {
                    "type": "macro_directive",
                    "directive": "MergeFaction",
                    "source_faction": sf,
                    "target_faction": self.brain_faction,
                }
            return {"type": "macro_directive", "directive": "Hold"}

        elif action == ACTION_SET_AGGRO_MASK:
            if self._active_sub_factions:
                sf = self._active_sub_factions[-1]
                self._last_aggro_state = not self._last_aggro_state
                return {
                    "type": "macro_directive",
                    "directive": "SetAggroMask",
                    "source_faction": sf,
                    "target_faction": self.enemy_faction,
                    "allow_combat": self._last_aggro_state,
                }
            return {"type": "macro_directive", "directive": "Hold"}

        return {"type": "macro_directive", "directive": "Hold"}

    # ─── Helpers ──────────────────────────────────────────────────

    def _get_density_centroid(self, faction: int) -> tuple[float, float]:
        """Calculate the world-space centroid of a faction's density map.

        Returns (world_x, world_y). Falls back to map center if no data.
        Used by PATCH 6 for context-aware epicenter calculation.
        """
        if self._last_snapshot is None:
            return self.world_width / 2.0, self.world_height / 2.0

        density_maps = self._last_snapshot.get("density_maps", {})
        key = str(faction)
        if key not in density_maps:
            return self.world_width / 2.0, self.world_height / 2.0

        flat = np.array(density_maps[key], dtype=np.float32)
        if len(flat) != GRID_WIDTH * GRID_HEIGHT:
            return self.world_width / 2.0, self.world_height / 2.0

        grid = flat.reshape(GRID_HEIGHT, GRID_WIDTH)
        total = grid.sum()
        if total < 0.01:
            return self.world_width / 2.0, self.world_height / 2.0

        rows, cols = np.indices(grid.shape)
        cy_cell = (rows * grid).sum() / total
        cx_cell = (cols * grid).sum() / total

        # Convert grid cells → world coordinates
        cell_w = self.world_width / GRID_WIDTH
        cell_h = self.world_height / GRID_HEIGHT
        return float(cx_cell * cell_w), float(cy_cell * cell_h)

    def _compute_reward(self, snapshot: dict) -> float:
        """Delegate to rewards.py (Task 09). Placeholder returns 0."""
        # Will be replaced by shaped reward in Task 09
        return 0.0

    def close(self):
        self._disconnect()
        self._ctx.term()
```

### Unit Tests (`test_swarm_env.py`)

These tests use a **mock ZMQ pair** (no live Rust needed):

1. `test_action_to_directive_hold`
2. `test_action_to_directive_update_nav`
3. `test_action_to_directive_frenzy`
4. `test_action_to_directive_retreat`
5. `test_action_to_directive_zone_modifier`
6. `test_action_to_directive_split_faction`
7. `test_action_to_directive_merge_faction_no_sub` — Falls back to Hold
8. `test_action_to_directive_aggro_mask_toggle`

### Patch Regression Tests (Mandatory)

9. **`test_patch6_dynamic_epicenter_uses_centroid`**
   - Mock snapshot with density_maps showing swarm at (200, 200)
   - Call `_action_to_directive(ACTION_SPLIT_FACTION)`
   - Assert: epicenter ≈ (300, 300), NOT (800, 500)

10. **`test_patch7_sub_factions_from_snapshot`**
    - Mock two step() calls with different `active_sub_factions` in snapshot
    - Assert: `env._active_sub_factions` matches snapshot, not local state

11. **`test_patch7_split_id_from_ground_truth`**
    - Set `_active_sub_factions = [101, 102]` via mock snapshot
    - Call `_action_to_directive(ACTION_SPLIT_FACTION)`
    - Assert: `new_sub_faction == 103`

12. **`test_density_centroid_empty_map`** — Returns map center

13. **`test_density_centroid_concentration`** — Centroid near dense cluster

---

## Task 08: PPO Training Loop

*(Unchanged from previous version — uses MultiInputPolicy, Discrete(8), SB3 PPO)*

---

## Task 09: Reward Shaping & Curriculum (Patched)

**Task_ID:** `task_09_reward_shaping`
**Execution_Phase:** 5
**Model_Tier:** `standard`
**Target_Files:**
  - `macro-brain/src/env/rewards.py` (NEW)
  - `macro-brain/src/env/swarm_env.py` (MODIFY — wire `_compute_reward`)
  - `macro-brain/tests/test_rewards.py` (NEW)
**Dependencies:** Task 08

### Strict Instructions

#### Patched `flanking_bonus` (P5: Pacifist Flank Fix)

```python
def flanking_bonus(
    own_density: np.ndarray,
    sub_faction_density: np.ndarray,
    enemy_density: np.ndarray,
    max_engage_radius: float = 15.0,  # Grid cells (~300 world units at 20px/cell)
) -> float:
    """Detect and reward flanking maneuvers with combat proximity guard.

    ## PATCH 5: Pacifist Flank Exploit Prevention
    The original implementation only checked projection geometry, not distance.
    An RL agent would exploit this by sending a sub-faction to the map corner,
    aligned with the projection axis, earning infinite flanking points while
    completely out of combat range.

    ## Fix
    1. Distance cutoff: sub-faction centroid must be within max_engage_radius
       of enemy centroid (in grid cells).
    2. Distance attenuation: reward decays linearly as distance increases.
       A flank at point-blank range gets full bonus; a flank at the edge
       of engage range gets near-zero bonus.

    Returns 0.0-1.0 (bonus only, never negative).
    """
    def centroid(density: np.ndarray) -> tuple[float, float] | None:
        total = density.sum()
        if total < 0.01:
            return None
        rows, cols = np.indices(density.shape)
        cy = (rows * density).sum() / total
        cx = (cols * density).sum() / total
        return (cx, cy)

    main_c = centroid(own_density)
    sub_c = centroid(sub_faction_density)
    enemy_c = centroid(enemy_density)

    if main_c is None or sub_c is None or enemy_c is None:
        return 0.0

    # ═══════════════════════════════════════════════════════════════
    # PATCH 5a: Combat Proximity Check
    # Sub-faction MUST be within engagement range of the enemy.
    # Without this, the agent parks the sub-faction at the map corner
    # and collects free flanking points forever.
    # ═══════════════════════════════════════════════════════════════
    dist_sub_to_enemy = (
        (sub_c[0] - enemy_c[0])**2 + (sub_c[1] - enemy_c[1])**2
    )**0.5

    if dist_sub_to_enemy > max_engage_radius:
        return 0.0  # Too far away — no flanking credit

    # Vector projection (existing logic)
    main_to_enemy = (enemy_c[0] - main_c[0], enemy_c[1] - main_c[1])
    main_to_sub = (sub_c[0] - main_c[0], sub_c[1] - main_c[1])

    main_to_enemy_len = (main_to_enemy[0]**2 + main_to_enemy[1]**2)**0.5
    main_to_sub_len = (main_to_sub[0]**2 + main_to_sub[1]**2)**0.5

    if main_to_enemy_len < 0.01 or main_to_sub_len < 0.01:
        return 0.0

    dot = main_to_enemy[0] * main_to_sub[0] + main_to_enemy[1] * main_to_sub[1]
    cos_sim = dot / (main_to_enemy_len * main_to_sub_len)

    if cos_sim > 0.5:
        projection_ratio = dot / (main_to_enemy_len**2)
        if projection_ratio > 1.0:
            raw_bonus = min(projection_ratio - 1.0, 1.0)

            # ═══════════════════════════════════════════════════════
            # PATCH 5b: Distance Attenuation
            # Reward decays linearly with distance to enemy.
            # At dist=0: full bonus. At dist=max_engage_radius: zero.
            # This prevents "barely in range" passive flanking.
            # ═══════════════════════════════════════════════════════
            proximity_multiplier = max(
                0.0,
                (max_engage_radius - dist_sub_to_enemy) / max_engage_radius
            )
            return raw_bonus * proximity_multiplier

    return 0.0
```

#### Shaped Reward (with flanking weight)

```python
def compute_shaped_reward(
    snapshot: dict,
    prev_snapshot: dict | None,
    brain_faction: int = 0,
    enemy_faction: int = 1,
    weights: dict | None = None,
) -> float:
    """Compute shaped reward from state transition.

    Components:
    - survival: positive for staying alive
    - kill: positive for eliminating enemies
    - territory: positive for occupying more cells
    - health: delta of average health
    - flanking: bonus for successful flank maneuvers (PATCH 5)
    """
    w = weights or {
        "survival": 0.25,
        "kill": 0.25,
        "territory": 0.15,
        "health": 0.15,
        "flanking": 0.20,
    }

    # ... [survival, kill, territory, health components — same as before] ...

    # Flanking bonus (uses patched version with proximity guard)
    flank = 0.0
    density_maps = snapshot.get("density_maps", {})
    own_key = str(brain_faction)
    enemy_key = str(enemy_faction)
    sub_factions = snapshot.get("active_sub_factions", [])

    if own_key in density_maps and enemy_key in density_maps and sub_factions:
        own_grid = np.array(density_maps[own_key]).reshape(50, 50)
        enemy_grid = np.array(density_maps[enemy_key]).reshape(50, 50)

        for sf in sub_factions:
            sf_key = str(sf)
            if sf_key in density_maps:
                sf_grid = np.array(density_maps[sf_key]).reshape(50, 50)
                flank = max(flank, flanking_bonus(own_grid, sf_grid, enemy_grid))

    total = (
        w["survival"] * survival
        + w["kill"] * kill
        + w["territory"] * territory
        + w["health"] * health_delta
        + w["flanking"] * flank
    )
    return total
```

### Patch Regression Tests (Mandatory)

14. **`test_patch5_pacifist_flank_exploit_blocked`**
    - Setup: main at (25, 25), enemy at (25, 30), sub-faction at (49, 49) (far corner, aligned axis)
    - Assert: `flanking_bonus() == 0.0` (too far from enemy)

15. **`test_patch5_genuine_flank_rewarded`**
    - Setup: main at (20, 25), enemy at (25, 25), sub at (30, 25) (behind enemy, close range)
    - Assert: `flanking_bonus() > 0.0`

16. **`test_patch5_distance_attenuation`**
    - Setup: same geometry, vary `dist_sub_to_enemy` from 1.0 to max_engage_radius
    - Assert: bonus decreases monotonically as distance increases

17. **`test_patch5_no_sub_faction_zero_bonus`**
    - Sub-faction density is all zeros → `flanking_bonus() == 0.0`

---

## Verification Strategy

```
Test_Type: unit + integration
Test_Stack: pytest (Python)
Acceptance_Criteria:
  PATCH 5: Pacifist flank exploit returns 0.0 for distant sub-factions
  PATCH 5: Genuine flank at close range returns > 0.0
  PATCH 5: Distance attenuation is monotonically decreasing
  PATCH 6: Epicenter calculated from density centroid, not hardcoded
  PATCH 7: _active_sub_factions always matches Rust snapshot
  PATCH 7: Sub-faction ID derived from ground truth, not local counter
  PATCH 8: ZMQ timeout truncates episode safely (truncated=True)
  PATCH 8: Intervention ticks swallowed (Hold reply, SB3 never sees them)
  All 8 action types mapped to correct MacroDirective JSON
Suggested_Test_Commands:
  - "cd macro-brain && python -m pytest tests/ -v"
```
