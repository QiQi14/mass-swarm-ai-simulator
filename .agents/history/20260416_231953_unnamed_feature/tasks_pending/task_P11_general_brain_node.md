# Task P11: General Brain Node

- **Task_ID:** `P11_general_brain_node`
- **Execution_Phase:** 3 (depends on P08, P09)
- **Model_Tier:** `advanced`
- **Live_System_Impact:** `safe`

## Target_Files
- `debug-visualizer/src/node-editor/nodes/general.js` — NEW
- `debug-visualizer/src/node-editor/brain-runner.js` — NEW
- `debug-visualizer/src/node-editor/compiler.js` — MODIFY (extend with brain integration)

## Dependencies
- P08 (combat nodes), P09 (nav nodes) — brain node connects to both

## Context_Bindings
- `implementation_plan_playground_feature_3.md` — Task 11 section (brain runner ONNX.js integration)
- `strategy_brief.md` — §Action Space v3 (brain uses same 8-action vocabulary)
- `playground_strategy_brief.md` — General node specification

## Strict_Instructions
**Read `implementation_plan_playground_feature_3.md` → Task 11 section.** Build General (Brain) node that connects to a faction, loads an ONNX model, and runs inference loop. The brain-runner.js implements the 10Hz decision loop: snapshot→vectorize→infer→decode action→inject_directive. Extend compiler to output `brains[]` array.

## Verification_Strategy
```
Test_Type: manual_steps
Acceptance_Criteria:
  - "General node connects to faction output port"
  - "Can specify model path and decision interval"
  - "Brain runner loads ONNX model and runs inference loop"
  - "Inference outputs are decoded to WS directives"
```
