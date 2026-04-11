# Lesson: Deleting DOM elements crashes out-of-scope modules on load

**Category:** workflow
**Discovered:** task_03_app_shell (2026-04-11)
**Severity:** high

## Context
When executing a phased refactor (e.g., rewriting `index.html` to remove old UI panels that will be natively rebuilt in later tasks).

## Problem
Out-of-scope Javascript modules (e.g., `src/panels/index.js`) often run DOM queries at the top level of the module (e.g., `const ref = document.getElementById('my-canvas'); ref.getContext(...)`).
If you remove the DOM elements that these out-of-scope files expect, the browser will throw `TypeError: Cannot read properties of null` the moment the module is imported. Because this happens at module resolution time, it cannot be caught by `try...catch` blocks further down the execution tree, and the entire application crashes.

## Correct Approach
When replacing HTML structures in a multi-task refactor, you MUST leave hidden DOM stubs (e.g., `<div id="xyz" style="display:none"></div>` or `<canvas id="abc" style="display:none"></canvas>`) for any elements expected by legacy files that you are not authorized to modify.
These stubs allow the out-of-scope Javascript to execute without crashing, paving the way for the later tasks to clean them up.

## Example
- ❌ What the executor did: Deleted `<canvas id="graph-tps">` because the panel system was being rewritten, causing `src/panels/index.js` to crash violently on load.
- ✅ What it should be: Included `<canvas id="graph-tps" style="display: none;"></canvas>` inside `index.html` to placate out-of-scope legacy module expectations until that module's respective task could be completed.
