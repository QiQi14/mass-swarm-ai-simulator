# Task A3: Python Sends Navigation Rules During Reset

**Task_ID:** task_a3_python_nav_rules
**Execution_Phase:** 3
**Model_Tier:** standard

## Target_Files
- `macro-brain/src/config/game_profile.py`
- `macro-brain/src/env/swarm_env.py`

## Dependencies
- **task_a1_navigation_rules_payload** — Rust must accept `navigation_rules` in `AiResponse::ResetEnvironment` first

## Context_Bindings
- context/architecture
- context/conventions
- context/ipc-protocol

## Strict_Instructions

### Step 1: Add `navigation_rules_payload()` to `GameProfile` in `game_profile.py`

Add this method to the `GameProfile` class, after the existing `removal_rules_payload()` method:

```python
def navigation_rules_payload(self) -> list[dict]:
    """Serialize navigation rules for ZMQ ResetEnvironment payload.
    
    Generates bidirectional navigation: brain faction chases bot factions
    and each bot faction chases the brain faction. Uses faction IDs from
    the profile — no hardcoded values.
    """
    rules = []
    brain = self.brain_faction
    for bot in self.bot_factions:
        # Brain faction navigates toward bot
        rules.append({
            "follower_faction": brain.id,
            "target": {"type": "Faction", "faction_id": bot.id}
        })
        # Bot faction navigates toward brain
        rules.append({
            "follower_faction": bot.id,
            "target": {"type": "Faction", "faction_id": brain.id}
        })
    return rules
```

### Step 2: Add `navigation_rules` to the reset payload in `swarm_env.py`

In `SwarmEnv.reset()`, find the `self._socket.send_string(json.dumps({...}))` call that sends the reset_environment payload (around line 149). Add `navigation_rules` to the JSON dict:

**BEFORE:**
```python
self._socket.send_string(json.dumps({
    "type": "reset_environment",
    "terrain": terrain,
    "spawns": spawns,
    "combat_rules": self.profile.combat_rules_payload(),
    "ability_config": self.profile.ability_config_payload(),
    "movement_config": self.profile.movement_config_payload(),
    "max_density": self.profile.training.max_density,
    "terrain_thresholds": self.profile.terrain_thresholds_payload(),
    "removal_rules": self.profile.removal_rules_payload(),
}))
```

**AFTER:**
```python
self._socket.send_string(json.dumps({
    "type": "reset_environment",
    "terrain": terrain,
    "spawns": spawns,
    "combat_rules": self.profile.combat_rules_payload(),
    "ability_config": self.profile.ability_config_payload(),
    "movement_config": self.profile.movement_config_payload(),
    "max_density": self.profile.training.max_density,
    "terrain_thresholds": self.profile.terrain_thresholds_payload(),
    "removal_rules": self.profile.removal_rules_payload(),
    "navigation_rules": self.profile.navigation_rules_payload(),
}))
```

### Step 3: Add unit test for `navigation_rules_payload()`

In `macro-brain/tests/`, find or create the appropriate test file. Add:

```python
def test_navigation_rules_payload():
    """Navigation rules should be generated from profile factions, not hardcoded."""
    profile = _make_test_profile()  # Use existing test profile helper
    rules = profile.navigation_rules_payload()
    
    # Should have bidirectional rules for each brain-bot pair
    assert len(rules) >= 2, "Should have at least 2 navigation rules"
    
    # Verify structure
    for rule in rules:
        assert "follower_faction" in rule
        assert "target" in rule
        assert "type" in rule["target"]
        assert rule["target"]["type"] in ("Faction", "Waypoint")
    
    # Verify no hardcoded faction IDs — values should come from profile
    brain_id = profile.brain_faction.id
    bot_ids = [f.id for f in profile.bot_factions]
    follower_ids = {r["follower_faction"] for r in rules}
    assert brain_id in follower_ids, "Brain faction should be a follower"
    for bot_id in bot_ids:
        assert bot_id in follower_ids, f"Bot faction {bot_id} should be a follower"
```

### Step 4: Verify

```bash
cd macro-brain && python -m pytest tests/ -v
```

## Verification_Strategy
  Test_Type: unit
  Acceptance_Criteria:
    - "GameProfile.navigation_rules_payload() returns a list of dicts with follower_faction and target"
    - "No hardcoded faction IDs — values come from the profile"
    - "SwarmEnv.reset() sends navigation_rules in the reset_environment payload"
    - "pytest passes with zero failures"
  Suggested_Test_Commands:
    - "cd macro-brain && python -m pytest tests/ -v -k navigation"
