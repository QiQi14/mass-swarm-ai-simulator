# Training UI Revamp — Implementation Plan

## Problem Summary

Four distinct UX bugs/aesthetics issues in `debug-visualizer/src/` identified from user screenshots and source audit:

| # | Problem | Root Cause | Files Affected |
|---|---------|-----------|----------------|
| 1 | **Height mismatch** — ML Brain Status & Stage Info side-by-side cards have different heights, creating a jarring visual gap | `align-items: flex-end` on `.overlay-linked-row` lets cards size to their own content; Stage Info grows taller than ML Brain | `overlay.css` |
| 2 | **Collapsed channels bug** — when an episode resets, active toggles become visually inactive | `_updateChannelAvailability()` calls `input.checked = false` whenever `hasData()` returns false — which it briefly does at episode boundary before new data arrives. This flickers the checked state to off | `training-main.js` |
| 3 | **Collapsed strip looks empty** — only dots in a row, no label, no context. Icons in headers use Unicode (📡 🧠 🎯 📈 👁) | All icon slots use emoji string literals | `training-main.js`, `ml-brain.js`, `stage-info.js`, `dashboard.js`, overlay.css header section |
| 4 | **Stage Info card boring; action badges look like toggles** — the badge style is identical to `.layer-pill` (same green border + bg). Modal sections have no visual hierarchy | `stage-modal__badge` shares the same CSS rules as `layer-pill input:checked` | `overlay.css`, `stage-info.js` |

---

## Design Decisions

> [!IMPORTANT]
> **Icon strategy**: Replace all unicode/emoji with inline SVG icons from the Lucide icon set (MIT license, no runtime dependency). Icons are inlined as `<svg>` strings in JS templates. Size: 14×14px for card headers, 12×12 for channel rows.

> [!IMPORTANT]
> **Height unification**: Both ML Brain Status and Stage Info cards join the same flex stretch context via `align-items: stretch` on `.overlay-linked-row`. A minimum card height of `140px` is set on the linked-row cards to prevent collapse. The Dashboard card is excluded from this constraint (left of linked-row).

> [!IMPORTANT]
> **Channel availability bug fix**: `_updateChannelAvailability()` must NOT uncheck active toggles during a transient data gap. New behavior: only add/remove the `--disabled` class and block new activations. Unchecking only happens if data was never available at all (initial state, `hasData()=false` AND `!input.checked`). This preserves user intent across episode boundaries.

> [!IMPORTANT]
> **Collapsed strip redesign**: When collapsed, the strip shows the **count of active channels** (`N active`) plus individual colored dots with a tooltip. Minimum height set so the card doesn't collapse to a sliver.

> [!IMPORTANT]
> **Action chips vs toggle pills**: Unlocked actions in Stage Info use a NEW class `.action-chip` — a rounded rectangular chip with a **left-side accent color bar** (cyan), an **icon prefix** (⚡ SVG), and a bold label. This is visually distinct from the toggle-style `.layer-pill` which is still used only for Overlays.

---

## Proposed Changes

### Phase 1 — Parallel Tasks (no file collision)

---

#### Task 01 — CSS: Fix Height Mismatch + Action Chip Styles + Collapsed Strip Styles

#### [MODIFY] [overlay.css](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/debug-visualizer/src/styles/overlay.css)

**Change A — Linked Row Height Unification:**
```css
/* BEFORE */
.overlay-linked-row {
  align-items: flex-end;
}

/* AFTER */
.overlay-linked-row {
  align-items: stretch;  /* All children fill to same height */
}

/* Add: min-height on the two linked-row cards */
#overlay-card-ml-brain,
#overlay-card-stage-info {
  min-height: 148px;
}

/* Fix: body inside linked-row must also stretch */
.overlay-linked-row > .overlay-card .overlay-card__body {
  flex: 1;
  display: flex;
  flex-direction: column;
}
```

**Change B — `.action-chip` (new class, replaces badge style on action buttons):**
```css
.action-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 700;
  color: var(--text-primary);
  padding: 5px 10px 5px 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-left: 3px solid var(--accent-primary);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  transition: background 0.15s, border-color 0.15s;
}
.action-chip:hover {
  background: rgba(6, 214, 160, 0.08);
  border-color: rgba(255, 255, 255, 0.12);
  border-left-color: var(--accent-primary);
}
.action-chip__icon {
  color: var(--accent-primary);
  flex-shrink: 0;
  display: flex;
  align-items: center;
}
```

**Change C — Collapsed channel strip (min-height + counter style):**
```css
.channel-active-strip {
  min-height: 36px;    /* was: 28px — prevent collapse to nothing */
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
}

/* New: counter badge in collapsed strip */
.channel-strip-count {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  color: var(--accent-primary);
  padding: 1px 6px;
  border-radius: 10px;
  background: rgba(6, 214, 160, 0.12);
  border: 1px solid rgba(6, 214, 160, 0.25);
  margin-right: 2px;
}
```

**Change D — Stage Modal: section headings upgrade + Graduation box:**
```css
/* Graduation box — keep but make it a proper stat row */
.grad-metrics {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.grad-metric {
  align-items: center;
  gap: 10px;
}
.grad-metric__icon {
  color: var(--accent-warning);
  flex-shrink: 0;
}
.grad-metric__label {
  font-size: 11px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.grad-metric__value {
  font-family: var(--font-mono);
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

/* Stage modal section divider */
.stage-modal__section-title {
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin: 0 0 10px 0;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}
```

---

#### Task 02 — JS: SVG Icon System + Panel Icon Updates

**Library choice**: Inline SVG strings (no node_modules). Create a new file:

#### [NEW] [debug-visualizer/src/components/icons.js](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/debug-visualizer/src/components/icons.js)

Exports an `icon(name, size)` function returning a ready-to-embed `<svg>` string. Required icons:

| Name | Lucide source | Used in |
|------|--------------|---------|
| `brain` | `Brain` | ml-brain panel header |
| `target` | `Crosshair` | stage-info panel header |
| `chart-line` | `TrendingUp` | dashboard panel header |
| `eye` | `Eye` | overlays card header |
| `radio` | `Radio` | observation channels header |
| `zap` | `Zap` | action chip prefix icon |
| `chevron-right` | `ChevronRight` | collapse button (open) |
| `chevron-left` | `ChevronLeft` | collapse button (closed) |
| `minimize` | `Minus` | overlay minimize button |
| `maximize` | `Square` (outline) | overlay expand button |
| `trophy` | `Trophy` | graduation win rate |
| `layers` | `Layers` | graduation min episodes |

```js
// src/components/icons.js
const SVG_ICONS = {
  brain: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">...</svg>`,
  // ... (full paths from lucide.dev source)
};

export function icon(name, size = 14) {
  const raw = SVG_ICONS[name] || SVG_ICONS['zap'];
  // Replace width/height attrs with size param
  return raw.replace(/width="\d+"/, `width="${size}"`).replace(/height="\d+"/, `height="${size}"`);
}
```

#### [MODIFY] [ml-brain.js](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/debug-visualizer/src/panels/training/ml-brain.js)

- Import `icon` from `../../components/icons.js`
- Replace `icon: '🧠'` with `icon: icon('brain')`
- In `render()`, replace `🟢 Connected` / `🔴 Disconnected` / `⚠️ Active` / `✅ Normal` with SVG dot indicators using `<span class="status-dot status-dot--ok">` pattern (colored CSS circle, no unicode)
- Remove inline emoji from `updateMlBrainPanel()` directive summaries — replace with plain text: `'Hold (Brake)'`, `'Idle'`, `'Attack → Faction X'` etc.

#### [MODIFY] [stage-info.js](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/debug-visualizer/src/panels/training/stage-info.js)

- Import `icon` from `../../components/icons.js`
- Replace `icon: '🎯'` with `icon: icon('target')`
- In `_updateCardContent()`, change action badges from `stage-modal__badge` to `action-chip` class with icon prefix: `` `<span class="action-chip"><span class="action-chip__icon">${icon('zap', 12)}</span>${a.name.toUpperCase()}</span>` ``
- In `openStageModal()` graduate box: restructure `grad-metric` to use `grad-metric__icon`, `grad-metric__label`, `grad-metric__value` sub-elements
- In `openStageModal()` actions section: also use `action-chip` instead of `stage-modal__badge`
- Stage toast: replace `⬆` with SVG arrow icon

#### [MODIFY] [dashboard.js](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/debug-visualizer/src/panels/training/dashboard.js)

- Import `icon` from `../../components/icons.js`
- Replace `icon: '📈'` with `icon: icon('chart-line')`

---

#### Task 03 — JS: Observation Channels Bug Fix + Collapsed Strip Redesign

#### [MODIFY] [training-main.js](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/debug-visualizer/src/training-main.js)

> [!WARNING]
> This file is 498 lines — approaching the 300-line split threshold. Since it is a bootstrap/orchestration file (all items are tightly coupled: init sequence + DOM wiring), it stays as-is per convention. Add a rationale comment at the top.

**Change A — Bug fix in `_updateChannelAvailability`:**

Current broken behavior:
```js
// BUG: unchecks toggles the moment hasData() temporarily returns false
if (input && input.checked) {
  input.checked = false;
  t.setter(false);
  refreshActiveStrip();
}
```

Fixed behavior: Only un-check if the user hasn't manually activated it AND data never arrived. Preserve checked state on transient data gaps:
```js
window._updateChannelAvailability = function() {
  for (const t of allChannels) {
    const row = document.getElementById(`row-${t.id}`);
    if (!row) continue;
    const input = row.querySelector('input');
    const available = t.hasData();

    if (available) {
      row.classList.remove('channel-row--disabled');
      row.title = t.desc;
    } else {
      row.classList.add('channel-row--disabled');
      row.title = `${t.desc} (no data yet)`;
      // IMPORTANT: Do NOT uncheck here. Only block new activations via CSS pointer-events:none.
      // This preserves user-toggled state across episode resets where data briefly disappears.
      // The `change` event handler already guards: if (!t.hasData()) { e.target.checked = false; }
      // So re-enabling a disabled channel is still blocked — we just don't forcibly clear existing state.
    }
  }
  refreshActiveStrip(); // always refresh strip to reflect current reality
};
```

**Change B — Replace unicode in headers with `icon()` calls:**

Import icons at top:
```js
import { icon } from './components/icons.js';
```

Replace panel icon strings in `renderOverlayCards()`:
```js
// BEFORE: const icon = panel.icon || '📌';
// AFTER:
const iconHtml = panel.icon || '<svg ...default icon.../>';
header.innerHTML = `<span class="overlay-card__header-icon">${iconHtml}</span> <span>${title}</span>`;
```

Replace the hardcoded `📡` in `buildLayersBar()` channel card header:
```js
forceCard.innerHTML = `
  <div class="overlay-card__header channel-card__header">
    <span class="overlay-card__header-icon">${icon('radio')}</span>
    <span>Observation Channels</span>
    <button class="channel-collapse-btn" id="channel-collapse-btn" title="Collapse to active only">
      ${icon('chevron-left', 12)}
    </button>
  </div>
  ...
`;
```

Update collapse button toggle to swap between `chevron-left` / `chevron-right` SVGs.

Replace overlays card header `👁`:
```js
envCard.innerHTML = `
  <div class="overlay-card__header"><span class="overlay-card__header-icon">${icon('eye')}</span> <span>Overlays</span></div>
  ...
`;
```

**Change C — Collapsed strip redesign:**

`refreshActiveStrip()` — updated to show count badge + dots:
```js
function refreshActiveStrip() {
  if (!channelCollapsed) return;
  const active = allChannels.filter(t => {
    const input = document.getElementById(t.id);
    return input?.checked;
  });
  if (active.length === 0) {
    activeStrip.innerHTML = `<span class="channel-strip-none">No active channels</span>`;
  } else {
    const countBadge = `<span class="channel-strip-count">${active.length} active</span>`;
    const dots = active.map(t =>
      `<span class="channel-strip-dot" style="background:${t.color};box-shadow:0 0 5px ${t.color}" title="ch${t.ch}: ${t.label}"></span>`
    ).join('');
    activeStrip.innerHTML = countBadge + dots;
  }
}
```

Also replace minimize button icons in `buildTopBar()`:
```js
// BEFORE: btn.innerHTML = '<span>—</span>';
// AFTER:  btn.innerHTML = icon('minimize');
```

---

### Phase 2 — Integration: Top Bar SVG Button + CSS Header Icon Alignment

#### [MODIFY] [overlay.css](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/debug-visualizer/src/styles/overlay.css)

Add CSS to properly align SVG icons in card headers:
```css
.overlay-card__header-icon {
  display: flex;
  align-items: center;
  color: var(--accent-primary);
  opacity: 0.8;
  flex-shrink: 0;
}

.overlay-card__header-icon svg {
  display: block;
}
```

---

## File Summary

| File | State | Owner Task | Change Type |
|------|-------|-----------|-------------|
| `src/styles/overlay.css` | Modify | Task 01 + Phase 2 | CSS additions — height fix, new classes, icon alignment |
| `src/components/icons.js` | **NEW** | Task 02 | SVG icon library with `icon(name, size)` export |
| `src/panels/training/ml-brain.js` | Modify | Task 02 | Import icon, replace emoji, refactor status display |
| `src/panels/training/stage-info.js` | Modify | Task 02 | Import icon, action-chip class, modal restructure |
| `src/panels/training/dashboard.js` | Modify | Task 02 | Import icon, replace emoji |
| `src/training-main.js` | Modify | Task 03 | Bug fix, icon imports, strip redesign |

---

## DAG Execution Graph

```
Phase 1 (Parallel — no collisions):
  Task 01: overlay.css changes (height, action-chip, strip styles)
  Task 02: icons.js [NEW] + ml-brain.js + stage-info.js + dashboard.js
  Task 03: training-main.js (bug fix + icon imports + strip redesign)

Phase 2 (Sequential — after Phase 1 completes):
  Task 04: overlay.css icon alignment additions + final polish pass
           (waits for Task 02 to know icon SVG dimensions)
```

> Task 01 and Task 04 both touch `overlay.css`. They are **sequential by design** (Phase 1 vs Phase 2). The Planner marks Task 04 as blocked on Task 01 completion.

---

## Contracts

### `icon(name, size)` → `string`
- Input: `name: string` — one of the named keys in SVG_ICONS map
- Input: `size: number` — pixel width/height (default 14)
- Output: raw HTML string `<svg ...>...</svg>` ready for `innerHTML`
- **No DOM side effects** — pure string function

### Panel `icon` field type change
- **Before:** `icon: '🎯'` (unicode string embedded in `header.innerHTML`)  
- **After:** `icon: icon('target')` (SVG HTML string)
- `renderOverlayCards()` in `training-main.js` treats the `icon` field as raw HTML (already uses template literal). No contract break.

### `.action-chip` vs `.stage-modal__badge`
- `.stage-modal__badge` is **only used in** the modal's Unlocked Actions section (fully replaced)
- `.layer-pill` remains unchanged (Overlays card toggles are NOT action chips)
- These are **not shared** — no unintended collisions

---

## Verification Plan

### Automated
- None (UI-only changes; no Rust or Python code modified)
- Live_System_Impact: `safe` — visualizer CSS/JS only

### Manual Browser Steps
1. Open `localhost:5173/training.html`
2. **Height test**: ML Brain Status and Stage Info cards must share identical height (top edges and bottom edges aligned)
3. **Collapsed strip**: Click `◀` to collapse channels → verify count badge displays `N active` + colored dots appear
4. **Episode reset**: Wait for an episode boundary (or manually trigger via WS) — active channel toggles must **remain checked** after the episode starts
5. **SVG icons**: All card headers must show SVG icons (no emoji) — check browser DevTools Elements panel
6. **Action chips**: In Stage Info card and in modal Unlocked Actions, chips must show left cyan border + zap icon, visually distinct from the Overlay toggle pills
7. **Modal graduation section**: Trophy and layers icons visible, value in large mono font, label in small caps above
8. **Minimize button**: Click `—` button — SVG icon used instead of unicode, tooltip still correct
