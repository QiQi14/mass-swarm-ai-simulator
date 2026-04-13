# Multi-Agent Task Framework

A portable, CLI-driven orchestration framework that turns a single AI conversation into a coordinated team of specialized agents. Plan once, dispatch many, learn forever.

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│ 1. PLAN                                                     │
│    Planner agent decomposes a feature into atomic,          │
│    collision-free tasks with explicit contracts              │
├─────────────────────────────────────────────────────────────┤
│ 2. DISPATCH                                                 │
│    CLI generates context-rich prompts for each task,        │
│    each assigned to a new agent session                     │
├─────────────────────────────────────────────────────────────┤
│ 3. EXECUTE                                                  │
│    Executor agents implement their assigned task with       │
│    surgical precision — no scope creep                      │
├─────────────────────────────────────────────────────────────┤
│ 4. VERIFY + LEARN                                           │
│    QA agent audits against contracts, captures lessons      │
│    learned, auto-archives on completion                     │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Copy the framework to your project

```bash
# Copy the core framework
cp -r .agents/ /path/to/your/project/.agents/
cp task_tool.sh task_tool.py dispatch.sh dispatch.py /path/to/your/project/
cp .gitignore /path/to/your/project/  # Merge with existing if needed
```

### 2. Install a tech stack (optional)

Pick the stack that matches your project from `stacks/`:

```bash
# For a React project:
cp stacks/react-fsd/rules/*.md /path/to/your/project/.agents/rules/
cp stacks/react-fsd/workflows/*.md /path/to/your/project/.agents/workflows/

# For a Kotlin Multiplatform project:
cp stacks/kotlin-multiplatform/rules/*.md /path/to/your/project/.agents/rules/
cp stacks/kotlin-multiplatform/workflows/*.md /path/to/your/project/.agents/workflows/
cp -r stacks/kotlin-multiplatform/skills/* /path/to/your/project/.agents/skills/
```

### 3. Configure your project context

Edit these files in `.agents/context/`:

| File | What to fill in |
|------|----------------|
| `context/tech-stack.md` | Your language, framework, dependencies |
| `context/architecture.md` | Your folder structure and data flow |
| `context/conventions.md` | Your naming, code style, git conventions |
| `context/infrastructure.md` | Your build, deploy, CI/CD setup |

### 4. Start planning

Open an AI session (Antigravity, Cursor, Aider, etc.) and paste:

```
@planner.md

Build a user authentication feature with login, registration, and password reset.
```

The Planner will:
1. Read your project context
2. Decompose the feature into a DAG of tasks
3. Generate task briefs in `tasks_pending/`
4. Initialize state and generate dispatch prompts

### 5. Execute tasks

Open new sessions for each generated prompt:

```bash
# See what tasks are ready
./dispatch.sh tasks

# Generate a prompt for an executor
./dispatch.sh prompt executor task_01_auth_ui
```

## Project Structure

```
your-project/
├── .agents/                    # ← The framework (copy this)
│   ├── agents/                 # Agent templates
│   │   ├── planner.md          #   Lead Architect — creates the DAG (advanced tier)
│   │   ├── executor.md         #   Execution Specialist — writes code (any tier)
│   │   └── qa.md               #   QA Auditor — verifies + captures knowledge (standard+ tier)
│   ├── context.md              # Project context index (thin)
│   ├── context/                # Project context sub-files
│   │   ├── tech-stack.md       #   Language, framework, deps
│   │   ├── architecture.md     #   Folder structure, data flow
│   │   ├── conventions.md      #   Naming, code style
│   │   ├── features.md         #   Logic Ledger — completed features
│   │   └── infrastructure.md   #   Build, deploy, CI/CD
│   ├── rules/                  # Architectural constraints
│   │   ├── execution-boundary.md
│   │   ├── multi-agents-planning.md
│   │   ├── qa-audit-protocol.md
│   │   └── shared-state-and-presistence.md
│   ├── workflows/              # Step-by-step processes
│   │   ├── dag-planning.md
│   │   ├── execution-lifecycle.md
│   │   ├── knowledge-capture.md
│   │   ├── qa-certification-template.md  # QA report template
│   │   ├── qa-lifecycle.md
│   │   └── task-lifecycle.md
│   ├── skills/                 # Domain-specific capabilities
│   │   └── index.md            #   Auto-generated catalog
│   ├── knowledge/              # Agent-generated lessons learned
│   ├── history/                # Archived completed features
│   │   └── <timestamp>/tests/  #   Archived test files + INDEX.md
│   └── scripts/
│       ├── gen_skills_index.py  #   Skills catalog generator
│       └── gen_tests_index.py  #   Test archive index generator
├── task_tool.sh / .py          # Task state management CLI
├── dispatch.sh / .py           # Agent session dispatch CLI
└── .gitignore                  # Ignores runtime artifacts
```

## CLI Tools

### `task_tool.sh` — State Management

```bash
./task_tool.sh init --feature "Feature Name"   # Initialize from tasks_pending/
./task_tool.sh start <task_id>                  # Executor: Mark as IN_PROGRESS
./task_tool.sh done <task_id>                   # Executor: Ready for QA review
./task_tool.sh complete <task_id>               # QA: Verified and certified
./task_tool.sh fail <task_id> --reason "..."    # QA: Defects found
./task_tool.sh reset <task_id>                  # Reset FAILED → PENDING
./task_tool.sh status                           # Show dashboard
```

State machine: `PENDING → IN_PROGRESS → DONE → COMPLETE → auto-archive`

When QA marks the final task `COMPLETE`, auto-archives to `.agents/history/`.

### `dispatch.sh` — Prompt Generation

```bash
./dispatch.sh tasks                             # List all tasks with status
./dispatch.sh prompt planner                    # Generate planner session prompt
./dispatch.sh prompt executor <task_id>         # Generate executor session prompt
./dispatch.sh prompt qa <task_id>               # Generate QA session prompt
./dispatch.sh batch                             # Generate all ready prompts to .dispatch/
```

## Model Tiers

The Planner assigns a model tier to each task based on complexity:

| Tier | Models | Context Load | Use Case |
|------|--------|-------------|----------|
| `basic` | ~14B local models | Zero external files | Config, boilerplate, single-file |
| `standard` | Sonnet, Flash, 4o-mini | Task brief + 1-2 bindings | Multi-file, business logic |
| `advanced` | Opus, Pro, GPT-4 | Full context | Architecture, cross-layer integration |

## Adding Custom Skills

1. Create `.agents/skills/<name>/SKILL.md` with YAML frontmatter:
   ```yaml
   ---
   name: my-skill
   description: What this skill does and when to use it.
   keywords: [keyword1, keyword2, keyword3]
   ---
   ```
2. Add `resources/` and `examples/` subdirectories with reference implementations
3. Run `python3 .agents/scripts/gen_skills_index.py` to update the catalog

## Available Stacks

| Stack | Path | Description |
|-------|------|-------------|
| **Kotlin Multiplatform** | `stacks/kotlin-multiplatform/` | KMP rules, workflows, and skills (Compose, data layer, session management) |
| **React FSD** | `stacks/react-fsd/` | Feature-Sliced Design rules, workflows, and test strategy |

See each stack's README for installation instructions.

## Key Concepts

- **DAG Planning**: Features are decomposed into a Directed Acyclic Graph of tasks with explicit phase dependencies
- **Collision-Free Contracts**: Each task has a strict `Target_Files` scope — parallel agents never touch the same files
- **Context Bindings**: Tasks reference only the context, rules, workflows, and skills they need — no token waste
- **Feature Ledger**: Completed features are summarized in `context/features.md` so future agents know what exists
- **Knowledge Capture**: The QA agent documents executor mistakes, deprecated APIs, and gotchas in `.agents/knowledge/` — executors (especially basic-tier) don't have the context window for this
- **Auto-Archive**: When all tasks complete, runtime artifacts are archived to `.agents/history/`
