# Lesson: Refactoring exported functions under strict scope

**Category:** gotcha
**Discovered:** task_03_app_shell (2026-04-11)
**Severity:** high

## Context
When extracting a utility function from an existing file into a new dedicated component file (e.g., extracting `showToast` from `websocket.js` into `toast.js`).

## Problem
Because of the DAG's Strict Scope Isolation rule, the executor is rarely authorized to update all the *other* files in the project that were importing that function (e.g., `src/controls/spawn.js`). 
By simply removing the export from the original file, the executor causes widespread `Module Error: "X" is not exported by "Y"` failures across the project during Vite build, crashing the application.

## Correct Approach
If you extract logic but cannot update the consuming files due to scope constraints, you MUST **re-export** the function from its original location so that out-of-scope files maintain their contract without modification.

## Example
- ❌ What the executor did: Removed `export function showToast` from `websocket.js`.
- ✅ What it should be: Left `export { showToast } from './components/toast.js';` at the bottom of `websocket.js` so that `import { showToast } from '../websocket.js'` in out-of-scope files continues to work.
