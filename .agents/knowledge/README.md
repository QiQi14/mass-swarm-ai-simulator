# Knowledge Directory

> Learned experiences from agent sessions. Organized by domain for quick agent lookup.
> When loading context, agents should scan only the folder(s) relevant to their task.

## Directory Structure

```
knowledge/
├── README.md           ← This index (start here)
├── bevy/               ← Bevy ECS engine gotchas and patterns
├── rust/               ← Rust language conventions and patterns
├── tooling/            ← IDE, build tools, dev environment
└── workflow/           ← Multi-agent DAG process rules
```

---

## Quick Lookup by Agent Role

| Agent | Scan These Folders | When |
|-------|-------------------|------|
| **Executor** | `bevy/`, `rust/` | Before writing Bevy/Rust code |
| **QA** | `bevy/`, `tooling/` | Before running tests or diagnosing failures |
| **Planner** | `workflow/`, `rust/` | Before creating task briefs or DAG plans |

---

## `bevy/` — Bevy Engine Gotchas (6 files)

| File | Severity | Summary |
|------|----------|---------|
| `architecture_bevy_mpsc_receiver_sync.md` | high | `mpsc::Receiver` needs `Mutex` wrapper to satisfy Bevy `Resource` `Sync` requirement |
| `deprecation_bevy_18_features.md` | high | Bevy 0.18 removed `bevy_log` and `bevy_winit` — use `default-features = false` |
| `gotcha_bevy_018_test_query.md` | high | Bevy 0.18 removed `Query::get_single` — use `query.single()` instead |
| `gotcha_bevy_schedule_runner_macos.md` | high | `ScheduleRunnerPlugin` on macOS causes 40% TPS degradation — use custom runner |
| `gotcha_bevy_state_unit_tests.md` | high | Must add `StatesPlugin` and call `app.update()` twice for state transitions in tests |
| `gotcha_tick_timeout_overlap.md` | medium | ZMQ timeout (5s) can overlap with smoke test exit (300 ticks = 5s) — adjust thresholds |

## `rust/` — Rust Conventions (1 file)

| File | Severity | Summary |
|------|----------|---------|
| `convention_rust_file_splitting.md` | medium | Split files >300 lines or with 3+ concerns; document rationale if choosing not to split |

## `tooling/` — IDE & Build Tools (2 files)

| File | Severity | Summary |
|------|----------|---------|
| `tooling_stale_rust_analyzer_cache.md` | low | Stale `target/` fingerprints cause phantom errors in rust-analyzer — fix with `cargo clean` |
| `tooling_testing_tmp_dir.md` | low | Use workspace-local temp dirs for test artifacts, not system `/tmp` |

## `workflow/` — Multi-Agent Process (3 files)

| File | Severity | Summary |
|------|----------|---------|
| `architecture_dispatch_template_vs_workflow.md` | high | Dispatch prompt is the ONLY input for executors — don't use `/executor` workflow trigger |
| `convention_strict_scope_and_changelog.md` | high | Executor must create changelog + stay within `Target_Files` scope — mandatory in dispatch template |
| `gotcha_basic_tier_context_ignorance.md` | high | `basic` tier models skip `Context_Bindings` — inline critical rules in the task brief |

---

*Last updated: 2026-04-04. Run `find .agents/knowledge -name "*.md" | sort` to verify.*
