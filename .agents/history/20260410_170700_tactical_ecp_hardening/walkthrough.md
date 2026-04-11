# Walkthrough: Effective Combat Power (ECP) Refactor

I have completed the refactoring of the observation pipeline to use **Effective Combat Power (ECP)**. This replaces the old raw density tracking and gives the CNN the exact spatial information it needs to evaluate "brute-force vs tactical" multi-group scenarios.

## What Changed

### 1. The ECP Metric (Rust Layer)
I added `build_ecp_density_maps` in the `micro-core` `state_vectorizer.rs`. It calculates ECP per cell as:
```rust
ecp = sum(entity_hp * damage_multiplier)
```
- It pulls the `damage_multiplier` directly from the `FactionBuffs` system using the configured `combat_damage_stat`.
- This ensures that debuffed units (e.g. 0.25x damage) appear "dimmer" in the threat heatmap, accurately representing their reduced threat level.

### 2. The Threat Heatmap (Python Layer)
The Python `vectorizer.py` now maps the unified `ecp_density_maps` to `ch7` (Threat Density) instead of merely mirroring `ch1` (Raw Enemy Count).

| Scenario | `ch1` (Count) | `ch7` (ECP) | AI Interpretation |
|----------|---------------|-------------|-------------------|
| **Tankers** | Dim (few) | Bright (high HP) | High survivability, low raw count → **Avoid pulling into traps** |
| **Squishies** | Bright (many) | Dim (low HP/DPS) | Easy kills → **Attack!** |
| **Debuffed** | Bright | Very Dim | Severely weakened → **Go for the kill!** |

> [!TIP]
> The MaskablePPO CNN can now easily determine if it should brute-force a group by matching its own ECP brightness (`ch0`) against the enemy's ECP brightness (`ch7`). If `ch0 >> ch7`, it learns to just attack.

### 3. Summary Vector Cleanup
I removed the target-cheating faction counters from the 12-dim summary vector. `summary[6]` and `summary[7]` no longer leak faction IDs. Instead, they provide total normalized HP:
- `summary[6]`: Total Own HP normalized
- `summary[7]`: Total Enemy HP normalized

### 4. LKP integration
`LKPBuffer` was restored to `num_enemy_channels=2`. The fog of war tracking now persists ghost trails for **both** raw count density (`ch1`) and ECP density (`ch7`). The AI will remember roughly how strong a hidden group was, not just that "a group was there".

## Verification
- ✅ Rust memory and spatial grids tested natively (`cargo test`). Tests verified the clamping normalization and ECP debuff calculations.
- ✅ Python tests refactored for new metrics and channels (`poetry run pytest`).
- ✅ A simulated training run (`2048 timesteps`) successfully executed with the new multi-channel vectorization, showing successful RL tracking and ZMQ pipeline stability!
