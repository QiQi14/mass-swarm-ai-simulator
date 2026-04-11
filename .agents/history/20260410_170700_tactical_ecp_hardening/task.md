# Task Checklist: Feature Extractor Hardening

## Phase 1: Rust Layer (Micro-Core)
- [x] Implement `build_ecp_density_maps` in `state_vectorizer.rs`
- [x] Add `test_ecp_density_single_entity`
- [x] Add `test_ecp_density_tanker_vs_glass_cannon`
- [x] Add `test_ecp_density_debuffed_units`
- [x] Add `test_ecp_density_normalization`
- [x] Update `types.rs` `StateSnapshot` with `ecp_density_maps` field
- [x] Update `snapshot.rs` to extract HP and damage mult, and compute ECP density maps
- [x] Run Rust tests (`cargo test`) to ensure everything passes

## Phase 2: Python Layer (Macro-Brain)
- [x] Update `vectorizer.py` to use `ecp_density_maps` for ch7
- [x] Update `vectorizer.py` summary logic (replace faction counts with HP totals/advantage)
- [x] Reconfigure LKP buffer to 2 channels in `swarm_env.py` and `vectorizer.py`
- [x] Update `test_vectorizer.py`
- [x] Update `test_lkp_buffer.py`
- [x] Update `spaces.py` docstrings
- [x] Run Python tests (`pytest`)

## Phase 3: Integration
- [x] Launch a short training run to verify no ZMQ protocol crashes
