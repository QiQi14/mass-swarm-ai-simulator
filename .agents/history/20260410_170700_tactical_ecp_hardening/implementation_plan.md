# Feature Extractor Hardening: Effective Combat Power + Summary Cleanup

## Background

The CNN's `ch7` (threat density) is currently a useless mirror of `ch1`. The summary vector leaks faction-specific information through `summary[6]` (trap_count by faction ID) and `summary[7]` (target_count by faction ID). These are artificial shortcuts that won't generalize to real-play scenarios.

**Goal:** Give the CNN the information it needs to evaluate **threat level** per spatial region, enabling decisions like "can I brute-force through both groups?" vs "I need to pick targets carefully."

### Key Metric: Effective Combat Power (ECP)

```
ECP per cell = sum(entity_HP × entity_damage_multiplier) / normalization
```

| Scenario | Count | HP | DPS mult | ECP | CNN Interpretation |
|----------|-------|----|----------|-----|--------------------|
| Tanker blob | 10 | 100 | 1.0 | 1000 | Bright ch7, dim ch1 → tough bait |
| DPS blob | 40 | 20 | 1.0 | 800 | Dim ch7, bright ch1 → squishy target |
| Debuffed blob | 50 | 25 | 0.25 | 312 | Very dim ch7 → weakened, attack now! |
| Own swarm | 50 | 100 | 1.0 | 5000 | Very bright ch0 → I outpower everything, brute force! |

The CNN compares ch0 (own ECP) vs ch7 (enemy ECP) to answer: *"Am I strong enough to steamroll, or do I need to be tactical?"*

---

## Proposed Changes

### Rust: Micro-Core

---

#### [MODIFY] [state_vectorizer.rs](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/micro-core/src/systems/state_vectorizer.rs)

Add `build_ecp_density_maps()` — Effective Combat Power per cell = `sum(entity_hp × damage_mult)`.

```rust
/// Builds Effective Combat Power (ECP) density heatmaps.
///
/// Each cell value = sum(entity_hp × entity_damage_mult) / (max_density × max_hp × max_dmg_mult),
/// clamped to [0.0, 1.0].
///
/// ECP captures both survivability (HP) and damage output (buff multiplier).
/// Tankers (high HP, low DPS) produce moderate ECP.
/// Glass cannons (low HP, high DPS) produce moderate ECP.
/// Debuffed units (low HP × 0.25 mult) produce very low ECP.
pub fn build_ecp_density_maps(
    entities: &[(f32, f32, u32, f32, f32)],  // (x, y, faction_id, hp, damage_mult)
    grid_w: u32, grid_h: u32,
    cell_size: f32,
    max_ecp_per_cell: f32,                   // = max_density × max_hp × max_dmg_mult
) -> HashMap<u32, Vec<f32>>
```

Tests:
- `test_ecp_density_single_entity` — one entity at 80 HP × 1.0 mult
- `test_ecp_density_tanker_vs_glass_cannon` — same count, different HP/DPS
- `test_ecp_density_debuffed_units` — 0.25× mult produces lower ECP
- `test_ecp_density_normalization` — clamps to 1.0

---

#### [MODIFY] [types.rs](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/micro-core/src/bridges/zmq_protocol/types.rs)

Add `ecp_density_maps` field to `StateSnapshot`:

```rust
/// Effective Combat Power density maps — per-faction, per-cell.
/// ECP = sum(entity_hp × entity_damage_mult) per cell, normalized.
#[serde(default)]
pub ecp_density_maps: std::collections::HashMap<u32, Vec<f32>>,
```

Also update the `Default` impl and the serialization roundtrip test.

---

#### [MODIFY] [snapshot.rs](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/micro-core/src/bridges/zmq_bridge/snapshot.rs)

During the existing entity iteration loop, collect `(x, y, faction_id, hp, damage_mult)` tuples:
- `hp` = `stat_block.0[0]`
- `damage_mult` = `combat_buffs.get_multiplier(faction.0, entity_id.id, combat_damage_stat)` (defaults to 1.0 if no buff)

Call `build_ecp_density_maps()` and add result to the snapshot.

---

### Python: Macro-Brain

---

#### [MODIFY] [vectorizer.py](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/macro-brain/src/utils/vectorizer.py)

**ch7 overhaul:** Replace the mirror copy with a unified **Effective Combat Power** channel.

```python
# ── ch7: Effective Combat Power (ECP) density ──────────
# Merge all enemy ecp_density_maps into a single channel.
# CNN compares ch1 (where are enemies?) vs ch7 (how dangerous are they?)
# ch0 (own density) vs ch7 (enemy ECP) → "can I brute-force?"
ecp_density_maps = snapshot.get("ecp_density_maps", {})
for ef in enemy_factions:
    key = str(ef)
    if key in ecp_density_maps:
        flat = ecp_density_maps[key]
        if flat and len(flat) == active_size:
            arr = np.array(flat, dtype=np.float32).reshape(active_grid_h, active_grid_w)
            channels[7][pad_y:pad_y+active_grid_h, pad_x:pad_x+active_grid_w] += arr

if fog_enabled and lkp_buffer is not None:
    channels[7] = lkp_buffer.update(1, channels[7], channels[6])
```

> [!IMPORTANT]
> This requires LKP buffer to go back to `num_enemy_channels=2` — index 0 for raw density (ch1), index 1 for ECP density (ch7).

**Summary vector cleanup:** Replace faction-specific cheats with generalizable metrics.

| Index | Before (cheat) | After (generalizable) |
|-------|---------------|----------------------|
| 6 | `trap_count / max_entities` | `total_enemy_hp_pool` — `sum(count * avg_hp) / (max_entities * 100)` |
| 7 | `target_count / max_entities` | `hp_advantage` — `own_pool / (own_pool + enemy_pool)` |

---

#### [MODIFY] [spaces.py](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/macro-brain/src/env/spaces.py)

Update channel docstrings:
- `ch7: HP-weighted enemy density (toughness heatmap)`

---

#### [MODIFY] [swarm_env.py](file:///Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/macro-brain/src/env/swarm_env.py)

Restore LKP buffer to `num_enemy_channels=2` (index 0 = raw density ch1, index 1 = HP density ch7).

---

### Tests

---

#### Rust Tests
- `test_ecp_density_single_entity` — one entity at 80 HP × 1.0 mult
- `test_ecp_density_tanker_vs_glass_cannon` — same count, different ECP = HP × DPS
- `test_ecp_density_debuffed_units` — 0.25× mult produces dim ECP
- `test_ecp_density_normalization` — clamps to 1.0
- `test_snapshot_includes_ecp_density_maps` — snapshot roundtrip includes the new field

#### Python Tests
- `test_ch7_ecp_density` — ch7 reflects ECP (HP × damage_mult)
- `test_ch7_differs_from_ch1` — tanker blob brighter in ch7 vs ch1
- `test_ch7_debuffed_is_dim` — debuffed units appear dim in ch7
- `test_summary_no_faction_cheats` — summary[6] and [7] are faction-agnostic
- `test_lkp_two_channels` — LKP correctly tracks both raw density and ECP

---

## Verification Plan

### Automated Tests
```bash
# Rust
cd micro-core && cargo test state_vectorizer
cd micro-core && cargo test snapshot

# Python
source macro-brain/.venv/bin/activate
pytest macro-brain/tests/test_vectorizer.py -v
pytest macro-brain/tests/test_lkp_buffer.py -v
```

### Manual Verification
After tests pass, launch a 10-episode training run to verify no ZMQ protocol breakage.
