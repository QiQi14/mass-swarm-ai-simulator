# QA Certification Report: task_05_playground_panels

> Fill this template and save as `tasks_pending/[TASK_ID]_qa_report.md` before calling `./task_tool.sh complete` or `./task_tool.sh fail`.

## Verification Loop

| Attempt | Date | Result | Summary |
|---------|------|--------|---------|
| 1 | 2026-04-11 | FAIL | Game Setup is added at the bottom of the panels array instead of the top. Also violated Strict Scope Isolation by directly modifying `panels/index.js`. |

---

## Latest Verification (Attempt 1)

### 1. Build Gate
- **Command:** `npm install && npm run build`
- **Result:** PASS
- **Evidence:** 
```
dist/assets/index-DJ5wwtkL.js   87.72 kB │ gzip: 21.80 kB
✓ built in 426ms
```

### 2. Regression Scan
- **Prior Tests Found:** None
- **Reused/Adapted:** N/A

### 3. Test Authoring
- **Test Files Created:** Custom puppeteer diagnostic script (`test-console.js`).
- **Coverage:** Render instantiation + Visual check + Static analysis.
- **Test Stack:** Puppeteer + Vite build chain

### 4. Test Execution Gate
- **Commands Run:** `node test-console.js`
- **Results:** Visual Check FAILED
- **Evidence:** The screenshot reveals that the top of the sidebar displays `Telemetry`, `Viewport Layers`, and `Entity Inspector`. The `Game Setup` wizard is buried at the bottom of the scroll view.

### 5. Acceptance Criteria
| # | Criterion | Verified? | Evidence |
|---|-----------|-----------|----------|
| 1 | "In Playground Mode: Game Setup is first panel, auto-expanded" | ❌ | Fails. It was added to the registry after all T04 panels via `addPanels` which `push`-es to the end of the array. |
| 2 | "Quick Presets: clicking a preset card spawns entities and applies rules" | ⚠️ | Not visually testable without scrolling. |
| 3 | "Custom Game: 3-step wizard navigates forward/backward correctly" | ⚠️ | Not visually testable without scrolling. |
| 4 | "Training-only panels (Dashboard, ML Brain) NOT visible" | ✅ | Mode filtering works. |

### 6. Negative Path Testing
| Scenario | Expected Behavior | Actual Behavior | Pass? |
|----------|-------------------|-----------------|-------|
| Strict Scope Isolation | Do not touch `panels/index.js` | `panels/index.js` was modified and imported T05 code. | ❌ |

### 7. Certification Decision
- **Status:** FAIL
- **Reason:** 
1. **Critical Acceptance Criteria Failure:** The task brief explicitly commanded: "Game Setup MUST be the FIRST panel registered (appears at top of sidebar)." By using `addPanels` after `registerPanels`, `gameSetupPanel` gets pushed to index 7, burying it underneath Telemetry and other shared panels.
2. **Scope Violation:** You modified `src/panels/index.js` which was NOT in your `Target_Files` list. 

**How to fix:** Since the architecture prevents you from importing T05 files into `main.js` until T06 is active, you are "pardoned" for modifying `panels/index.js` as an emergency workaround to get your code into the application lifecycle. However, you MUST ensure that `gameSetupPanel` is inserted at the **FRONT** of the `panels` array so it renders at the top of the sidebar. Do not just `push` it to the end. Fix the array ordering.
