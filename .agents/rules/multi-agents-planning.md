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

## 4. Human Code is Concept, Not Truth

> **"Humans are incredible at concepting. They are lazy at details."**

When a human provides source code (inline, in messages, or in reference files):

- **ADOPT the architectural idea** — the pattern, the algorithm choice, the data flow, the design rationale. These are almost always correct and deeply considered.
- **DO NOT blindly copy-paste** — the human's code may contain typos, wrong variable names, incorrect API usage, missing edge cases, or outdated syntax for the target framework version.
- **INDEPENDENTLY VERIFY** every line against:
  1. The project's actual Cargo.toml / package.json dependencies and versions
  2. The framework's real API (e.g., Bevy 0.18 method signatures)
  3. Rust/TypeScript compiler rules and borrow semantics
  4. Existing project contracts in `implementation_plan.md`
  5. Any `.agents/knowledge/` lessons from prior sessions
- **If the concept is sound but the code is wrong**, fix the implementation while preserving the architectural intent. Document what was corrected and why.
- **If the concept itself is flawed** (e.g., suggests an O(N²) approach when O(N log N) exists), flag it for architectural review before implementing.