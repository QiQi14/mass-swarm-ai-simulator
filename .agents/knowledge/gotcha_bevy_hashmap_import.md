# Lesson: Use bevy::utils::HashMap instead of std or bevy::platform

**Category:** gotcha
**Discovered:** task_10_faction_visibility
**Severity:** medium

## Context
When implementing associative collections (e.g., Maps and Sets) within Bevy structures or resources.

## Problem
The Executor attempted to import `bevy::platform::collections::HashMap` as dictated by a potentially outdated or inaccurate specification. When that failed to resolve, the Executor fell back to the standard library's `std::collections::HashMap`. This can lead to non-deterministic serialization or iteration orders which is highly undesirable in simulation environments.

## Correct Approach
In Bevy, the deterministic and highly performant alternative to the standard library HashMap is located at `bevy::utils::HashMap`. You should always prefer this wrapper for cross-platform compatibility and performance reasons in Bevy systems unless explicitly barred.

## Example
- ❌ What the executor did: `use std::collections::HashMap;`
- ✅ What it should be: `use bevy::utils::HashMap;`
