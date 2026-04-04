# Lesson: Basic tier models skip context bindings

**Category:** gotcha
**Discovered:** task_01_project_scaffold
**Severity:** high

## Context
A task was assigned `Model_Tier: basic`. The task brief listed several `Context_Bindings`, including `skills/rust-code-standards`, which contained critical commenting conventions (like adding `//!` module comments).

## Problem
The Executor completely ignored the Rust commenting standards. This wasn't an AI failure—it was a framework logic consequence. The Executor workflow explicitly instructs `basic` tier models to "Skip all external file reading. Your Task Brief below IS your complete instruction." Therefore, any `Context_Bindings` placed on a `basic` task are dead code and will not be applied.

## Correct Approach
If a task requires adherence to external files (like a `SKILL.md` or a convention file), it MUST be assigned at least `Model_Tier: standard` so the Executor is allowed to read the files. Alternatively, if it must be `basic`, the required conventions must be explicitly copy-pasted into the `Strict Instructions` section of the task brief.

## Example
- ❌ What the abstract planner did: Set `Model_Tier: basic` but then provided `Context_Bindings: - skills/rust-code-standards`.
- ✅ What it should be: Set `Model_Tier: standard` if external context is strictly required, OR paste the standard directly into the `basic` task prompt.
