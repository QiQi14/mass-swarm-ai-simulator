# Task A2: NavigationRuleSet Default to Empty

**Task_ID:** task_a2_nav_ruleset_default_empty
**Execution_Phase:** 1
**Model_Tier:** basic

## Target_Files
- `micro-core/src/rules/navigation.rs`

## Dependencies
- None

## Context_Bindings
- context/architecture
- context/conventions
- skills/rust-code-standards

## Strict_Instructions

### Step 1: Change `NavigationRuleSet::default()` to empty

In `micro-core/src/rules/navigation.rs`, replace the `Default` impl:

**BEFORE:**
```rust
impl Default for NavigationRuleSet {
    /// Bidirectional default: both factions navigate toward each other.
    /// Ensures combat by removing the "static defenders" problem.
    fn default() -> Self {
        Self {
            rules: vec![
                NavigationRule {
                    follower_faction: 0,
                    target: NavigationTarget::Faction { faction_id: 1 },
                },
                NavigationRule {
                    follower_faction: 1,
                    target: NavigationTarget::Faction { faction_id: 0 },
                },
            ],
        }
    }
}
```

**AFTER:**
```rust
impl Default for NavigationRuleSet {
    /// Empty ruleset — no navigation unless explicitly configured by game profile.
    /// Consistent with InteractionRuleSet and RemovalRuleSet defaults.
    fn default() -> Self {
        Self { rules: vec![] }
    }
}
```

### Step 2: Update the test

Replace `test_navigation_rule_set_default`:

**BEFORE:**
```rust
#[test]
fn test_navigation_rule_set_default() {
    let ruleset = NavigationRuleSet::default();
    assert_eq!(ruleset.rules.len(), 2);
    assert_eq!(ruleset.rules[0].follower_faction, 0);
    // ...
}
```

**AFTER:**
```rust
#[test]
fn test_navigation_rule_set_default_is_empty() {
    // Arrange & Act
    let ruleset = NavigationRuleSet::default();

    // Assert — consistent with InteractionRuleSet and RemovalRuleSet
    assert_eq!(ruleset.rules.len(), 0, "Default NavigationRuleSet should be empty");
}
```

### Step 3: Verify

```bash
cd micro-core && cargo test rules && cargo clippy
```

## Verification_Strategy
  Test_Type: unit
  Acceptance_Criteria:
    - "NavigationRuleSet::default().rules.len() == 0"
    - "cargo test passes with zero failures"
    - "cargo clippy passes with zero warnings"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test rules::navigation"
