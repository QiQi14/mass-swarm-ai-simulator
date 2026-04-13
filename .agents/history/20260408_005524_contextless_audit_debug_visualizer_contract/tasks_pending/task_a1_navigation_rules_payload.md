# Task A1: Add navigation_rules to ResetRequest Payload

**Task_ID:** task_a1_navigation_rules_payload
**Execution_Phase:** 2
**Model_Tier:** standard

## Target_Files
- `micro-core/src/bridges/zmq_protocol/payloads.rs`
- `micro-core/src/bridges/zmq_protocol/directives.rs`
- `micro-core/src/bridges/zmq_bridge/reset.rs`

## Dependencies
- **task_a2_nav_ruleset_default_empty** — `NavigationRuleSet::default()` must be empty first

## Context_Bindings
- context/architecture
- context/conventions
- context/ipc-protocol
- skills/rust-code-standards

## Strict_Instructions

### Step 1: Add `NavigationRulePayload` to `payloads.rs`

Add this new struct in `payloads.rs` after `RemovalRulePayload`:

```rust
/// Navigation rule from game profile (replaces NavigationRuleSet::default).
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct NavigationRulePayload {
    pub follower_faction: u32,
    pub target: super::NavigationTarget,
}
```

Note: `NavigationTarget` is defined in `directives.rs` and re-exported from the `zmq_protocol` module. Use `super::NavigationTarget` since both files are in the same module.

### Step 2: Add `navigation_rules` field to `AiResponse::ResetEnvironment` in `directives.rs`

Add a new optional field to the `ResetEnvironment` variant:

```rust
#[serde(rename = "reset_environment")]
ResetEnvironment {
    terrain: Option<TerrainPayload>,
    spawns: Vec<SpawnConfig>,
    #[serde(default)]
    combat_rules: Option<Vec<CombatRulePayload>>,
    #[serde(default)]
    ability_config: Option<AbilityConfigPayload>,
    #[serde(default)]
    movement_config: Option<MovementConfigPayload>,
    #[serde(default)]
    max_density: Option<f32>,
    #[serde(default)]
    terrain_thresholds: Option<TerrainThresholdsPayload>,
    #[serde(default)]
    removal_rules: Option<Vec<RemovalRulePayload>>,
    #[serde(default)]                                    // ← NEW
    navigation_rules: Option<Vec<NavigationRulePayload>>, // ← NEW
},
```

### Step 3: Add `navigation_rules` to `ResetRequest` in `reset.rs`

Add the field to the `ResetRequest` struct:

```rust
pub struct ResetRequest {
    pub terrain: Option<TerrainPayload>,
    pub spawns: Vec<SpawnConfig>,
    pub combat_rules: Option<Vec<crate::bridges::zmq_protocol::CombatRulePayload>>,
    pub ability_config: Option<crate::bridges::zmq_protocol::AbilityConfigPayload>,
    pub movement_config: Option<crate::bridges::zmq_protocol::MovementConfigPayload>,
    pub max_density: Option<f32>,
    pub terrain_thresholds: Option<crate::bridges::zmq_protocol::TerrainThresholdsPayload>,
    pub removal_rules: Option<Vec<crate::bridges::zmq_protocol::RemovalRulePayload>>,
    pub navigation_rules: Option<Vec<crate::bridges::zmq_protocol::NavigationRulePayload>>, // ← NEW
}
```

### Step 4: Replace hardcoded nav rules in `reset_environment_system`

In `reset.rs`, find the hardcoded navigation rules (around lines 111-120):

**BEFORE:**
```rust
rules.nav.rules.clear();
// Re-seed bidirectional chase so both factions approach each other
rules.nav.rules.push(crate::rules::NavigationRule {
    follower_faction: 0,
    target: crate::bridges::zmq_protocol::NavigationTarget::Faction { faction_id: 1 },
});
rules.nav.rules.push(crate::rules::NavigationRule {
    follower_faction: 1,
    target: crate::bridges::zmq_protocol::NavigationTarget::Faction { faction_id: 0 },
});
```

**AFTER:**
```rust
rules.nav.rules.clear();
// Apply navigation rules from game profile (if provided)
if let Some(nav_rules) = &reset.navigation_rules {
    for r in nav_rules {
        rules.nav.rules.push(crate::rules::NavigationRule {
            follower_faction: r.follower_faction,
            target: r.target.clone(),
        });
    }
    println!("[Reset] Applied {} navigation rules from game profile", rules.nav.rules.len());
} else {
    println!("[Reset] WARNING: No navigation_rules provided. Factions will not navigate. \
              The adapter (game profile) should provide explicit navigation rules.");
}
```

### Step 5: Update `ai_poll_system` to pass the new field

In `micro-core/src/bridges/zmq_bridge/systems.rs`, find where `ResetRequest` is constructed from `AiResponse::ResetEnvironment`. Add the new field:

**Important:** The `ResetRequest` is constructed in `ai_poll_system` when it receives and parses the AiResponse. Find the match arm for `AiResponse::ResetEnvironment` and add `navigation_rules` to the struct construction.

> **Note:** `systems.rs` is NOT in your Target_Files because it overlaps with Task B1. You may ONLY add the `navigation_rules` field passthrough — do not modify any other logic in `systems.rs`. If this creates a collision concern, add a `// TODO: task_a1 — navigation_rules field added` comment.

Actually, we need to check — the `systems.rs` field passthrough MUST be done here since it's where `ResetRequest` is constructed. Add `systems.rs` to your modified files list in the changelog but limit changes to ONLY the `navigation_rules` field passthrough.

### Step 6: Add a serialization test

Add this test in `directives_tests.rs` (or in `payloads.rs` tests):

```rust
#[test]
fn test_reset_environment_with_navigation_rules() {
    // Arrange
    let json = r#"{
        "type": "reset_environment",
        "terrain": null,
        "spawns": [],
        "navigation_rules": [
            {"follower_faction": 0, "target": {"type": "Faction", "faction_id": 1}},
            {"follower_faction": 1, "target": {"type": "Waypoint", "x": 500.0, "y": 500.0}}
        ]
    }"#;

    // Act
    let response: AiResponse = serde_json::from_str(json).unwrap();

    // Assert
    match response {
        AiResponse::ResetEnvironment { navigation_rules, .. } => {
            let rules = navigation_rules.unwrap();
            assert_eq!(rules.len(), 2, "Should have 2 navigation rules");
            assert_eq!(rules[0].follower_faction, 0);
            assert_eq!(rules[1].target, NavigationTarget::Waypoint { x: 500.0, y: 500.0 });
        }
        _ => panic!("Expected ResetEnvironment"),
    }
}
```

### Step 7: Verify

```bash
cd micro-core && cargo test && cargo test --doc && cargo clippy
```

## Verification_Strategy
  Test_Type: unit
  Acceptance_Criteria:
    - "NavigationRulePayload exists in payloads.rs with follower_faction and target fields"
    - "AiResponse::ResetEnvironment has optional navigation_rules field"
    - "ResetRequest has optional navigation_rules field"
    - "reset_environment_system uses navigation_rules from payload instead of hardcoded values"
    - "Warning printed when no navigation_rules provided"
    - "Serialization roundtrip test passes"
    - "cargo test passes with zero failures"
    - "cargo clippy passes with zero warnings"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test bridges"
    - "cd micro-core && cargo test zmq_protocol"
