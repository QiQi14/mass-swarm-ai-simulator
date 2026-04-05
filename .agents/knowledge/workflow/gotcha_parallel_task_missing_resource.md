# Lesson: Handling Missing Dependencies in Parallel DAG Execution

**Category:** gotcha
**Discovered:** task_13_ws_commands
**Severity:** medium

## Context
In a parallel DAG workflow where multiple implementation tasks are operating concurrently, an executor may be instructed to use or assign a resource (like `ActiveFogFaction`) that is supposed to be created by another simultaneous task (`task_12_visibility_ipc`). 

## Problem
Because the dependent task is being implemented in parallel (or hasn't merged yet), the executor experiences compiler errors referencing a missing struct/resource. Strict isolation prohibits the executor from modifying the missing target files outside of their specified targets list, blocking development.

## Correct Approach
Instead of stripping the implementation or halting with an unresolvable error, the executor should declare a placeholder `struct` matching the required name directly within their own target file to "appease the compiler" and complete their task's logic. Then, the executor must explicitly document this in the changelog as a deviation, noting where the missing resource was instantiated locally so it can be integrated down the line.

## Example
- ❌ What the executor did: Stopped, stripped the logic needing the unmerged struct, and failed the task OR violated scope by arbitrarily creating the structure in a system-agnostic registry file without permission.
- ✅ What it should be: Created a temporary wrapper bounded inside the target file (e.g. `pub struct ActiveFogFaction(pub Option<u32>);`), finished the associated logic referencing it, and documented the required follow-up.
