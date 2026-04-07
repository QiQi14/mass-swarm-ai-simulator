# Task B1: WS Commands for Rule Configuration

**Task_ID:** task_b1_ws_rule_commands
**Execution_Phase:** 2
**Model_Tier:** standard

## Target_Files
- `micro-core/src/systems/ws_command.rs`

## Dependencies
- None (B2 builds the JS panel, but B1 can be implemented independently)

## Context_Bindings
- context/architecture
- context/conventions
- context/ipc-protocol
- skills/rust-code-standards

## Strict_Instructions

### Overview

Add 3 new WebSocket command handlers to `ws_command_system` in `ws_command.rs`. These allow the debug visualizer to configure simulation rules without the Python macro-brain, enabling standalone algorithm testing.

### Step 1: Add `set_navigation` command handler

When cmd is `"set_navigation"`, parse the params and replace the `NavigationRuleSet` resource:

```rust
"set_navigation" => {
    // Expects: { "rules": [{ "follower_faction": 0, "target": { "type": "Faction", "faction_id": 1 } }] }
    if let Some(rules_array) = cmd.params.get("rules").and_then(|v| v.as_array()) {
        nav_rules.rules.clear();
        for rule_json in rules_array {
            if let (Some(follower), Some(target_json)) = (
                rule_json.get("follower_faction").and_then(|v| v.as_u64()),
                rule_json.get("target"),
            ) {
                if let Ok(target) = serde_json::from_value::<crate::bridges::zmq_protocol::NavigationTarget>(target_json.clone()) {
                    nav_rules.rules.push(crate::rules::NavigationRule {
                        follower_faction: follower as u32,
                        target,
                    });
                }
            }
        }
        println!("[WS Command] Set {} navigation rules", nav_rules.rules.len());
    }
}
```

**System parameters:** The `ws_command_system` already takes `ResMut<NavigationRuleSet>` — verify this. If not, add it.

### Step 2: Add `set_interaction` command handler

When cmd is `"set_interaction"`, parse and replace the `InteractionRuleSet` resource:

```rust
"set_interaction" => {
    // Expects: { "rules": [{ "source_faction": 0, "target_faction": 1, "range": 15.0, "effects": [{ "stat_index": 0, "delta_per_second": -10.0 }] }] }
    if let Some(rules_array) = cmd.params.get("rules").and_then(|v| v.as_array()) {
        interaction_rules.rules.clear();
        for rule_json in rules_array {
            if let (Some(source), Some(target), Some(range)) = (
                rule_json.get("source_faction").and_then(|v| v.as_u64()),
                rule_json.get("target_faction").and_then(|v| v.as_u64()),
                rule_json.get("range").and_then(|v| v.as_f64()),
            ) {
                let effects = rule_json.get("effects")
                    .and_then(|v| v.as_array())
                    .map(|fx| {
                        fx.iter().filter_map(|e| {
                            Some(crate::rules::StatEffect {
                                stat_index: e.get("stat_index")?.as_u64()? as usize,
                                delta_per_second: e.get("delta_per_second")?.as_f64()? as f32,
                            })
                        }).collect()
                    })
                    .unwrap_or_default();

                interaction_rules.rules.push(crate::rules::InteractionRule {
                    source_faction: source as u32,
                    target_faction: target as u32,
                    range: range as f32,
                    effects,
                });
            }
        }
        println!("[WS Command] Set {} interaction rules", interaction_rules.rules.len());
    }
}
```

**System parameters:** Add `mut interaction_rules: ResMut<InteractionRuleSet>` to the system.

### Step 3: Add `set_removal` command handler

When cmd is `"set_removal"`, parse and replace the `RemovalRuleSet` resource:

```rust
"set_removal" => {
    // Expects: { "rules": [{ "stat_index": 0, "threshold": 0.0, "condition": "LessThanEqual" }] }
    if let Some(rules_array) = cmd.params.get("rules").and_then(|v| v.as_array()) {
        removal_rules.rules.clear();
        for rule_json in rules_array {
            if let (Some(stat_idx), Some(threshold)) = (
                rule_json.get("stat_index").and_then(|v| v.as_u64()),
                rule_json.get("threshold").and_then(|v| v.as_f64()),
            ) {
                let condition = match rule_json.get("condition").and_then(|v| v.as_str()) {
                    Some("GreaterThanEqual") => crate::rules::RemovalCondition::GreaterOrEqual,
                    _ => crate::rules::RemovalCondition::LessOrEqual,
                };
                removal_rules.rules.push(crate::rules::RemovalRule {
                    stat_index: stat_idx as usize,
                    threshold: threshold as f32,
                    condition,
                });
            }
        }
        println!("[WS Command] Set {} removal rules", removal_rules.rules.len());
    }
}
```

**System parameters:** Add `mut removal_rules: ResMut<RemovalRuleSet>` to the system.

### Step 4: Verify system parameters

Ensure `ws_command_system` has these ResMut parameters:
- `ResMut<NavigationRuleSet>` — may already exist (check for `set_faction_mode`)
- `ResMut<InteractionRuleSet>` — likely NEW
- `ResMut<RemovalRuleSet>` — likely NEW

Add the necessary `use crate::rules::*` imports.

### Step 5: Verify

```bash
cd micro-core && cargo test ws_command && cargo clippy
```

## Verification_Strategy
  Test_Type: unit
  Acceptance_Criteria:
    - "set_navigation WS command replaces NavigationRuleSet with parsed rules"
    - "set_interaction WS command replaces InteractionRuleSet with parsed rules"
    - "set_removal WS command replaces RemovalRuleSet with parsed rules"
    - "Each command prints a log message with rule count"
    - "cargo test passes with zero failures"
    - "cargo clippy passes with zero warnings"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test ws_command"
