# Context Organization Plan

Re-organizing the `.agents/context/` directory to prevent context bloat and allow agents to perform fast-scans of domain knowledge using index files.

## User Review Required

- Please review the proposed folder structure and naming below.
- Do these category names (`engine`, `training`, `project`) align with your vision for fast-scanning?
- The agent prompt workflows and `Context_Bindings` guidelines in `.agents/context.md` will be updated to point to the new paths.

## Proposed Structure

We will transition the 8 flat files into 3 domain-specific folders. To prevent context window bloat for smaller agents, large files like `engine-mechanics.md` and `training-curriculum.md` will be split into smaller, topic-specific files. Each folder will contain an `index.md` listing its contents to enable fast scanning.

### 1. `engine/` (Core Simulation & Architecture)
- `[NEW]` `.agents/context/engine/index.md` - Fast scan index of engine domains.
- `[NEW]` `.agents/context/engine/combat.md` - Entity Model, Combat System, Buffs, and Removal. (Split from `engine-mechanics.md`)
- `[NEW]` `.agents/context/engine/navigation.md` - Movement, Directives, Spatial Grid. (Split from `engine-mechanics.md`)
- `[NEW]` `.agents/context/engine/terrain.md` - Terrain, Zones, Fog of War, ECP. (Split from `engine-mechanics.md`)
- `[NEW]` `.agents/context/engine/architecture.md` (Moved from `architecture.md`)
- `[NEW]` `.agents/context/engine/protocol-zmq.md` - (Split from `ipc-protocol.md`)
- `[NEW]` `.agents/context/engine/protocol-state.md` - Observation packing and payloads. (Split from `ipc-protocol.md`)
- `[DELETE]` `engine-mechanics.md`, `architecture.md`, `ipc-protocol.md`

### 2. `training/` (RL, Bots, Strategy)
- `[NEW]` `.agents/context/training/index.md` - Fast scan index of training pipelines.
- `[NEW]` `.agents/context/training/overview.md` - RL principles, Stage Summary, Key Files. (Split from `training-curriculum.md`)
- `[NEW]` `.agents/context/training/stages.md` - Stage Details and Episode Flow. (Split from `training-curriculum.md`)
- `[NEW]` `.agents/context/training/environment.md` - Observation Space and Reward Structure. (Split from `training-curriculum.md`)
- `[NEW]` `.agents/context/training/bots.md` - Bot Behavior System. (Split from `training-curriculum.md`)
- `[DELETE]` `training-curriculum.md`

### 3. `project/` (Standards & Ledgers)
- `[NEW]` `.agents/context/project/index.md` - Fast scan index of conventions and stacks.
- `[NEW]` `.agents/context/project/conventions.md` (Moved from `conventions.md`)
- `[NEW]` `.agents/context/project/tech-stack.md` (Moved from `tech-stack.md`)
- `[NEW]` `.agents/context/project/infrastructure.md` (Moved from `infrastructure.md`)
- `[NEW]` `.agents/context/project/features.md` (Moved from `features.md`)
- `[DELETE]` `conventions.md`, `tech-stack.md`, `infrastructure.md`, `features.md`

### 4. Updating Workflow References
#### `[MODIFY]` `.agents/context.md`
- Update the Quick Reference table and `Context_Bindings` examples to point to the new folder paths.

#### `[MODIFY]` `.agents/workflows/planner.md`
- Update the step reading `context/features.md` to `context/project/features.md`.

#### `[MODIFY]` `.agents/workflows/strategist.md`
- Update mandatory reads from `context/engine-mechanics.md` to `context/engine/mechanics.md`.

#### `[MODIFY]` `.agents/rules/shared-state-and-presistence.md`
- Update references to `engine-mechanics.md` and `training-curriculum.md`.

#### `[MODIFY]` `.agents/workflows/qa.md`
- No direct file path updates needed, but operates on updated `Context_Bindings`.

#### `[MODIFY]` `.agents/workflows/task-lifecycle.md`
- Update reference to `context/features.md` to `context/project/features.md`.

## Open Questions

- Is it okay to rename the files by dropping prefixes where redundant (e.g. `engine-mechanics.md` -> `engine/mechanics.md`)?

## Verification Plan

- Check all updated workflow files and `context.md` to ensure no broken `.agents/context/` references remain.
- The new `index.md` files will contain summary paragraphs allowing smaller LLMs and sub-agents to scan before deciding what deep-dive file to open.
