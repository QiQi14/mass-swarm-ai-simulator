# Lesson: Bevy 0.18 Test World Querying Requires Mutable Access

**Category:** gotcha
**Discovered:** task_02_ecs_components
**Severity:** high

## Context
When writing unit tests for Bevy systems that inspect component state after an update, it's common to instantiate an `App` and query its `World`.

## Problem
In earlier versions of Bevy, you could call `.query()` on an immutable reference to the `World` (`app.world().query()`). In Bevy 0.18, `query()` requires mutable access to the world to construct the query state, leading to a test compilation error `cannot borrow as mutable`.

## Correct Approach
Always use `app.world_mut().query::<...>()` when querying the world within a test.

## Example
- ❌ What the executor did: `let mut query = app.world().query::<&EntityId>();`
- ✅ What it should be: `let mut query = app.world_mut().query::<&EntityId>();`
