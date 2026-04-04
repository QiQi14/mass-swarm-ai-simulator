# Lesson: Bevy 0.18 Headless Feature Flags

**Category:** deprecation
**Discovered:** task_01_project_scaffold
**Severity:** medium

## Context
When bootstrapping a Bevy 0.18 headless project via Cargo under `default-features = false`.

## Problem
The task prompt commanded the executor to add Bevy 0.18 with `features = ["bevy_app", "bevy_ecs"]`. However, in `bevy` 0.18, cargo rejects these features: `error: unrecognized features for crate bevy: bevy_app, bevy_ecs`. The architecture of the `bevy` crate in 0.18 does not require explicit feature flags for basic ECS/App functionality when standard default features are disabled; these components are included.

## Correct Approach
For a headless Bevy 0.18 instance, simply use `default-features = false` with no additional `features` array unless specifically importing explicit new modular features (like `bevy_log`).

## Example
- ❌ What the executor did: `bevy = { version = "0.18", default-features = false, features = ["bevy_app", "bevy_ecs"] }`
- ✅ What it should be: `bevy = { version = "0.18", default-features = false }`
