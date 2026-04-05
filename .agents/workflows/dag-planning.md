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

To prevent output truncation and ensure maximum detail, you MUST split your output across multiple files.

### 4a. The Implementation Plan — Draft Phase

Create the plan as an **Antigravity artifact** at `<appDataDir>/brain/<conversation-id>/implementation_plan.md` with `RequestFeedback: true`.

**Token Budget Rule:** If the plan exceeds ~400 lines, you MUST split it:

| File | Contains | Max Lines |
|------|----------|-----------|
| `implementation_plan.md` | Overview, core principles, inter-layer architecture, DAG phases, file summary, verification plan | ~300 |
| `implementation_plan_feature_[N].md` | Detailed contracts + strict instructions for one feature/component | ~300 each |

**Index file (`implementation_plan.md`) MUST contain:**
- High-level architecture and design decisions
- The DAG execution phases with dependency graph
- Shared contracts that cross feature boundaries (e.g., WS protocol types)
- File summary table (all files across all features)
- Verification plan
- A `## Feature Details` section listing links to detail files:
  ```markdown
  ## Feature Details
  - [Feature 1: Mass Spawn](./implementation_plan_feature_1.md)
  - [Feature 2: Fog of War](./implementation_plan_feature_2.md)
  ```

**Detail files (`implementation_plan_feature_[N].md`) contain:**
- Full code contracts (struct definitions, function signatures, algorithm pseudocode)
- Strict per-file change instructions
- Anti-patterns and gotchas specific to that feature

> **Why split?** A 780-line plan consumed during the planning phase's review loop
> is fine for the Planner agent, but Executor agents loading it via `Context_Bindings`
> often hit token limits. Splitting lets each executor load ONLY the feature detail
> file relevant to their task.

**Small plans (<400 lines):** Keep everything in a single `implementation_plan.md`. Don't split unnecessarily.

- The user will review, ask questions, and request changes via the artifact feedback loop.
- **Do NOT create task files or run `task_tool.sh` until the user explicitly approves the plan.**

### 4b. Plan Promotion (After User Approval)

- Once the user approves the implementation plan, **copy** ALL plan files (index + detail files) to the project ROOT.
- Only then proceed to generate task files and dispatch.

### 4c. Task File Generation

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

| Tier | Models | Max Context | Use When |
|------|--------|-------------|----------|
| `basic` | Qwen 3.6 14B, Gemma 3 27B, Nemotron Nano | ≤ 8K tokens | Single-file tasks, config changes, simple CRUD, boilerplate. Task brief must be fully self-contained — agent skips external file reading. |
| `standard` | Gemini Flash, Claude Sonnet 4.6, GPT-OSS 120B | ≤ 32K tokens | Multi-file tasks, business logic, state management. Agent reads task brief + 1-2 external context files. |
| `advanced` | Gemini Pro, Claude Opus 4.6 | > 32K tokens | Architectural decisions, complex state, cross-layer integration. Agent reads full context. |

For `basic` tier: write MORE detailed `Strict_Instructions` — include exact imports, full function signatures, and literal code where possible. The task brief IS the complete instruction.

## Step 4d: Token Budget Verification

After generating all task files, run the token estimation script to verify tier assignments are correct:

```bash
python3 .agents/scripts/estimate_tokens.py --verbose
```

Review the output:
- **✔ OK**: The assigned tier can handle the estimated context
- **⚠ UPGRADE**: The estimated tokens exceed the tier's budget — upgrade `Model_Tier` in the task brief
- **↓ DOWNGRADE**: The context is well below the tier's capacity — consider downgrading to save budget

If adjustments are needed:
1. Edit the `Model_Tier` field in the flagged `tasks_pending/task_*.md` files
2. Re-run the script to confirm all tasks are within budget

> **Note:** This step is advisory. The Planner and developer make the final tier decision.

## Step 5: Execution Handover

Do not attempt to execute the code yourself. Once the index file and all task node files are written to the file system, halt your operation. The agent template will handle state initialization (`task_tool.sh`) and dispatch (`dispatch.sh`).