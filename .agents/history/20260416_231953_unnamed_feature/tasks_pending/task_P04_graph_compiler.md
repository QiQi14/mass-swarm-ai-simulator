# Task P04: Graph Compiler

- **Task_ID:** `P04_graph_compiler`
- **Execution_Phase:** 1 (depends on P02, P03)
- **Model_Tier:** `advanced`
- **Live_System_Impact:** `safe`

## Target_Files
- `debug-visualizer/src/node-editor/compiler.js` — NEW

## Dependencies
- P02 + P03 complete (node type definitions)

## Context_Bindings
- `implementation_plan_playground_feature_2.md` — Task 04 section (detailed compiler algorithm)
- `implementation_plan_playground.md` — §Graph Compiler Output Contract
- `playground_strategy_brief.md` — Node→WS command mapping

## Strict_Instructions
**Read `implementation_plan_playground_feature_2.md` → Task 04 section.** Build `compileGraph(editor)` that walks the Drawflow graph and produces the `CompiledScenario` object. Must handle: spawn extraction from faction+unit chains, interaction rule construction, removal rules, aggro from relationships, validation errors.

## Verification_Strategy
```
Test_Type: unit + manual
Acceptance_Criteria:
  - "compileGraph returns valid CompiledScenario for faction→unit→stat→death chain"
  - "Missing connections produce validation errors"
  - "Relationship nodes produce correct aggro entries"
  - "Output JSON matches WS command payload format"
```
