# Task 02: Tactical Reward Components

```yaml
Task_ID: task_02_reward_components
Execution_Phase: 1
Model_Tier: standard
Dependencies: []
Target_Files:
  - macro-brain/src/env/rewards.py
  - macro-brain/src/config/definitions.py
Context_Bindings:
  - context/architecture
  - context/conventions
```

## Objective

Extend the reward system with tactical shaping signals: exploration, flanking geometry, lure success, and threat priority bonuses. Update `RewardWeights` to hold all new weights.

## Strict Instructions

### 1. Extend `RewardWeights` in `definitions.py`

Add new fields to the frozen dataclass (after existing fields):

```python
@dataclass(frozen=True)
class RewardWeights:
    time_penalty_per_step: float
    kill_reward: float
    death_penalty: float
    win_terminal: float
    loss_terminal: float
    survival_bonus_multiplier: float
    # New tactical reward weights
    approach_scale: float = 0.02
    exploration_reward: float = 0.005
    exploration_decay_threshold: float = 0.8  # decay to 0 after 80% explored
    threat_priority_bonus: float = 2.0
    flanking_bonus_scale: float = 0.1
    lure_success_bonus: float = 3.0
    debuff_bonus: float = 2.0
```

### 2. Add new reward functions in `rewards.py`

Keep the existing `flanking_bonus()` and `compute_shaped_reward()` functions. Add the following NEW functions:

#### a. Exploration Reward

```python
def exploration_reward(
    fog_explored: np.ndarray,
    prev_fog_explored: np.ndarray | None,
    reward_per_cell: float = 0.005,
    decay_threshold: float = 0.8,
) -> float:
    """Reward for exploring new map cells under fog of war.
    
    Returns positive reward proportional to number of newly explored cells.
    Decays to 0 once decay_threshold (e.g., 80%) of map is explored.
    
    Args:
        fog_explored: Current explored grid (binary 50x50).
        prev_fog_explored: Previous step's explored grid.
        reward_per_cell: Reward per newly revealed cell.
        decay_threshold: Fraction of map above which reward decays to 0.
    """
    if prev_fog_explored is None:
        return 0.0
    
    # Count active (non-padding) cells: padding has terrain=wall,
    # but fog_explored in padding is always 1.0 — so we can't simply sum.
    # Caller must pass ONLY the active portion or track total active cells.
    explored_pct = fog_explored.mean()
    if explored_pct >= decay_threshold:
        return 0.0
    
    new_cells = np.sum((fog_explored > 0.5) & (prev_fog_explored < 0.5))
    return float(new_cells) * reward_per_cell
```

#### b. Threat Priority Bonus

```python
def threat_priority_bonus(
    snapshot: dict,
    enemy_factions: list[int],
    bonus: float = 2.0,
) -> float:
    """Bonus when the smaller/weaker enemy faction is eliminated first.
    
    Fires once when the first enemy faction reaches 0 count AND it was
    the faction with fewer starting units (or lower avg HP).
    
    Returns bonus if correct target eliminated first, 0.0 otherwise.
    """
    counts = snapshot.get("summary", {}).get("faction_counts", {})
    
    alive = []
    dead = []
    for fid in enemy_factions:
        c = counts.get(str(fid), counts.get(fid, 0))
        if c <= 0:
            dead.append(fid)
        else:
            alive.append(fid)
    
    # Only fires when exactly one enemy faction is dead and others alive
    if len(dead) != 1 or len(alive) == 0:
        return 0.0
    
    # Check if the dead faction was the smaller one (correct target)
    # Use faction_avg_stats HP as tiebreaker
    avg_stats = snapshot.get("summary", {}).get("faction_avg_stats", {})
    dead_fid = dead[0]
    
    # Heuristic: the "correct" target is the one with fewer units at start
    # This is determined by the profile, but we approximate from count ratios
    # The bonus is applied by the env which knows the faction configs
    return bonus
```

#### c. Flanking Geometry Score

```python
def compute_flanking_score(
    brain_centroid: tuple[float, float] | None,
    sub_centroid: tuple[float, float] | None,
    enemy_centroid: tuple[float, float] | None,
) -> float:
    """Compute flanking angle score between main body and sub-faction.
    
    Returns 0.0-1.0 based on the angle between:
      main_body → enemy vector
      sub_faction → enemy vector
    
    Score = angle / 180°. Angle > 60° = flanking. 180° = perfect pincer.
    Returns 0.0 if any centroid is missing.
    """
    if brain_centroid is None or sub_centroid is None or enemy_centroid is None:
        return 0.0
    
    bx, by = brain_centroid
    sx, sy = sub_centroid
    ex, ey = enemy_centroid
    
    # Vectors: brain→enemy and sub→enemy
    v1 = (ex - bx, ey - by)
    v2 = (ex - sx, ey - sy)
    
    len1 = (v1[0]**2 + v1[1]**2)**0.5
    len2 = (v2[0]**2 + v2[1]**2)**0.5
    
    if len1 < 0.01 or len2 < 0.01:
        return 0.0
    
    dot = v1[0]*v2[0] + v1[1]*v2[1]
    cos_angle = max(-1.0, min(1.0, dot / (len1 * len2)))
    
    import math
    angle_rad = math.acos(cos_angle)
    angle_deg = math.degrees(angle_rad)
    
    # Score: angle / 180, clamped to [0, 1]
    return min(angle_deg / 180.0, 1.0)
```

### 3. Update `compute_shaped_reward()` 

Add a `stage` parameter and `fog_explored`/`prev_fog_explored` parameters. Integrate the new components conditionally by stage:

```python
def compute_shaped_reward(
    snapshot: dict,
    prev_snapshot: dict | None,
    brain_faction: int,
    enemy_faction: int | list[int],
    reward_weights: RewardWeights | None = None,
    starting_entities: float = 50.0,
    stage: int = 1,
    fog_explored: np.ndarray | None = None,
    prev_fog_explored: np.ndarray | None = None,
    flanking_score: float = 0.0,
    lure_success: bool = False,
    threat_priority_hit: bool = False,
) -> float:
```

Inside the function, after existing reward computation, add:

```python
    # ── 5. EXPLORATION (Stages 2, 7, 8) ─────────────────────
    if stage in (2, 7, 8) and fog_explored is not None:
        reward += exploration_reward(
            fog_explored, prev_fog_explored,
            reward_weights.exploration_reward,
            reward_weights.exploration_decay_threshold,
        )
    
    # ── 6. THREAT PRIORITY (Stage 1+) ───────────────────────
    if threat_priority_hit:
        reward += reward_weights.threat_priority_bonus
    
    # ── 7. FLANKING GEOMETRY (Stage 5+) ─────────────────────
    if stage >= 5 and flanking_score > 0.0:
        reward += reward_weights.flanking_bonus_scale * flanking_score
    
    # ── 8. LURE SUCCESS (Stage 6+) ──────────────────────────
    if stage >= 6 and lure_success:
        reward += reward_weights.lure_success_bonus
```

### 4. Preserve existing functions

Keep `flanking_bonus()` as-is (it's still used by the old reward path and may be useful as reference). The new `compute_flanking_score()` is a simplified version used by swarm_env directly.

## Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: unit
  Test_Stack: pytest (macro-brain)
  Acceptance_Criteria:
    - "RewardWeights accepts all new fields with defaults"
    - "exploration_reward returns 0.0 when prev is None"
    - "exploration_reward returns positive for newly explored cells"
    - "exploration_reward returns 0.0 when explored_pct >= threshold"
    - "compute_flanking_score returns 0.0 when any centroid is None"
    - "compute_flanking_score returns ~0.5 for 90° angle"
    - "compute_flanking_score returns ~1.0 for 180° angle"
    - "compute_shaped_reward includes exploration only at stages 2,7,8"
    - "compute_shaped_reward includes flanking only at stage >= 5"
    - "Gradient: tactical win > brute force win > loss ≈ timeout"
  Suggested_Test_Commands:
    - "cd macro-brain && python -m pytest tests/test_rewards.py -v"
```
