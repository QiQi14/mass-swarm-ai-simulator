# Task 11: Integration Testing

```yaml
Task_ID: task_11_integration_tests
Execution_Phase: 6
Model_Tier: advanced
Dependencies:
  - task_06_swarm_env_refactor
  - task_07_curriculum_stages
  - task_08_training_callbacks
  - task_09_feature_extractor_train
  - task_10_game_profile
Target_Files:
  - macro-brain/tests/test_tactical_integration.py  # NEW FILE
  - macro-brain/tests/test_feature_extractor.py  # NEW FILE
  - macro-brain/tests/test_lkp_buffer.py  # NEW FILE
Context_Bindings:
  - context/architecture
  - context/conventions
  - context/ipc-protocol
```

## Objective

Write comprehensive integration tests that validate the full tactical training pipeline: observation shapes, action masking, coordinate decoding, LKP buffer, CNN forward pass, and reward gradients.

## Strict Instructions

### 1. Create `test_lkp_buffer.py`

Tests for `LKPBuffer`:

```python
def test_lkp_overwrites_visible_cells():
    """Visible cells get ground truth density."""

def test_lkp_decays_hidden_cells():
    """Hidden cells decay by decay_rate per update."""

def test_lkp_never_negative():
    """Decayed density never drops below 0."""

def test_lkp_reset_zeros_memory():
    """reset() clears all stored density."""

def test_lkp_mixed_visible_hidden():
    """Partial visibility: some cells overwrite, others decay."""
```

### 2. Create `test_feature_extractor.py`

Tests for `TacticalExtractor`:

```python
def test_extractor_forward_shape():
    """Forward pass with dummy Dict obs produces (B, 256) tensor."""

def test_extractor_batch_processing():
    """Batch of 4 observations produces (4, 256) output."""

def test_extractor_handles_summary_dim():
    """12-dim summary vector processed correctly."""

def test_extractor_cnn_output_nonzero():
    """CNN branch produces non-zero output for non-zero input."""
```

### 3. Create `test_tactical_integration.py`

End-to-end tests that verify the pipeline WITHOUT the Rust Micro-Core (mock ZMQ):

```python
def test_observation_shape_all_stages():
    """All 8 stages produce obs with 8 ch*(50,50) + summary(12)."""

def test_action_masking_stage1():
    """Stage 1: only Hold and AttackCoord unmasked."""

def test_action_masking_stage6():
    """Stage 6+: all 8 actions unmasked."""

def test_coordinate_masking_small_map():
    """Stage 1 (25x25): only 625 of 2500 coords unmasked."""

def test_coordinate_masking_full_map():
    """Stage 6 (50x50): all 2500 coords unmasked."""

def test_center_padding():
    """Stage 1: terrain padding zone = 1.0 (wall)."""

def test_fog_disabled_channels():
    """Stages without fog: ch5 and ch6 are all 1.0."""

def test_fog_enabled_channels():
    """Stage 2: ch5 starts mostly 0 (unexplored) except brain vicinity."""

def test_reward_gradient():
    """Verify: tactical_win > brute_force_win > loss >= timeout."""
    # Synthetic snapshots with controlled faction counts

def test_multidiscrete_action_accepted():
    """SwarmEnv.step(np.array([1, 625])) does not crash."""

def test_action_sinking():
    """Hold(0) with any coordinate produces same Hold directive."""
```

### 4. Mock ZMQ for integration tests

Use the existing mock pattern from `tests/` — mock the ZMQ socket to return synthetic snapshots:

```python
@pytest.fixture
def mock_env():
    """SwarmEnv with mocked ZMQ that returns synthetic snapshots."""
    # Build env with mock ZMQ socket
    # Return synthetic state_snapshot on recv
    # Include density_maps, summary, fog_explored, fog_visible
```

### 5. Test reward gradient enforcement

```python
def test_reward_gradient():
    """Ensure the reward ordering is strictly maintained."""
    from src.env.rewards import compute_shaped_reward
    from src.config.definitions import RewardWeights
    
    weights = RewardWeights(...)
    
    # Tactical win: target killed, patrol far, many survivors
    tactical = compute_shaped_reward(
        snapshot_tactical_win, prev, brain=0, enemy=[1,2],
        reward_weights=weights, lure_success=True,
        threat_priority_hit=True, flanking_score=0.8,
    )
    
    # Brute force: all killed, few survivors
    brute = compute_shaped_reward(
        snapshot_brute_win, prev, brain=0, enemy=[1,2],
        reward_weights=weights,
    )
    
    # Loss and timeout
    loss = compute_shaped_reward(snapshot_loss, ...)
    
    assert tactical > brute, "Tactical win must beat brute force"
    assert brute > loss, "Brute force win must beat loss"
```

## Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: integration
  Test_Stack: pytest (macro-brain)
  Acceptance_Criteria:
    - "All tests in test_lkp_buffer.py pass"
    - "All tests in test_feature_extractor.py pass"
    - "All tests in test_tactical_integration.py pass"
    - "Observation shapes are (50,50) for all channels, all stages"
    - "Action masking prevents stage-locked actions"
    - "Coordinate masking prevents out-of-bounds coords"
    - "Reward gradient: tactical > brute > loss ≈ timeout"
    - "CNN forward pass produces correct shape"
    - "No import errors or circular dependencies"
  Suggested_Test_Commands:
    - "cd macro-brain && python -m pytest tests/test_lkp_buffer.py tests/test_feature_extractor.py tests/test_tactical_integration.py -v"
```
