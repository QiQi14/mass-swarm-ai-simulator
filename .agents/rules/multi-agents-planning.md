---
trigger: model_decision
description: Only use when user request planning new feature, refactor or complex task
---

# RULE: MULTI-AGENT COLLISION AVOIDANCE

## 1. Collision Avoidance (Strict File Scoping)
- **Rule of Exclusivity:** Two parallel tasks MUST NEVER be assigned to modify the same file. 
- If multiple components need to be registered in a single shared file (e.g., a central Router, a Dependency Injection module, or a Root Store), you must extract this wiring step into a separate, final "Integration Task" that runs sequentially AFTER all parallel tasks complete.

## 2. Contract-First Development (The Handshake Protocol)
- Before parallel agents can build interacting layers (e.g., a Frontend agent and a Backend agent), they must share a common truth.
- For every interacting boundary, you MUST explicitly define the Data Models (DTOs), Function Signatures, or API Endpoints in your plan BEFORE assigning the tasks.
- Sub-agents will strictly implement against these pre-defined contracts.

## 3. Agent Isolation
- Never assume sub-agents can read each other's minds or share real-time memory. They are completely isolated during execution.
- All inter-agent communication happens through files on disk: task briefs, changelogs, and contracts in `implementation_plan.md`.