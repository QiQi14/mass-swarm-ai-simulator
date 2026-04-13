---
Task_ID: "task_02_stage4_curriculum"
Execution_Phase: 2
Model_Tier: "standard"
Target_Files:
  - "macro-brain/src/training/curriculum.py"
  - "macro-brain/src/env/swarm_env.py"
Dependencies: ["task_01_ch7_rewards"]
Context_Bindings:
  - "context/training-curriculum"
Strict_Instructions: |
  1. In `macro-brain/src/training/curriculum.py`:
     - Update `_spawns_stage4` to spawn Brain at center, Target A (fid 1) at a random edge, and Target B (fid 2) at the opposite edge. Each target has 15 count and 60.0 HP. Also import random if needed.
       ```python
       brain_count = _faction_count(profile, 0, 50)
       fid_a, fid_b = 1, 2
       target_count = 15
       edges = [(100.0, 400.0), (700.0, 400.0), (400.0, 100.0), (400.0, 700.0)]
       if rng is not None:
           idx = rng.integers(0, 4)
       else:
           import random
           idx = random.randint(0, 3)
           
       spawns = [
           {"faction_id": 0, "count": brain_count, "x": 400.0, "y": 400.0, "spread": 60.0, "stats": _faction_stats(profile, 0)},
           {"faction_id": fid_a, "count": target_count, "x": edges[idx][0], "y": edges[idx][1], "spread": 40.0, "stats": [{"index": 0, "value": 60.0}]},
           {"faction_id": fid_b, "count": target_count, "x": edges[(idx+2)%4][0], "y": edges[(idx+2)%4][1], "spread": 40.0, "stats": [{"index": 0, "value": 60.0}]},
       ]
       return spawns, {"trap_faction": fid_a, "target_faction": fid_a}
       ```
  2. In `macro-brain/src/env/swarm_env.py`:
     - In `__init__`, add:
       ```python
       self._active_objective_fid = 1
       self._active_ping: tuple[float, float] | None = None
       self._ping_timer = 0
       self._ping_lifespan = 10
       ```
     - In `reset()`, add reset inside the `super().reset(...)` block:
       ```python
       self._active_objective_fid = 1
       self._active_ping = None
       self._ping_timer = 0
       ```
     - In `step()`, BEFORE the `obs = vectorize_snapshot(...)` call (after the `_check_debuff_condition` block):
       ```python
       ping_reward_delta = 0.0
       if self.curriculum_stage == 4:
           if self._active_ping is not None:
               self._ping_timer += 1
               brain_c = self._get_density_centroid(snapshot, self.brain_faction)
               if brain_c is not None:
                   dist = ((brain_c[0] - self._active_ping[0])**2 + (brain_c[1] - self._active_ping[1])**2)**0.5
                   if dist < 60.0:
                       ping_reward_delta += 1.0
                       self._active_ping = None
               if self._active_ping is not None and self._ping_timer >= self._ping_lifespan:
                   ping_reward_delta -= 1.0
                   self._active_ping = None
                   
           count = self._get_faction_count(snapshot, self._active_objective_fid)
           if count <= 0 and self._active_objective_fid == 1:
               self._active_objective_fid = 2
               self._active_ping = None
               
           if self._active_ping is None:
               c = self._get_density_centroid(snapshot, self._active_objective_fid)
               if c is not None:
                   px = np.clip(c[0] + self.np_random.uniform(-80, 80), 0, self.world_width)
                   py = np.clip(c[1] + self.np_random.uniform(-80, 80), 0, self.world_height)
                   self._active_ping = (px, py)
                   self._ping_timer = 0
       ```
     - Modify the `vectorize_snapshot` call to include:
       `active_objective_ping=self._active_ping if self.curriculum_stage == 4 else None,`
       `ping_intensity=max(0.0, 1.0 - (self._ping_timer / self._ping_lifespan)) if self.curriculum_stage == 4 else 1.0,`
     - After `reward = self._compute_reward(...)`, append:
       `reward += ping_reward_delta`
Verification_Strategy:
  Test_Type: "manual_steps"
  Test_Stack: "none"
  Acceptance_Criteria:
    - "Stage 4 swarm_env runs step without errors and correctly applies ping rewards/penalties"
  Suggested_Test_Commands:
    - "cd macro-brain && python -m pytest tests/"
Live_System_Impact: "destructive"
---
