---
description: How the QA agent captures and persists learned experiences
---

# WORKFLOW: KNOWLEDGE CAPTURE (PERSISTENT LEARNING)

When the QA agent finds mistakes, bad patterns, or non-obvious gotchas during verification, it MUST document them in `.agents/knowledge/` so future agents (especially low-tier executors) don't repeat the same errors.

## Why QA Owns This

- **Executors** (especially basic-tier ~14B) lack the context window to write quality knowledge entries
- **QA agents** are high-tier models that SEE the actual failures — wrong APIs, deprecated functions, malformed code
- QA runs AFTER execution, when the mistake is concrete and documented in the changelog

## When to Capture

You MUST create a knowledge file when:
1. The executor used a **deprecated API/function** and you had to flag or fix it
2. The executor produced **malformed code** (wrong imports, bad syntax patterns)
3. The executor used **outdated CLI commands** or tooling
4. You found a **recurring contract violation** across multiple tasks
5. You discovered a **platform-specific gotcha** (e.g., Android Keystore edge case)
6. The user corrected your verification approach

## Where to Write

Create a Markdown file in the appropriate **subdirectory** under `.agents/knowledge/`:

```
.agents/knowledge/
├── README.md               ← Master index (agent lookup table)
├── bevy/                   ← Bevy ECS engine gotchas and patterns
├── rust/                   ← Rust language conventions
├── tooling/                ← IDE, build tools, dev environment
└── workflow/               ← Multi-agent DAG process rules
```

**File naming:** `[type]_[short_name].md`  
**Types:** `architecture`, `convention`, `gotcha`, `deprecation`, `tooling`

**Examples:**
- `.agents/knowledge/bevy/gotcha_bevy_018_test_query.md`
- `.agents/knowledge/rust/convention_rust_file_splitting.md`
- `.agents/knowledge/tooling/tooling_stale_rust_analyzer_cache.md`
- `.agents/knowledge/workflow/gotcha_basic_tier_context_ignorance.md`

**After creating a knowledge file**, you MUST update `README.md` to add the new entry to the appropriate domain table. The README is the lookup index — if a file isn't listed there, agents won't find it.

If a new domain subdirectory is needed (e.g., `python/`, `frontend/`), create the folder and add a new section to README.md.

## File Format

```markdown
# Lesson: [Concise, descriptive title]

**Category:** [architecture | ui | data | tooling | convention | gotcha | deprecation]
**Discovered:** [Date or task ID where this was learned]
**Severity:** [low | medium | high — how likely is this to break things]

## Context
[What was being done when this was discovered]

## Problem
[What went wrong — include the executor's mistake if applicable]

## Correct Approach
[The right way to do it]

## Example
- ❌ What the executor did: [The incorrect code/command]
- ✅ What it should be: [The correct code/command]
```

## When in the QA Lifecycle

Knowledge capture happens in **Step 5** of the QA workflow (`qa-lifecycle.md`), after verification is complete — whether the task passed or failed:

- **PASS with issues found:** Still capture the lesson if the executor did something fragile
- **FAIL:** Always capture the root cause so the re-attempt doesn't repeat it

## How Future Agents Use It

1. All agent templates instruct agents to scan `.agents/knowledge/` before starting
2. Planners can reference knowledge entries in `Context_Bindings` for task briefs
3. Knowledge entries accumulate over time, making the framework smarter per-project
