# Project Context

> **This is an index file.** It contains only the minimal overview.
> Detailed context lives in `.agents/context/` sub-files.
> Task briefs reference specific sub-files via `Context_Bindings`.

## Project Name
Decoupled Headless Mass-Swarm AI Simulation

## Tech Stack
Tri-language system: Rust/Bevy ECS (Micro-Core) • Python/PyTorch (Macro-Brain) • HTML5 Canvas/JS (Debug Visualizer), bridged via ZeroMQ and WebSockets.

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
- **Phase Roadmap:** `implementation_plan.md` (root) — 5-phase plan approved by user
- **Original TDD:** `CASE_STUDY.md` — full technical design document
- **Human Docs:** `docs/` — developer-facing documentation (NOT for agents)
