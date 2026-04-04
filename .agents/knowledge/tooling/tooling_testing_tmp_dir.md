# Lesson: Avoid /tmp directory for scratch scripts

**Category:** tooling
**Discovered:** 2026-04-03
**Severity:** low

## Context
When writing temporary python scripts (e.g. `ws_test.py`) to validate running background commands during QA testing, an agent attempted to save the script to `/tmp/ws_test.py`.

## Problem
Depending on the macOS permissions and sandboxing constraints, writing to or executing from `/tmp/` can lead to permission issues or block the test suite runner entirely. The user observed the agent struggling to use temp files due to these permission blockers.

## Correct Approach
Instead of writing scratch scripts and test validation tools to `/tmp/`, write them into the local workspace, ideally within `.agents/scripts/`. This ensures they fall under the standard directory permission tree for the project.

## Example
- ❌ What the executor did: Using `TargetFile: /tmp/ws_test.py`
- ✅ What it should be: Using `TargetFile: .agents/scripts/ws_test.py`
