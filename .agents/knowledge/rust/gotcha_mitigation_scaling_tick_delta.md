# Lesson: Flat Mitigation Must Be Scaled By Tick Delta

**Category:** gotcha
**Discovered:** task_03_interaction_system_upgrade
**Severity:** medium

## Context
When calculating damage/healing delta per tick for `FlatReduction` interaction mitigation in Bevy systems.

## Problem
A static rule defines mitigation over time (per second, implicitly), but a naive equation `(base_delta.abs() - mit_value).max(0.0)` operates on `base_delta` which has already been scaled by `tick_delta` (the fraction of the second elapsed in this frame). This means the flat mitigation operates at *N times the mitigation strength* because it is subtracted at full strength on a per-frame basis against scaled down damage.

## Correct Approach
The resistance value `mit_value` MUST be scaled by the same `tick_delta` variable used to scale `base_delta` in order to represent an effective constant reduction over time rather than a per-frame reduction over time.

## Example
- ❌ What the executor did: `let abs_reduced = (base_delta.abs() - mit_value).max(0.0);`
- ✅ What it should be: `let abs_reduced = (base_delta.abs() - mit_value * tick_delta).max(0.0);`
