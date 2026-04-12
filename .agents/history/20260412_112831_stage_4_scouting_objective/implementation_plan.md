# Stage 4 Curriculum Refactor

The objective is to fix curriculum Stage 4 learnability issues stemming from sparse gradients in fog-of-war conditions. We will re-purpose `ch7` to provide a randomized "Intel Ping" in the vicinity of the active target to guide the swarm. Crucially, the ping will decay over time, granting small rewards for proactive scouting and penalties for idling. We will also update the reward structure to remove death penalties without removing time pressure.

## User Review Required

> [!IMPORTANT]
> **Dissipate Time Calculation based on Game Physics:**
> - **Speed**: The swarm speed is `60.0 units/sec`.
> - **Map Distances**: Center to edge is `300 units` (5.0s travel). Edge to opposite edge is `600 units` (10.0s travel).
> - **Action Rate**: `ai_eval_interval_ticks` = `30 ticks`. At a 60Hz simulation rate, 1 agent step = `0.5 seconds`.
> - **Calculated Lifespan**: I have set the ping lifespan to **10 agent steps** (which equals **300 engine ticks**, or exactly **5.0 seconds**).
> - *Behavioral result*: When switching from Target A to Target B (600 units away, 10 sec travel), the first ping will inherently dissipate on route (giving the agent a small `-1.0` penalty and a visual indicator that the intel refreshed), and the second ping will be reached successfully for a `+1.0` reward. This mathematically matches your `<5s` design requirement.
> Let me know if you approve this math!

## Proposed Changes

---

### Phase 1: Observation Vectorizer and Reward Tuning

#### [MODIFY] [vectorizer.py](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/macro-brain/src/utils/vectorizer.py)
- **Signature Change**: Update `vectorize_snapshot` to accept `active_objective_ping: tuple[float, float] | None = None` and `ping_intensity: float = 1.0`.
- **ch7 Rendering**: Read `active_objective_ping`. If provided:
  - Map the world coordinate to grid coordinates.
  - Render a blurred 5x5 heatmap blob (centered on the ping) into `channels[7]`. 
  - The cell value calculation will be `max(0.0, ping_intensity - dist / 3.0)` so the entire blob visually fades out as `ping_intensity` drops.

#### [MODIFY] [rewards.py](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/macro-brain/src/env/rewards.py)
- **Exploration Reward**: Add `4` to the valid exploration stages check: `if stage in (2, 4, 7, 8) and fog_explored is not None:`. This ensures the agent is rewarded per tile revealed in Stage 4.
- **Eliminate Dead Penalty**: Inside `compute_shaped_reward`:
  - `compute_shaped_reward` calculates reward per step (tick). The `-0.01` time penalty per-step forces the model to move quickly.
  - To implement "eliminate the dead penalty", add `if stage == 4: own_lost = 0` during the combat trading calculation. The net result is that the time pressure remains, but dying to the fog/target does not penalize the model in Stage 4.

---

### Phase 2: Environment Objective State & Spawn Management

#### [MODIFY] [curriculum.py](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/macro-brain/src/training/curriculum.py)
- **_spawns_stage4**: Modify to hardcode `fid_a = 1` and `fid_b = 2`.
- Spawn `fid_a` (Target A) at a random map edge, with 15 units and 60 HP.
- Spawn `fid_b` (Target B) at the *opposite* map edge, with 15 units and 60 HP.
- Return `{"trap_faction": fid_a, "target_faction": fid_a}` for metadata mapping.

#### [MODIFY] [swarm_env.py](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/macro-brain/src/env/swarm_env.py)
- **State Initialization (`__init__`/`reset`)**: 
  - Initialize `self._active_objective_fid = 1`, `self._active_ping: tuple[float, float] | None = None`.
  - Initialize `self._ping_timer = 0` and `self._ping_lifespan = 10` (10 steps = 300 ticks = 5.0 seconds).
- **Target & Ping Polling (`step`)**: 
  - **Ping Decay & Interaction Check**: If `self._active_ping` is set, increment `self._ping_timer + 1`. Calculate distance from the Brain's centroid (via `_get_density_centroid`) to the `_active_ping`.
    - If `dist < 60.0`: **Success**. Add `+1.0` to the step `reward` and clear `_active_ping = None`.
    - If `self._ping_timer >= self._ping_lifespan`: **Failure**. Add `-1.0` to the step `reward` and clear `_active_ping = None` (so it regenerates).
  - **Switch Target Check**: Verify the live count of `self._active_objective_fid`. If `count <= 0` and the current objective is `1`, automatically switch `self._active_objective_fid = 2` and clear `self._active_ping = None`.
  - **Ping Generation**: If `self._active_ping` is `None`:
    - Retrieve the centroid of `self._active_objective_fid`.
    - Apply a random spatial jitter: `x = np.random.uniform(-80, 80)`, `y = np.random.uniform(-80, 80)`.
    - Set `self._active_ping` to the clamped spatial area and reset `self._ping_timer = 0`.
  - **Pass to Vectorizer**: Call `vectorize_snapshot` with `active_objective_ping=self._active_ping` and `ping_intensity=max(0.0, 1.0 - self._ping_timer / self._ping_lifespan)`.

## DAG Execution Plan
- **Phase 1**: Update `vectorizer.py` and `rewards.py` (Domain: Observations & Rewards).
- **Phase 2**: Update `curriculum.py` and `swarm_env.py` (Domain: Mechanics & Spawns).

## Verification Plan

### Automated Tests
- Run `cd macro-brain && python -m pytest tests/` to ensure no regression in `vectorizer.py` or reward computations.

### Manual Verification
- Render the curriculum stage in the visualizer for Stage 4.
- Observe `ch7` showing a blurry hotspot that linearly degrades/fades out step-over-step (10 steps to fade completely, approx 5s).
- If the agent hits the zone, the hotspot should jump to a new "fuzzed" location near the objective and the intensity restarts.
- Once Target A is eliminated, the target ID flips and the hotspot anchors to Target B.
