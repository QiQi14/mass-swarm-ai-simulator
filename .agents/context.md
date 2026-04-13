# Project Context

> **This is an index file.** It contains only the minimal overview.
> Detailed context lives in `.agents/context/` sub-files.
> Task briefs reference specific sub-files via `Context_Bindings`.

> [!CAUTION]
> **WORKFLOW PRIORITY RULE:** If you were invoked via a slash command (e.g., `/strategist`, `/planner`, `/qa`),
> you MUST read and follow that workflow file FIRST, BEFORE reading any context files or taking action.
> Do NOT skip the workflow because the task "seems simple" or "investigatory."
> The workflow defines your role, process, and output format — it is NOT optional.

## Project Name
Decoupled Headless Mass-Swarm AI Simulation

## Current Phase
**Phase 3.5: ACTIVE** (2026-04-10). Tactical curriculum training in progress. 9-stage progressive curriculum, 8-action MultiDiscrete space, MaskablePPO. Currently training Stage 1 (Target Selection).

## Tech Stack
Tri-language system: Rust/Bevy ECS (Micro-Core) • Python/SB3 (Macro-Brain) • HTML5 Canvas/JS (Debug Visualizer), bridged via ZeroMQ and WebSockets.

## Architecture
Tri-Node Decoupled System — three independent OS processes (Rust, Python, Browser) communicating over IPC. No shared memory. Each node is replaceable independently.

## Quick Reference

| Context Folder | When to Load |
|-------------|-------------|
| `context/project` | **Always for Planner.** Contains the feature ledger, conventions, and tech stack information. |
| `context/engine` | **Any task touching combat, buffs, terrain, movement, or simulation logic.** Covers Rust-side systems that Python interacts with, plus IPC protocols. |
| `context/training` | **Any task involving training stages, spawns, rewards, bot behavior, or curriculum design.** |


## Agent Roles & Workflow Chain

```
User question → /strategist (research + design) → strategy_brief.md
                → /planner (implementation tasks) → implementation_plan.md → tasks_pending/
                → /execution (code)               → changelogs
                → /qa (verify)                     → certification reports
```

| Role | Slash Command | Input | Output | When to Use |
|------|--------------|-------|--------|-------------|
| **Strategist** | `/strategist` | Training logs, engine code | `strategy_brief.md` | Diagnosis, curriculum design, combat math, "why isn't this working?" |
| **Planner** | `/planner` | Strategy brief or feature request | `implementation_plan.md` + `tasks_pending/` | Convert strategy into implementation tasks |
| **Executor** | via dispatch | Task brief | Code changes + changelog | Write code |
| **QA** | `/qa` | Task changelogs | Certification reports | Verify implementation |

## How It Works

1. **Strategist** analyzes problems, does combat math, traces engine code, proposes designs
2. **Planner** converts approved strategies into DAG task files with file ownership
3. **Executor** loads ONLY the context slices listed in their task `Context_Bindings`
4. New context sub-files can be added anytime — just add a row to the table below

```
Context_Bindings:
  - context/engine           # if task touches combat, buffs, terrain, movement, or inter-node architecture
  - context/training         # if task touches stages, spawns, rewards, bots
  - context/project          # if task touches project tracking, code style, or general infrastructure
  - skills/rust-code-standards  # if task involves Rust code
```

## Key References (Supplementary)

> These files provide additional context AFTER you have followed your workflow and loaded required context files.
> Do NOT jump directly to these files to shortcut a workflow.

- **Phase Roadmap:** `ROADMAP.md` (root) — 5-phase plan, Phases 1-3 complete
- **Training Status:** `TRAINING_STATUS.md` — live training run tracker (summary only — for mechanics see `context/engine/` and `context/training/`)
- **Original TDD:** `CASE_STUDY.md` — full technical design document
- **Human Docs:** `docs/` — developer-facing documentation (NOT for agents)
- **Study Notes:** `docs/study/` — 12 engineering case studies (bugs, design decisions, research)
- **Archived Tasks:** `.agents/history/` — completed implementation cycles

## Test Health
| Suite | Count | Command |
|-------|-------|---------|
| Rust | 181 | `cd micro-core && cargo test` |
| Python | 51+ | `cd macro-brain && .venv/bin/python -m pytest tests/ -v` |
| Smoke | 300 ticks | `cd micro-core && cargo run -- --smoke-test` |
