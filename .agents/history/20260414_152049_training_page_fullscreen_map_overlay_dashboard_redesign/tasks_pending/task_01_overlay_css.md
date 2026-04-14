# Task 01: Overlay Design System

## Metadata

```yaml
Task_ID: task_01_overlay_css
Execution_Phase: 1
Model_Tier: advanced
Live_System_Impact: safe
Feature: "Training Page — Fullscreen Map + Overlay Dashboard Redesign"
```

## Target_Files

- `debug-visualizer/src/styles/overlay.css` [NEW]

## Dependencies

None — Phase 1 task with zero dependencies.

## Context_Bindings

- `skills/frontend-ux-ui`
- `strategy_brief.md`
- `research_digest.md`

## Strict_Instructions

Create a complete CSS design system for the training page's glassmorphic overlay dashboard. This file will be imported by `training-main.js` via `import './styles/overlay.css'` (Vite handles the bundling).

### Design Direction

**Tactical command center** — dark glass panels with accent glow, precision military-HUD aesthetic. Reuse the existing CSS variables from `variables.css`:

| Variable | Value | Usage |
|----------|-------|-------|
| `--accent-primary` | `#06d6a0` | Accent borders, glow, active states |
| `--bg-surface` | `rgba(8, 12, 18, 0.92)` | Base for glass overlays |
| `--font-display` | `'Geist', ...` | Headers, labels |
| `--font-mono` | `'Geist Mono', ...` | Data values |
| `--border-subtle` | `rgba(255, 255, 255, 0.06)` | Card borders |
| `--radius-lg` | `12px` | Card corners |
| `--transition-base` | `0.2s ease` | Hover/state transitions |
| `--transition-spring` | `0.35s cubic-bezier(...)` | Slide animations |

### Required Classes

#### 1. Overlay Card (`.overlay-card`)
```css
background: rgba(8, 12, 18, 0.75);
backdrop-filter: blur(12px) saturate(1.4);
-webkit-backdrop-filter: blur(12px) saturate(1.4);
border: 1px solid rgba(6, 214, 160, 0.12);
border-radius: 12px;
box-shadow: 0 8px 32px rgba(0,0,0,0.4);
```
- `.overlay-card__header` — flex row, icon + title, font `--font-display`, uppercase, `font-size: 11px`, `letter-spacing: 0.1em`, `color: var(--text-secondary)`, padding `12px 16px`, bottom border `1px solid rgba(255,255,255,0.04)`
- `.overlay-card__body` — padding `12px 16px`

#### 2. Top Bar (`.overlay-top-bar`)
- `position: fixed; top: 0; left: 0; right: 0; z-index: 1000; height: 48px`
- Same glassmorphic background as cards
- Flex row with: connection badge area, page title "SwarmControl", stage badge, spacer, action buttons (minimize, layers toggle)
- Bottom border glow: `border-bottom: 1px solid rgba(6, 214, 160, 0.08)`
- `.overlay-top-bar__title` — uppercase, letter-spacing, display font
- `.overlay-top-bar__actions` — flex row, gap, button styling
- `.overlay-btn` — generic overlay button: 32×32px, transparent bg, border-radius 8px, hover: `background: rgba(255,255,255,0.06)`
- `.overlay-btn--active` — active state for toggles like layers

#### 3. Bottom Card Groups
- `.overlay-group--left` — `position: fixed; bottom: 24px; left: 24px; z-index: 999; display: flex; flex-direction: column; gap: 12px; max-width: 320px;`
- `.overlay-group--right` — `position: fixed; bottom: 24px; right: 24px; z-index: 999; display: flex; flex-direction: column; gap: 12px; max-width: 280px;`
- Slide-in animation on load: each card uses `animation: overlaySlideIn 0.4s ease-out both` with staggered `animation-delay` (0s, 0.05s, 0.1s via `:nth-child`)
- `@keyframes overlaySlideIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }`

#### 4. Minimized State
- `.overlay--minimized .overlay-group--left, .overlay--minimized .overlay-group--right` — `opacity: 0; pointer-events: none; transform: translateY(20px); transition: all 0.3s ease-out;`
- `.overlay--minimized .overlay-mini-strip` — `display: flex` (normally `display: none`)
- `.overlay--expanded .overlay-mini-strip` — `display: none`
- Restore canvas hint when minimized:
  ```css
  .training-page .canvas-hint { opacity: 0; pointer-events: none; }
  .overlay--minimized ~ .canvas-hint,
  .overlay--minimized + main .canvas-hint { opacity: 0.8; transition: opacity 0.3s ease; }
  ```

#### 5. Mini Strip (`.overlay-mini-strip`)
- `position: fixed; bottom: 24px; left: 24px; right: 24px; z-index: 999; height: 44px`
- Same glassmorphic card styling
- Flex row: stage badge, episode count (mono font), win rate mini-bar (inline), connection dot, expand button
- `.mini-strip__stage` — compact badge, accent background at 15% opacity
- `.mini-strip__metric` — mono font, small
- `.mini-strip__wr-bar` — inline progress bar, 60px wide, 4px tall
- `.mini-strip__expand` — icon button aligned right

#### 6. Stage Graduation Toast (`.overlay-stage-toast`)
- `position: fixed; top: 72px; left: 50%; transform: translateX(-50%); z-index: 2000;`
- Glassmorphic card with stronger accent glow
- `border: 1px solid rgba(6, 214, 160, 0.3)` (brighter than cards)
- `box-shadow: 0 0 40px rgba(6, 214, 160, 0.15)` (teal glow)
- `animation: stageToast 4s ease-out forwards`
- `@keyframes stageToast { 0% { opacity: 0; transform: translateX(-50%) translateY(-20px); } 8% { opacity: 1; transform: translateX(-50%) translateY(0); } 75% { opacity: 1; } 100% { opacity: 0; transform: translateX(-50%) translateY(-10px); } }`
- Content styling: large stage number, description text below

#### 7. Stage Detail Modal (`.stage-modal`)
- `.stage-modal` — `position: fixed; inset: 0; z-index: 2000; display: flex; align-items: center; justify-content: center; opacity: 0; pointer-events: none; transition: opacity 0.25s ease;`
- `.stage-modal--open` — `opacity: 1; pointer-events: auto;`
- `.stage-modal__backdrop` — `position: absolute; inset: 0; background: rgba(0, 0, 0, 0.6); backdrop-filter: blur(4px);`
- `.stage-modal__dialog` — `position: relative; max-width: 600px; width: 90vw; max-height: 80vh; overflow-y: auto; z-index: 1;` — same glassmorphic card styling but elevated: `border: 1px solid rgba(6, 214, 160, 0.18)`, `box-shadow: 0 16px 64px rgba(0,0,0,0.5)`
- `.stage-modal__close` — absolute top-right, 32×32px, `×` character, transparent with hover glow
- `.stage-modal__section` — margin-bottom, section titles uppercase dimmed
- `.stage-modal__table` — compact table with `border-collapse: collapse`, mono data font, alternating row `background: rgba(255,255,255,0.02)`, cell padding 6px 12px, header row with bottom border
- `.stage-modal__badge` — inline action badges: small pill, accent border, accent text at reduced opacity
- Scrollbar styling matching `.panel-scroll` (4px, accent colored)

#### 8. Layers Dropdown (`.layers-dropdown`)
- `position: fixed; top: 56px; right: 24px; z-index: 1001;`
- Same glassmorphic card styling, max-width 280px
- `.layers-dropdown--open` — visible
- Contains toggle controls (reuses `.toggle-control` from `controls.css`)
- Click-outside closes

#### 9. Mobile Training Sheet (`.training-sheet`)
- Only visible at `@media (max-width: 768px)`
- `position: fixed; bottom: 0; left: 0; right: 0; z-index: 200;`
- Glassmorphic card, top border-radius `16px 16px 0 0`
- `.training-sheet__handle` — center-aligned pill handle (same as existing bottom-sheet)
- Peek state (default): `transform: translateY(calc(100% - 64px));` showing only `.training-sheet__peek`
- `.training-sheet--expanded` — `transform: translateY(0);`
- `.training-sheet__peek` — flex row, compact training status (stage badge + ep + WR)
- `.training-sheet__body` — padding, shows training status summary card + layer toggles
- Height: `max-height: 60vh`
- Transition: `transform 0.35s cubic-bezier(0.4, 0, 0.2, 1)`

#### 10. Responsive Rules
```css
@media (max-width: 768px) {
  .overlay-group--left,
  .overlay-group--right,
  .overlay-mini-strip,
  .layers-dropdown { display: none !important; }
  
  .overlay-top-bar { height: 40px; }
  .overlay-top-bar__title { display: none; }
}

@media (min-width: 769px) {
  .training-sheet { display: none !important; }
}
```

### What NOT to Do
- Do NOT use `@import` to load this file — it's loaded by JS (`import './styles/overlay.css'`)
- Do NOT define `.app-container`, `.sidebar`, or any sidebar layout classes — those belong to `layout.css`
- Do NOT duplicate `.connection-badge` or `.status-dot` styles — those are in `layout.css` and work as-is
- Do NOT use Inter, Roboto, or other generic fonts — use the project's existing `--font-display` and `--font-mono` variables

## Verification_Strategy

```yaml
Test_Type: manual_steps
Test_Stack: Browser DevTools
Acceptance_Criteria:
  - "overlay.css defines all classes from the CSS contract"
  - "Classes use existing CSS variables from variables.css"
  - "Modal has backdrop + dialog + close button + table styles"
  - "Mobile sheet has peek + expanded states with handle"
  - "Minimized state shows canvas hint, expanded state hides it"
  - "Stage toast has 4s animation with glow accent"
  - "Responsive breakpoint at 768px hides desktop overlays and shows mobile sheet"
Manual_Steps:
  - "Import overlay.css into training.html (Task 03) and verify rendered styles in browser"
```
