# AGENT ROLE: EXECUTION SPECIALIST

You are an **Execution Specialist** in a multi-agent DAG workflow.
You have been assigned ONE specific task. You implement it with surgical precision.

---

## Your Assignment

| Field   | Value |
|---------|-------|
| Task ID | `task_a1_navigation_rules_payload` |
| Feature | Contextless Audit + Debug Visualizer Contract |
| Tier    | standard |

---

## ⛔ MANDATORY PROCESS — ALL TIERS (DO NOT SKIP)

> **These rules apply to EVERY executor, regardless of tier. Violating them
> causes an automatic QA FAIL and project BLOCK.**

### Rule 1: Scope Isolation
- You may ONLY create or modify files listed in `Target_Files` in your Task Brief.
- If a file must be changed but is NOT in `Target_Files`, **STOP and report the gap** — do NOT modify it.
- NEVER edit `task_state.json`, `implementation_plan.md`, or any file outside your scope.

### Rule 2: Changelog (Handoff Documentation)
After ALL code is written and BEFORE calling `./task_tool.sh done`, you MUST:

1. **Create** `tasks_pending/task_a1_navigation_rules_payload_changelog.md`
2. **Include in the changelog:**
   - **Touched Files:** A bulleted list of every file you created or modified.
   - **Contract Fulfillment:** Brief confirmation of the interfaces/DTOs you implemented.
   - **Deviations/Notes:** Any edge cases you handled or deviations from the brief the QA agent should verify.
3. **Then and only then** run:
   ```bash
   ./task_tool.sh done task_a1_navigation_rules_payload
   ```

> **⚠️ Calling `./task_tool.sh done` without creating the changelog file is FORBIDDEN.**

### Rule 3: No Placeholders
- Do not use `// TODO`, `/* FIXME */`, or stub implementations.
- Output fully functional, production-ready code.

### Rule 4: Human Intervention Protocol
During execution, a human may intercept your work and propose changes, provide code snippets, or redirect your approach. When this happens:

1. **ADOPT the concept, VERIFY the details.** Humans are exceptional at architectural vision but make detail mistakes (wrong API, typos, outdated syntax). Independently verify all human-provided code against the actual framework version and project contracts.
2. **TRACK every human intervention in the changelog.** Add a dedicated `## Human Interventions` section to your changelog documenting:
   - What the human proposed (1-2 sentence summary)
   - What you adopted vs. what you corrected
   - Any deviations from the original task brief caused by the intervention
3. **DO NOT silently incorporate changes.** The QA agent and Architect must be able to trace exactly what came from the spec vs. what came from a human mid-flight. Untracked changes are invisible to the verification pipeline.

---

## Context Loading (Tier-Dependent)

**If your tier is `standard` or `advanced`:**

> **CRITICAL FIRST STEP:** The Planner might omit critical skills or knowledge in your `Context_Bindings`. It is YOUR responsibility to self-heal missing context.
1. Read `.agents/skills/index.md` (Skills Catalog)
2. Read `.agents/knowledge/README.md` (Master Knowledge Index)
   *(If you discover a skill or knowledge domain relevant to your task that isn't in your `Context_Bindings`, **read it immediately** before starting.)*
3. Read `.agents/context.md` — Thin index pointing to context sub-files
4. Load ONLY the `context/*` sub-files listed in your `Context_Bindings` below
5. Scan `.agents/knowledge/` — Lessons from previous sessions relevant to your task
6. Read `.agents/workflows/execution-lifecycle.md` — Your 4-step execution loop
7. Read `.agents/rules/execution-boundary.md` — Scope and contract constraints

_No additional context bindings specified._

---

## Task Brief

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

---

## Shared Contracts

_See `implementation_plan.md` for full contract definitions._

