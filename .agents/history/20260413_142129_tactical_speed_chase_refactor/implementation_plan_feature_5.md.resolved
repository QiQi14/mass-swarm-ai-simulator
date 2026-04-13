# Feature 4: ch6 Sub-Faction Density Activation (Task 05)

## Purpose

Activate observation channel 6 (ch6) as **allied sub-faction density** — a spatial heatmap showing where the brain's split groups are positioned. This gives the model awareness of its own force distribution, enabling informed Retreat decisions (retreat TOWARD bright spots = ally support) and formation awareness.

**Currently:** ch6 is plumbed as all zeros (line 173 of `vectorizer.py`).

---

## Target Files

- `macro-brain/src/utils/vectorizer.py`

## Dependencies

- **Task 01** (only indirectly — no config deps, but sequenced after Phase 1 for safety)

## Context Bindings

- `context/training/environment.md` (channel layout)

---

## Strict Instructions

### Step 1: Replace ch6 zeros with sub-faction density data

Replace line 173-174 of `vectorizer.py`:

```python
# ── ch6: Interactable terrain overlay (plumbed, zeros) ─────────
# All zeros — activated when destructible wall mechanics exist.
```

With:

```python
# ── ch6: Allied sub-faction density (unit class / split group awareness) ─
# Shows where the brain's sub-factions are positioned.
# When Stage 5+ SplitToCoord creates sub-groups, their density appears here.
# For Stage 7+ heterogeneous units, this channel shows class distribution.
# The model learns: "retreat toward bright spots on ch6 for mutual support"
# Value: normalized count density of active sub-factions (brain excluded).
# When no sub-factions exist, ch6 = 0.0 (backward compatible with Stages 0-4).
for sf_id in active_sub_faction_ids:
    sf_key = str(sf_id)
    if sf_key in density_maps:
        _place_density(density_maps[sf_key], 6, accumulate=True)
```

### Step 2: Update channel layout docstring

Update the module docstring (lines 5-20) to reflect ch6 activation:

```python
"""State vectorization: JSON snapshot → numpy observation dict.

8-channel fixed 50×50 tensor + 12-dim summary vector.

Channel Layout (v5.0):
  🟦 Force Picture:
    ch0: all friendly count density (brain + sub-factions merged)
    ch1: all enemy count density (ALL enemies merged, LKP-processed under fog)
    ch2: all friendly ECP density (brain + sub-factions merged)
    ch3: all enemy ECP density (ALL enemies merged, LKP-processed under fog)
  🟩 Environment:
    ch4: terrain cost (base + zone modifier effects, 0=pass, 1=wall; padding=1.0)
    ch5: fog awareness (merged 3-level: 0.0=unknown, 0.5=explored, 1.0=visible)
  🟨 Tactical:
    ch6: allied sub-faction density (split groups / unit class positions)
    ch7: system objective signal (intel ping location + intensity)

For maps smaller than 50×50, the active arena is centered in the tensor.
Padding zones have: density=0, terrain=1(wall), fog=1(explored/visible).
"""
```

> [!IMPORTANT]
> **ch6 is a SUBSET of ch0**, not a duplicate. ch0 contains ALL friendly density (brain + sub-factions merged). ch6 contains ONLY sub-faction density (excluding the main brain body). This means:
> - ch0 = full allied picture (where are ALL my units?)
> - ch6 = split group picture (where are my detached groups?)
> - ch0 - ch6 ≈ main body (where is my primary force?)
> 
> The CNN can learn this relationship to coordinate main body + flanks.

### Step 3: Update context documentation

Update `.agents/context/training/environment.md` to reflect the ch6 activation.

---

## Backward Compatibility

- **Stages 0-4:** No sub-factions exist (SplitToCoord unlocks at Stage 5), so `active_sub_faction_ids` = `[]` and ch6 remains all zeros. ✅
- **Stage 4 Scout:** Scout creates a sub-faction. ch6 will now show the scout group's position — this is actually beneficial! The model can see where its scout is on ch6 and retreat to merge.
- **Existing CNN weights:** ch6 has been zeros throughout training. Activating it mid-curriculum won't confuse the model because:
  1. Fresh Stage 5 starts with new randomly initialized weights (no transfer from Stage 4)
  2. The model learns ch6 meaning from scratch at Stage 5

---

## Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: unit
  Test_Stack: Python / pytest
  Acceptance_Criteria:
    - "ch6 is all zeros when active_sub_faction_ids=[]"
    - "ch6 shows sub-faction density when active_sub_faction_ids=[100]"
    - "ch6 accumulates density from multiple sub-factions"
    - "ch6 does NOT include the main brain faction density"
    - "ch0 = brain + sub-factions, ch6 = sub-factions only (subset relationship)"
    - "Existing tests for ch0-ch5 continue passing"
  Suggested_Test_Commands:
    - "cd macro-brain && .venv/bin/python -m pytest tests/test_vectorizer.py -v"
```
