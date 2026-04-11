# Task 10: Tactical Curriculum Game Profile

```yaml
Task_ID: task_10_game_profile
Execution_Phase: 5
Model_Tier: basic
Dependencies:
  - task_08_training_callbacks
  - task_09_feature_extractor_train
Target_Files:
  - macro-brain/profiles/tactical_curriculum.json
  - macro-brain/profiles/stage1_tactical.json  # DELETE or overwrite
  - macro-brain/profiles/default_swarm_combat.json  # DELETE or overwrite
Context_Bindings: []
```

## Objective

Create the master GameProfile JSON for the 8-stage tactical curriculum. Replace all old profiles.

## Strict Instructions

### 1. Delete old profiles

Overwrite `stage1_tactical.json` and `default_swarm_combat.json` with a deprecation notice or delete them.

### 2. Create `macro-brain/profiles/tactical_curriculum.json`

This is the complete profile. Every field must be present. All values come from the approved implementation plan v3.

```json
{
  "meta": {
    "name": "Tactical Decision-Making Curriculum",
    "version": "3.0.0",
    "description": "8-stage curriculum: target selection → scouting → walls → pheromone → flanking → lure → combined → randomized. MultiDiscrete([8, 2500]) action space with CNN+MLP feature extractor."
  },
  "world": {
    "width": 1000.0,
    "height": 1000.0,
    "grid_width": 50,
    "grid_height": 50,
    "cell_size": 20.0
  },
  "factions": [
    {
      "id": 0,
      "name": "Brain",
      "role": "brain",
      "stats": { "hp": 100.0 },
      "default_count": 50
    },
    {
      "id": 1,
      "name": "Trap",
      "role": "bot",
      "stats": { "hp": 100.0 },
      "default_count": 50
    },
    {
      "id": 2,
      "name": "Target",
      "role": "bot",
      "stats": { "hp": 100.0 },
      "default_count": 20
    }
  ],
  "combat": {
    "rules": [
      {
        "source_faction": 0, "target_faction": 1,
        "range": 25.0,
        "effects": [{ "stat_index": 0, "delta_per_second": -25.0 }]
      },
      {
        "source_faction": 1, "target_faction": 0,
        "range": 25.0,
        "effects": [{ "stat_index": 0, "delta_per_second": -25.0 }]
      },
      {
        "source_faction": 0, "target_faction": 2,
        "range": 25.0,
        "effects": [{ "stat_index": 0, "delta_per_second": -25.0 }]
      },
      {
        "source_faction": 2, "target_faction": 0,
        "range": 25.0,
        "effects": [{ "stat_index": 0, "delta_per_second": -25.0 }]
      }
    ]
  },
  "movement": {
    "max_speed": 60.0,
    "steering_factor": 5.0,
    "separation_radius": 6.0,
    "separation_weight": 1.5,
    "flow_weight": 1.0
  },
  "terrain_thresholds": {
    "impassable_threshold": 65535,
    "destructible_min": 60001
  },
  "removal_rules": [
    { "stat_index": 0, "threshold": 0.0, "condition": "LessOrEqual" }
  ],
  "abilities": {
    "buff_cooldown_ticks": 180,
    "movement_speed_stat": 1,
    "combat_damage_stat": 2,
    "activate_buff": {
      "modifiers": [
        { "stat_index": 0, "modifier_type": "Multiplier", "value": 0.25 },
        { "stat_index": 2, "modifier_type": "Multiplier", "value": 0.25 }
      ],
      "duration_ticks": 9999
    }
  },
  "actions": [
    { "index": 0, "name": "Hold", "unlock_stage": 1 },
    { "index": 1, "name": "AttackCoord", "unlock_stage": 1 },
    { "index": 2, "name": "DropPheromone", "unlock_stage": 4 },
    { "index": 3, "name": "DropRepellent", "unlock_stage": 4 },
    { "index": 4, "name": "SplitToCoord", "unlock_stage": 5 },
    { "index": 5, "name": "MergeBack", "unlock_stage": 5 },
    { "index": 6, "name": "Retreat", "unlock_stage": 6 },
    { "index": 7, "name": "Lure", "unlock_stage": 6 }
  ],
  "training": {
    "max_density": 50.0,
    "max_steps": 500,
    "ai_eval_interval_ticks": 30,
    "observation_channels": 9,
    "rewards": {
      "time_penalty_per_step": -0.01,
      "kill_reward": 0.05,
      "death_penalty": -0.03,
      "win_terminal": 10.0,
      "loss_terminal": -10.0,
      "survival_bonus_multiplier": 5.0,
      "approach_scale": 0.02,
      "exploration_reward": 0.005,
      "exploration_decay_threshold": 0.8,
      "threat_priority_bonus": 2.0,
      "flanking_bonus_scale": 0.1,
      "lure_success_bonus": 3.0,
      "debuff_bonus": 2.0
    },
    "curriculum": [
      {
        "stage": 1,
        "description": "Target Selection: read density, aim AttackCoord",
        "graduation": { "win_rate": 0.80, "min_episodes": 50 }
      },
      {
        "stage": 2,
        "description": "Scouting: navigate fog, find enemies with LKP",
        "graduation": { "win_rate": 0.80, "min_episodes": 50 }
      },
      {
        "stage": 3,
        "description": "Wall Navigation: find gap, route through",
        "graduation": { "win_rate": 0.80, "min_episodes": 50 }
      },
      {
        "stage": 4,
        "description": "Pheromone Control: shape flow fields",
        "graduation": { "win_rate": 0.80, "min_episodes": 50 }
      },
      {
        "stage": 5,
        "description": "Flanking: split and pincer from two angles",
        "graduation": { "win_rate": 0.80, "min_episodes": 50, "avg_flanking_score_min": 0.3 }
      },
      {
        "stage": 6,
        "description": "Lure Tactics: bait patrol, strike target",
        "graduation": { "win_rate": 0.80, "min_episodes": 50 }
      },
      {
        "stage": 7,
        "description": "Protected Target: fog + lure + flank vs guarded HVT",
        "graduation": { "win_rate": 0.75, "min_episodes": 100 }
      },
      {
        "stage": 8,
        "description": "Full Tactical: random scenarios, any tactic",
        "graduation": { "win_rate": 0.80, "min_episodes": 500 }
      }
    ]
  },
  "bot_stage_behaviors": [
    { "stage": 1, "faction_id": 1, "strategy": { "type": "HoldPosition" }, "eval_interval_ticks": 60 },
    { "stage": 1, "faction_id": 2, "strategy": { "type": "HoldPosition" }, "eval_interval_ticks": 60 },
    { "stage": 2, "faction_id": 2, "strategy": { "type": "HoldPosition" }, "eval_interval_ticks": 60 },
    { "stage": 3, "faction_id": 2, "strategy": { "type": "HoldPosition" }, "eval_interval_ticks": 60 },
    { "stage": 4, "faction_id": 2, "strategy": { "type": "HoldPosition" }, "eval_interval_ticks": 60 },
    { "stage": 5, "faction_id": 1, "strategy": { "type": "HoldPosition" }, "eval_interval_ticks": 60 },
    { "stage": 6, "faction_id": 1, "strategy": { "type": "Charge", "target_faction": 0 }, "eval_interval_ticks": 60 },
    { "stage": 6, "faction_id": 2, "strategy": { "type": "HoldPosition" }, "eval_interval_ticks": 60 },
    {
      "stage": 7, "faction_id": 1,
      "strategy": {
        "type": "Patrol",
        "waypoints": [
          { "x": 700.0, "y": 400.0 },
          { "x": 900.0, "y": 400.0 },
          { "x": 900.0, "y": 600.0 },
          { "x": 700.0, "y": 600.0 }
        ],
        "waypoint_threshold": 50.0
      },
      "eval_interval_ticks": 30
    },
    { "stage": 7, "faction_id": 2, "strategy": { "type": "HoldPosition" }, "eval_interval_ticks": 60 }
  ]
}
```

> **IMPORTANT:** The executor must verify all faction IDs, stage numbers, and action indices match the contracts from T01 (spaces.py), T07 (curriculum.py), and T08 (callbacks.py). Any mismatch will cause silent training failures.

### 3. Verify profile loads without errors

```bash
cd macro-brain && python -c "from src.config.game_profile import load_profile; p = load_profile('profiles/tactical_curriculum.json'); print(f'Loaded: {p.meta.name} v{p.meta.version}')"
```

## Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: unit
  Test_Stack: pytest (macro-brain)
  Acceptance_Criteria:
    - "Profile loads without errors"
    - "Profile has 8 actions"
    - "Profile has 8 curriculum stages"
    - "Profile has 3 factions (Brain/Trap/Target)"
    - "actions[7].name == 'Lure'"
    - "rewards.approach_scale == 0.02"
    - "rewards.lure_success_bonus == 3.0"
    - "curriculum[6].graduation.win_rate == 0.75 (Stage 7)"
    - "Old profiles deleted or deprecated"
  Suggested_Test_Commands:
    - "cd macro-brain && python -c \"from src.config.game_profile import load_profile; p = load_profile('profiles/tactical_curriculum.json'); print(f'{p.meta.name}: {p.num_actions} actions, {len(p.training.curriculum)} stages')\""
```
