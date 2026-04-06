# Knowledge Directory

> Learned experiences from agent sessions. Organized by domain for quick agent lookup.
> When loading context, agents should scan only the folder(s) relevant to their task.

## Directory Structure

```
knowledge/
├── README.md           ← This index (start here)
├── bevy/               ← Bevy ECS engine gotchas and patterns
├── python/             ← Python language gotchas and patterns
├── rust/               ← Rust language conventions and patterns
├── tooling/            ← IDE, build tools, dev environment
└── workflow/           ← Multi-agent DAG process rules
```

---

## Quick Lookup by Agent Role

| Agent | Scan These Folders | When |
|-------|-------------------|------|
| **Executor** | `bevy/`, `rust/`, `python/` | Before writing Bevy/Rust/Python code |
| **QA** | `bevy/`, `python/`, `tooling/` | Before running tests or diagnosing failures |
| **Planner** | `workflow/`, `rust/`, `python/` | Before creating task briefs or DAG plans |

---

## `bevy/` — Bevy Engine Gotchas (10 files)

| File | Severity | Summary |
|------|----------|---------|
| `architecture_bevy_mpsc_receiver_sync.md` | high | `mpsc::Receiver` needs `Mutex` wrapper to satisfy Bevy `Resource` `Sync` requirement |
| `architecture_engine_override_ws_sync_gap.md` | low | `EntityState` WS protocol does not include `has_override` — visualizer marker won't activate until field is added |
| `convention_flowfield_fog_of_war.md` | medium | Flow field goals must be filtered by follower faction's visible cells for fog-of-war |
| `deprecation_bevy_18_features.md` | high | Bevy 0.18 removed `bevy_log` and `bevy_winit` — use `default-features = false` |
| `gotcha_bevy_018_test_query.md` | high | Bevy 0.18 removed `Query::get_single` — use `query.single()` instead |
| `gotcha_bevy_schedule_runner_macos.md` | high | `ScheduleRunnerPlugin` on macOS causes 40% TPS degradation — use custom runner |
| `gotcha_bevy_state_unit_tests.md` | high | Must add `StatesPlugin` and call `app.update()` twice for state transitions in tests |
| `gotcha_broadcast_lagged_kills_forwarder.md` | medium | Broadcast channel `Lagged` error kills the forwarder task — must handle gracefully |
| `gotcha_simstate_freezes_simulation.md` | medium | `SimState` gating can freeze simulation if systems incorrectly gated |
| `gotcha_tick_timeout_overlap.md` | medium | ZMQ timeout (5s) can overlap with smoke test exit (300 ticks = 5s) — adjust thresholds |

## `rust/` — Rust Conventions (1 file)

| File | Severity | Summary |
|------|----------|---------|
| `convention_rust_file_splitting.md` | medium | Split files >300 lines or with 3+ concerns; document rationale if choosing not to split |

## `tooling/` — IDE & Build Tools (3 files)

| File | Severity | Summary |
|------|----------|---------|
| `gotcha_heredoc_terminal_crash.md` | high | Never use heredocs in `run_command` — causes terminal zombie → session crash cascade. Use `write_to_file` instead. |
| `tooling_stale_rust_analyzer_cache.md` | low | Stale `target/` fingerprints cause phantom errors in rust-analyzer — fix with `cargo clean` |
| `tooling_testing_tmp_dir.md` | low | Use workspace-local temp dirs for test artifacts, not system `/tmp` |

## `workflow/` — Multi-Agent Process (5 files)

| File | Severity | Summary |
|------|----------|---------|
| `architecture_dispatch_template_vs_workflow.md` | high | Dispatch prompt is the ONLY input for executors — don't use `/executor` workflow trigger |
| `convention_strict_scope_and_changelog.md` | high | Executor must create changelog + stay within `Target_Files` scope — mandatory in dispatch template |
| `convention_split_large_plans.md` | high | Split `implementation_plan.md` into index + per-feature detail files when >400 lines to avoid executor token truncation |
| `gotcha_basic_tier_context_ignorance.md` | high | `basic` tier models skip `Context_Bindings` — inline critical rules in the task brief |
| `gotcha_never_manually_archive_tasks.md` | critical | **NEVER** manually `mv` task files — always use `./task_tool.sh complete` → auto-archive. Manual moves lose audit trail and skip state validation. |
| `gotcha_parallel_task_missing_resource.md` | medium | When a dependency isn't merged from a parallel task, locally stub it inside the target file and document it in the changelog |

## `python/` — Python Gotchas (2 files)

| File | Severity | Summary |
|------|----------|---------|
| `gotcha_hyphen_module_name.md` | medium | `macro-brain` directory hyphen prevents Python module imports — must use `PYTHONPATH=.` and `from src.*` imports |
| `gotcha_terrain_payload_format_mismatch.md` | ~~high~~ RESOLVED | ~~Python `generate_random_terrain` returns `{"costs"}` but Rust `TerrainPayload` expects `{"hard_costs", "soft_costs", "cell_size"}`~~ — FIXED: generator now returns `{hard_costs, soft_costs, width, height, cell_size}` |

---

*Last updated: 2026-04-06. Run `find .agents/knowledge -name "*.md" | sort` to verify.*
