---
description: The DAG Planning Process
---

# WORKFLOW: DAG PLANNING (INDEX-NODE STRATEGY)

When instructed to plan a feature, follow these 5 sequential steps:

## Step 1: Feature Deconstruction & Boundary Identification

Analyze the request and break down the feature into isolated, atomic tasks based on architectural boundaries (e.g., UI Components, State Management, Data/Local Storage, Network).

- **The Atomic Definition:** A task is ONLY considered "atomic" if it operates within a SINGLE technical domain (e.g., ONLY UI, ONLY Database, or ONLY Network).
- **The Context Density Limit:** Evaluate the required `Context_Bindings` for each drafted task. If a single task requires loading more than 2 distinct architectural rule sets (e.g., it needs both `/rule-compose` and `/rule-data-layer`), the task is too complex and violates separation of concerns. You MUST split it into smaller tasks.
- **Example:** Do not create a task like "Build Login UI and save user to database". Instead, split it into:
  - Task A (Domain: Data): "Create AuthRepository and LocalDataSource" -> Binds to `rules/data-layer`.
  - Task B (Domain: UI): "Create Login Screen and ViewModel" -> Binds to `rules/kotlin-compose` and waits for Task A.

## Step 2: Contract Drafting (The Handshake Protocol)

Before parallel agents can build interacting layers, they must share a common truth. For every interacting boundary between tasks, you MUST explicitly define the exact data structures and interfaces.

- Write the complete and exact type definitions, interface signatures, and data payloads.
- If a task involves state management, explicitly list all state variables, events, and action payloads.
- Sub-agents will strictly implement against these pre-defined contracts.

## Step 3: Execution Graph Creation (DAG Formulation)

Group the atomic tasks into a Directed Acyclic Graph (DAG) of execution phases to avoid file collision:

- **Phase 1 (Parallel):** Tasks with zero dependencies on each other (e.g., pure UI components, database migrations, base interfaces).
- **Phase 2+ (Parallel/Sequential):** Tasks that depend on Phase 1 or the contracts defined in Step 2.
- **Final Phase (Integration):** A strictly sequential task that imports all created modules and wires them together in shared registry files (e.g., main router, root dependency injection container).

## Step 4: Output Generation & File Splitting

To prevent output truncation and ensure maximum detail, DO NOT attempt to write the entire DAG and all task instructions into a single file. You MUST split your output:

**1. The Index File (`implementation_plan.md`) — Draft Phase:**
- Create this file as an **Antigravity artifact** at `<appDataDir>/brain/<conversation-id>/implementation_plan.md` with `RequestFeedback: true`.
- This file must contain the high-level architecture, the DAG execution phases, the shared contracts (from Step 2), and the dependency mapping between tasks.
- The user will review, ask questions, and request changes via the artifact feedback loop.
- **Do NOT create task files or run `task_tool.sh` until the user explicitly approves the plan.**

**1b. Plan Promotion (After User Approval):**
- Once the user approves the implementation plan, **copy** the finalized artifact to the project ROOT: `implementation_plan.md`.
- Only then proceed to generate task files and dispatch.

- Create a directory: `tasks_pending/` (if it does not exist).
- For EACH task identified in your DAG, create a separate, heavily detailed Markdown file inside this directory (e.g., `tasks_pending/task_01_auth_ui.md`).
- Each node file MUST contain:
  - `Task_ID` and `Execution_Phase`.
  - `Model_Tier`: **basic**, **standard**, or **advanced** (see below).
  - `Target_Files`: Exact list of files this specific sub-agent is allowed to create or modify.
  - `Dependencies`: Required contracts or outputs from previous phases.
  - `Context_Bindings`: Explicitly list the exact rules/workflows the Executor must load.
  - `Strict_Instructions`: Step-by-step, exhaustive coding instructions. No placeholders.
  - `Verification_Strategy`: **REQUIRED.** Defines how QA will verify this task (see below).

**Verification Strategy (Required per Task):**

The Planner MUST define a `Verification_Strategy` for every task. This tells the QA agent *what* to test and *how*:

```markdown
Verification_Strategy:
  Test_Type: [unit | integration | e2e | manual_steps]
  Test_Stack: [reference to testing framework from stacks/ — REQUIRED]
  Acceptance_Criteria:
    - "Function X returns correct output for input Y"
    - "Empty input returns empty array without throwing"
  Suggested_Test_Commands: (optional hints for QA)
    - "npx vitest run src/features/my-feature"
  Manual_Steps: (for UI/complex tasks where automation is insufficient)
    - "Open config panel → click button → verify result"
    - "Use browser control to navigate to /page and verify rendering"
```

> **Rule:** The `Test_Stack` MUST reference the project's tech stack (from `stacks/`). If no relevant stack exists, the Planner MUST stop and ask the user which testing framework/approach to use. Never guess.

**Test Task Splitting (Planner's Responsibility):**
- For **simple tasks**: QA handles test authoring + execution + certification in one session.
- For **complex features**: The Planner SHOULD create a dedicated test task (assigned to a `standard` or `advanced` tier executor) that writes the test suite. QA then runs the tests + certifies.
- The Planner decides the split at planning time based on implementation complexity.

**Model Tier Assignment:**

| Tier | Model Size | Use When |
|------|-----------|----------|
| `basic` | ~14B local | Single-file tasks, config changes, simple CRUD, boilerplate. Task brief must be fully self-contained — agent skips external file reading. |
| `standard` | Mid-tier (Sonnet, Flash, 4o-mini) | Multi-file tasks, business logic, state management. Agent reads task brief + 1-2 external context files. |
| `advanced` | Top-tier (Opus, Pro, GPT-4) | Architectural decisions, complex state, cross-layer integration. Agent reads full context. |

For `basic` tier: write MORE detailed `Strict_Instructions` — include exact imports, full function signatures, and literal code where possible. The task brief IS the complete instruction.

## Step 5: Execution Handover

Do not attempt to execute the code yourself. Once the index file and all task node files are written to the file system, halt your operation. The agent template will handle state initialization (`task_tool.sh`) and dispatch (`dispatch.sh`).