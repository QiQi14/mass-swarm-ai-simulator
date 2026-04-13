# Task 09: Custom Feature Extractor & Train Script - Changelog

## Touched Files
- `macro-brain/src/models/__init__.py` (NEW)
- `macro-brain/src/models/feature_extractor.py` (NEW)
- `macro-brain/src/training/train.py` (MODIFIED)

## Contract Fulfillment
- Implemented `TacticalExtractor` (CNN + MLP) extending `BaseFeaturesExtractor`.
- Configured Stacked grids processing using `torch.stack` with 8 channels outputting a 128-dim tensor.
- Configured 12-dim summary processing through MLP outputting a 64-dim tensor.
- Combined both embeddings into a single features tensor with size defined by `features_dim` (256 default).
- Updated `make_env`, `policy_kwargs`, `MaskablePPO` policy, and `EpisodeLogCallback` in the `train.py` script.

## Deviations/Notes
- The brief's Verification Strategy suggested running `pytest tests/test_feature_extractor.py`, but this file did not exist and was not in the `Target_Files`. To strictly follow `Rule 1: Scope Isolation`, I did not create it.
- A quick scratch script `scratch_test.py` was executed temporarily to verify `TacticalExtractor` correctly processed the dictionary inputs and outputted a shape of `(B, 256)`. It passed successfully. There are no actual code deviations from the instructions.
