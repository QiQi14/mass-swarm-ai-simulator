# Project Context

> **This is an index file.** It contains only the minimal overview.
> Detailed context lives in `.agents/context/` sub-files.
> Task briefs reference specific sub-files via `Context_Bindings`.

## Project Name
Decoupled Headless Mass-Swarm AI Simulation

## Current Phase
**Phase 3: COMPLETE** (2026-04-06). Multi-Master Arbitration + RL Training pipeline fully implemented. 180 Rust tests, 33 Python tests, 0 warnings.

## Tech Stack
Tri-language system: Rust/Bevy ECS (Micro-Core) • Python/SB3 (Macro-Brain) • HTML5 Canvas/JS (Debug Visualizer), bridged via ZeroMQ and WebSockets.

## Architecture
Tri-Node Decoupled System — three independent OS processes (Rust, Python, Browser) communicating over IPC. No shared memory. Each node is replaceable independently.

## Quick Reference

| Context File | When to Load |
|-------------|-------------|
| `context/features` | **Always for Planner.** Executor/QA load when touching existing features |
| `context/tech-stack` | Any task involving dependencies, build tools, or framework APIs |
| `context/architecture` | Any task involving folder structure, layer boundaries, or data flow |
| `context/conventions` | Any task involving naming, formatting, or code style |
| `context/infrastructure` | Tasks involving build, deploy, CI/CD, or environment setup |
| `context/ipc-protocol` | Any task involving bridges, message parsing, serialization, or WS/ZMQ code |

## How It Works

1. **Planner** assigns relevant context slices in each task's `Context_Bindings`
2. **Executor** loads ONLY the slices listed — not the entire context directory
3. New sub-files can be added anytime — just add a row to the table above

```
Context_Bindings:
  - context/tech-stack
  - context/conventions
  - context/ipc-protocol     # if task touches bridge code
  - skills/my-skill          # if a relevant skill exists
```

## Key References
- **Phase Roadmap:** `ROADMAP.md` (root) — 5-phase plan, Phases 1-3 complete
- **Training Status:** `TRAINING_STATUS.md` — live training run tracker
- **Original TDD:** `CASE_STUDY.md` — full technical design document
- **Human Docs:** `docs/` — developer-facing documentation (NOT for agents)
- **Study Notes:** `docs/study/` — 12 engineering case studies (bugs, design decisions, research)
- **Archived Tasks:** `.agents/history/` — completed implementation cycles

## Test Health
| Suite | Count | Command |
|-------|-------|---------|
| Rust | 181 | `cd micro-core && cargo test` |
| Python | 33 | `cd macro-brain && python -m pytest tests/ -v` |
| Smoke | 300 ticks | `cd micro-core && cargo run -- --smoke-test` |
