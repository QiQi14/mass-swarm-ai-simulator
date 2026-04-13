# Lesson: Orphaned new files due to strict scope constraints

**Category:** gotcha
**Discovered:** task_02_design_system (2026-04-11)
**Severity:** high

## Context
When performing frontend restyling with a "Strict Scope Isolation" rule, an Executor created a new central CSS file (`reset.css`) that was explicitly listed in `Target_Files`.

## Problem
Because `index.html` was not listed in `Target_Files`, the executor did not update `index.html` to link the new `reset.css` file. Furthermore, the executor did not use `@import "./reset.css";` in any of the *other* modified CSS files (like `variables.css` or `layout.css`). 
This resulted in `reset.css` being completely orphaned. Since `reset.css` contained the foundational body colors, fonts, and textures, the entire restyle collapsed to browser default fallback fonts and white backgrounds, failing the task's visual acceptance criteria.

## Correct Approach
If you are authorized to create a NEW `foo.css` file, but NOT authorized to touch `index.html`, you MUST leverage standard CSS cascade patterns by adding `@import './foo.css';` to one of the other CSS files that *is* authorized and already loaded by the HTML entry point.
Alternatively, if bridging the file is impossible without breaking scope, the executor MUST stop and ask for an architectural review or document the intentional lack of linkage for the final integration agent.

## Example
- ❌ What the executor did: Created `reset.css` but left it unlinked, hoping the index/router magically finds it.
- ✅ What it should be: Created `reset.css`, then added `@import './reset.css';` at the top of `variables.css` (which was inside `Target_Files` and already linked in the host page).
