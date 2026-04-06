# Lesson: Terrain Payload Format Mismatch Between Python Generator and Rust Receiver

**Category:** gotcha
**Discovered:** task_07 + task_08 QA audit (2026-04-06)
**Severity:** high — will cause runtime deserialization failure

## Context
Task 07 defines `TerrainPayload` in Rust (`zmq_protocol.rs`) with fields `hard_costs`, `soft_costs`, `width`, `height`, `cell_size`. Task 08 implements `generate_random_terrain()` in Python which returns `{"width", "height", "costs"}`.

## Problem
The Python terrain generator returns a dict with a single `"costs"` key, but the Rust `TerrainPayload` expects two separate cost arrays (`hard_costs` and `soft_costs`) plus a `cell_size` field. When the `SwarmEnv.reset()` sends `ResetEnvironment` with terrain data, Rust will fail to deserialize the payload because:
1. Field `"costs"` does not match `"hard_costs"` or `"soft_costs"`
2. `"soft_costs"` is entirely absent
3. `"cell_size"` is absent

## Correct Approach
During Task 10 (Integration Smoke Test), the Python terrain generator output must be aligned with the Rust `TerrainPayload` contract:

```python
return {
    "hard_costs": flat_costs,
    "soft_costs": [100] * len(flat_costs),  # Default full speed
    "width": width,
    "height": height,
    "cell_size": 20.0,  # Must match Rust TerrainGrid cell_size
}
```

## Example
- ❌ What the executor did: `return {"width": w, "height": h, "costs": flat_costs}`
- ✅ What it should be: `return {"hard_costs": flat_costs, "soft_costs": [100]*len(flat_costs), "width": w, "height": h, "cell_size": 20.0}`
