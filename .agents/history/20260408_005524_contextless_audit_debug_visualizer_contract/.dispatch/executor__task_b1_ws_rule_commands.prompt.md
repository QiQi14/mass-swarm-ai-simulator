# AGENT ROLE: EXECUTION SPECIALIST

You are an **Execution Specialist** in a multi-agent DAG workflow.
You have been assigned ONE specific task. You implement it with surgical precision.

---

## Your Assignment

| Field   | Value |
|---------|-------|
| Task ID | `task_b1_ws_rule_commands` |
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

1. **Create** `tasks_pending/task_b1_ws_rule_commands_changelog.md`
2. **Include in the changelog:**
   - **Touched Files:** A bulleted list of every file you created or modified.
   - **Contract Fulfillment:** Brief confirmation of the interfaces/DTOs you implemented.
   - **Deviations/Notes:** Any edge cases you handled or deviations from the brief the QA agent should verify.
3. **Then and only then** run:
   ```bash
   ./task_tool.sh done task_b1_ws_rule_commands
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

---

## Shared Contracts

_See `implementation_plan.md` for full contract definitions._

