# Task 02: Stage Info Panel + Detail Modal

## Metadata

```yaml
Task_ID: task_02_stage_info
Execution_Phase: 1
Model_Tier: advanced
Live_System_Impact: safe
Feature: "Training Page — Fullscreen Map + Overlay Dashboard Redesign"
```

## Target_Files

- `debug-visualizer/src/panels/training/stage-info.js` [NEW]

## Dependencies

None — Phase 1 task with zero dependencies.

## Context_Bindings

- `context/project`
- `research_digest.md`

## Strict_Instructions

Create a new panel module that displays a compact stage summary card with a "Details" button that opens a modal dialog showing full curriculum data. Also emits a stage-change toast animation when the training stage transitions.

### Module Structure

Single ES module file exporting a default panel object + named exports.

### Exports

1. **`default`** — Panel object conforming to the standard panel interface:
   ```js
   {
     id: 'stage-info',
     title: 'Stage Info',
     icon: '🎯',
     modes: ['training'],
     defaultExpanded: true,
     render(body) { ... },
     update() { ... },
   }
   ```

2. **`loadCurriculum()`** — Named export, async function called once at boot by `training-main.js`.

### Imports

```js
// Only these imports are needed:
import { drawSparkline } from '../../components/sparkline.js';  // optional, for future use
```

Do NOT import from `state.js` for this task. Stage number is read from existing DOM (see below).

### `loadCurriculum()` Implementation

```js
let curriculum = null;

export async function loadCurriculum() {
  try {
    const resp = await fetch('/logs/run_latest/tactical_curriculum.json', { cache: 'no-store' });
    if (resp.ok) curriculum = await resp.json();
  } catch (e) {
    console.warn('[stage-info] Could not load curriculum:', e.message);
  }
}
```

- Fetch path: `/logs/run_latest/tactical_curriculum.json`
- Store in module-level `let curriculum = null`
- Silent failure — if file doesn't exist, card shows "No curriculum data"

### `getCurrentStageFromDOM()` — Internal Helper

```js
function getCurrentStageFromDOM() {
  const el = document.getElementById('dash-stage');
  if (!el) return 0;
  const match = el.textContent.match(/\d+/);
  return match ? parseInt(match[0], 10) : 0;
}
```

This reads the stage number from the Training Dashboard panel's DOM element (`#dash-stage`), which is rendered by `dashboard.js` and updated by its HTTP poll. This pragmatic coupling avoids needing to modify `state.js` (which is outside this task's scope).

### `render(body)` — Compact Card

Render this DOM structure into the `body` element:

```
┌─ 🎯 Stage Info ──────────────────┐
│ Stage 1: Target Selection         │
│ Goal: 80% WR · Min 50 episodes   │
│ Actions: [Hold] [AttackCoord]     │
│ [📋 Details]                      │
└───────────────────────────────────┘
```

**DOM IDs:**
- `#stage-info-name` — stage N + description text
- `#stage-info-goal` — graduation one-liner
- `#stage-info-actions` — container for action badges
- `#stage-info-details-btn` — button that opens the modal

**Logic:**
- Read `currentStage = getCurrentStageFromDOM()`
- If `curriculum` is null, show "Curriculum data unavailable"
- Otherwise:
  - Stage name: `curriculum.training.curriculum[currentStage].description` (or "Unknown" if out of bounds)
  - Goal: `${Math.round(graduation.win_rate * 100)}% WR · Min ${graduation.min_episodes} episodes`
  - Actions: `curriculum.actions.filter(a => a.unlock_stage <= currentStage)` → render each as an inline badge (`<span class="stage-modal__badge">${a.name}</span>`)
  - Details button → `onclick` calls `openStageModal(currentStage)`

### `update()` — Per-Frame Update

Called every animation frame by the overlay system.

```js
let lastRenderedStage = -1;

update() {
  if (!curriculum) return;
  const stage = getCurrentStageFromDOM();
  if (stage !== lastRenderedStage) {
    // Re-render compact card content
    this._updateCardContent(stage);
    // Fire toast if this is a genuine stage change (not initial render)
    if (lastRenderedStage >= 0 && stage > lastRenderedStage) {
      showStageToast(stage);
    }
    lastRenderedStage = stage;
  }
}
```

### `openStageModal(stageIndex)` — Internal Function

Creates and shows a modal dialog. The modal is appended to `document.body` (not inside the card).

**Modal DOM structure:**
```html
<div class="stage-modal stage-modal--open" id="stage-detail-modal">
  <div class="stage-modal__backdrop"></div>
  <div class="stage-modal__dialog">
    <button class="stage-modal__close">&times;</button>
    
    <h2>Stage 1: Target Selection</h2>
    <p class="stage-modal__desc">Read ECP density to pick correct target</p>
    
    <div class="stage-modal__section">
      <h3>Graduation Criteria</h3>
      <p>Win Rate: 80% · Min Episodes: 50</p>
    </div>
    
    <div class="stage-modal__section">
      <h3>Combat Rules</h3>
      <table class="stage-modal__table">
        <thead><tr><th>Source</th><th>Target</th><th>Range</th><th>Effects</th></tr></thead>
        <tbody>
          <tr><td>Brain</td><td>Target</td><td>25</td><td>HP -25/s</td></tr>
          <!-- ... -->
        </tbody>
      </table>
    </div>
    
    <div class="stage-modal__section">
      <h3>Unlocked Actions</h3>
      <div>[Hold] [AttackCoord]</div>
    </div>
    
    <div class="stage-modal__section">
      <h3>Factions</h3>
      <p>F0: Brain (brain) · F1: Trap · F2: Target</p>
    </div>
  </div>
</div>
```

**Close behavior:**
- Click `×` button → remove modal
- Click backdrop → remove modal
- Press `Escape` key → remove modal (use `document.addEventListener('keydown', ...)` + cleanup)

**Data rendering:**
- **Combat rules table:** Iterate `curriculum.combat.rules[]`. Resolve `source_faction` and `target_faction` to names via `curriculum.factions[id].name`. Format effects as `"stat[index] delta/s"` e.g. `"HP -25/s"`.
- **Unlocked actions:** Same logic as compact card but full display
- **Factions:** List each faction with id, name, role, and HP from stats if available

### `showStageToast(stageIndex)` — Internal Function

Creates a toast notification when the stage changes:

```js
function showStageToast(stageIndex) {
  const stageDef = curriculum?.training?.curriculum?.[stageIndex];
  const toast = document.createElement('div');
  toast.className = 'overlay-stage-toast';
  toast.innerHTML = `
    <div style="font-size: 24px; font-weight: 700; font-family: var(--font-mono);">⬆ STAGE ${stageIndex}</div>
    <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">${stageDef?.description || ''}</div>
  `;
  document.body.appendChild(toast);
  toast.addEventListener('animationend', () => toast.remove());
}
```

- Toast uses `.overlay-stage-toast` class (styled by Task 01's overlay.css)
- Auto-removes after animation completes (~4s)
- Only fires when `lastRenderedStage >= 0` (prevents toast on initial load)

### CSS Classes Used (from overlay.css — Task 01)

These classes MUST be used exactly as listed (they are defined in Task 01):
- `.stage-modal` — modal container
- `.stage-modal--open` — visible state
- `.stage-modal__backdrop` — click-to-close overlay
- `.stage-modal__dialog` — centered content box
- `.stage-modal__close` — close button
- `.stage-modal__section` — section wrapper
- `.stage-modal__table` — rules table
- `.stage-modal__badge` — action badge
- `.overlay-stage-toast` — toast animation container

### What NOT to Do

- Do NOT modify `state.js` — read stage from DOM
- Do NOT start any HTTP polling — this panel reads from existing Dashboard poll via DOM
- Do NOT import `router.js` — this panel doesn't need routing
- Do NOT create additional files — everything goes in `stage-info.js`
- Do NOT use `innerHTML` with user-controlled data — curriculum JSON is trusted local data

## Verification_Strategy

```yaml
Test_Type: manual_steps
Test_Stack: Browser console
Acceptance_Criteria:
  - "Panel renders compact stage info with name, goal, and action badges"
  - "Details button opens modal with full combat rules table"
  - "Modal closes on X click, backdrop click, and Escape key"
  - "Stage change fires toast animation element with .overlay-stage-toast class"
  - "No errors if curriculum JSON is unavailable (graceful fallback text)"
  - "getCurrentStageFromDOM reads from #dash-stage element"
Manual_Steps:
  - "Load training page, verify compact card renders with stage data"
  - "Click Details button, verify modal opens with rules table"
  - "Close modal via all 3 methods (X, backdrop, Escape)"
  - "Simulate stage change in DOM, verify toast appears"
```
