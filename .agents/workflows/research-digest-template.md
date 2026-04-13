---
description: Structured template for the Research Digest artifact
---

# Research Digest Template

> **Producer:** Strategist agent
> **Consumers:** Planner agent (primary), Advanced-tier Executor agents (secondary)
> **Location:** Project root as `research_digest.md`

The Research Digest is an **optional** artifact the Strategist produces when its analysis
involves understanding existing codebase structure. It captures the *raw facts* about the
codebase — not analysis or recommendations (those belong in `strategy_brief.md`).

## When to Produce a Digest

| Strategist Session Type | Produce Digest? |
|------------------------|----------------|
| Training diagnosis involving Rust engine code | ✅ Yes |
| Curriculum design touching existing codebase | ✅ Yes |
| System investigation / code tracing | ✅ Yes |
| Pure research (exploring ideas, evaluating libraries) | ❌ No |
| Training/experiment status tracking | ❌ No |
| Design exploration with no existing code dependency | ❌ No |

**Rule of thumb:** If the Planner will need to understand *existing code* to write task briefs,
produce a digest. If the strategy brief is self-contained (no codebase dependency), skip it.

## Template

```markdown
# Research Digest: [Feature/Investigation Name]

## Relevant File Map

| File | Purpose | Key Exports / Types | Relevant Lines |
|------|---------|-------------------|----------------|
| `path/to/file.rs` | [What this file does] | `TypeA`, `fn method_b()` | L45-120 |
| `path/to/other.py` | [What this file does] | `ClassX`, `def function_y()` | L10-85 |

> List ONLY files relevant to the planned work. Not the entire codebase.

## Existing Contracts & Types

Extract the EXACT type/struct/interface definitions that the Planner and Executor
will need. Include file:line references.

```rust
// From: micro-core/src/types.rs:L45-62
pub struct EcpResult {
    pub value: f32,
    pub source_id: EntityId,
    pub timestamp: f64,
}
`` `

> Copy exact definitions. Do not summarize or paraphrase type structures.

## Integration Points

Document how the relevant subsystems connect:

```
[Producer] micro-core/src/systems/combat.rs::calculate_ecp()
    → writes to: SharedState.ecp_map
    → called by: system_scheduler (every 3 ticks)

[Consumer] micro-core/src/systems/render.rs::render_overlay()
    → reads from: SharedState.ecp_map
    → called by: render_pipeline (every frame)
`` `

> Show actual function names and data flow, not descriptions.

## Code Patterns in Use

Document patterns the executor should follow to maintain consistency:

- **Error handling:** [How does this codebase handle errors? Result types? Panics? Logging?]
- **Config loading:** [How are configs read? Runtime? Compile-time? Hot-reload?]
- **State management:** [ECS components? Global resources? Shared state?]
- **Testing patterns:** [What test framework? How are fixtures set up?]

> Only include patterns relevant to the planned work.

## Gotchas & Constraints Discovered

Things the Strategist found during investigation that would cause executor failures if ignored:

- [e.g., "The `transform` field is in WORLD space, not local — must convert before applying offsets"]
- [e.g., "Config changes require restart — hot-reload is not wired for this subsystem"]
- [e.g., "The `update()` method is called twice per frame due to the split schedule — mutations must be idempotent"]

> These are the highest-value items in the digest. Be specific and cite evidence.
```

## Quality Rules

1. **Facts, not analysis.** The digest contains extracted code, measured values, and traced call chains. Analysis and recommendations belong in `strategy_brief.md`.
2. **Exact references.** Every entry must include file paths and line numbers. "The rendering module" is not acceptable — `micro-core/src/systems/render.rs:L200-280` is.
3. **Verified, not assumed.** Every claim in the digest must come from reading actual source code. Do not infer behavior from variable names or documentation.
4. **Minimal, not exhaustive.** Include only what the Planner/Executor will need for the planned work. A 200-line digest is fine; a 2000-line digest defeats the purpose.
