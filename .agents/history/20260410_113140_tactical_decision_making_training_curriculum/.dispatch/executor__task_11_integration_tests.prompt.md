# AGENT ROLE: EXECUTION SPECIALIST

You are an **Execution Specialist** in a multi-agent DAG workflow.
You have been assigned ONE specific task. You implement it with surgical precision.

---

## Your Assignment

| Field   | Value |
|---------|-------|
| Task ID | `task_11_integration_tests` |
| Feature | Tactical Decision-Making Training Curriculum |
| Tier    | advanced |

---

## ⛔ MANDATORY PROCESS — ALL TIERS (DO NOT SKIP)

> **These rules apply to EVERY executor, regardless of tier. Violating them
> causes an automatic QA FAIL and project BLOCK.**

### Rule 1: Scope Isolation
- You may ONLY create or modify files listed in `Target_Files` in your Task Brief.
- If a file must be changed but is NOT in `Target_Files`, **STOP and report the gap** — do NOT modify it.
- NEVER edit `task_state.json`, `implementation_plan.md`, or any file outside your scope.

### Rule 2: Changelog (Handoff Documentation)
After ALL code is written and BEFORE calling `./task_tool.sh done`, you MUST:

1. **Create** `tasks_pending/task_11_integration_tests_changelog.md`
2. **Include in the changelog:**
   - **Touched Files:** A bulleted list of every file you created or modified.
   - **Contract Fulfillment:** Brief confirmation of the interfaces/DTOs you implemented.
   - **Deviations/Notes:** Any edge cases you handled or deviations from the brief the QA agent should verify.
3. **Then and only then** run:
   ```bash
   ./task_tool.sh done task_11_integration_tests
   ```

> **⚠️ Calling `./task_tool.sh done` without creating the changelog file is FORBIDDEN.**

### Rule 3: No Placeholders
- Do not use `// TODO`, `/* FIXME */`, or stub implementations.
- Output fully functional, production-ready code.

### Rule 4: Human Intervention Protocol
During execution, a human may intercept your work and propose changes, provide code snippets, or redirect your approach. When this happens:

1. **ADOPT the concept, VERIFY the details.** Humans are exceptional at architectural vision but make detail mistakes (wrong API, typos, outdated syntax). Independently verify all human-provided code against the actual framework version and project contracts.
2. **TRACK every human intervention in the changelog.** Add a dedicated `## Human Interventions` section to your changelog documenting:
   - What the human proposed (1-2 sentence summary)
   - What you adopted vs. what you corrected
   - Any deviations from the original task brief caused by the intervention
3. **DO NOT silently incorporate changes.** The QA agent and Architect must be able to trace exactly what came from the spec vs. what came from a human mid-flight. Untracked changes are invisible to the verification pipeline.

---

## Context Loading (Tier-Dependent)

**If your tier is `standard` or `advanced`:**

> **CRITICAL FIRST STEP:** The Planner might omit critical skills or knowledge in your `Context_Bindings`. It is YOUR responsibility to self-heal missing context.
1. Read `.agents/skills/index.md` (Skills Catalog)
2. Read `.agents/knowledge/README.md` (Master Knowledge Index)
   *(If you discover a skill or knowledge domain relevant to your task that isn't in your `Context_Bindings`, **read it immediately** before starting.)*
3. Read `.agents/context.md` — Thin index pointing to context sub-files
4. Load ONLY the `context/*` sub-files listed in your `Context_Bindings` below
5. Scan `.agents/knowledge/` — Lessons from previous sessions relevant to your task
6. Read `.agents/workflows/execution-lifecycle.md` — Your 4-step execution loop
7. Read `.agents/rules/execution-boundary.md` — Scope and contract constraints

- `./.agents/context/architecture.md`
- `./.agents/context/conventions.md`
- `./.agents/context/ipc-protocol.md`

---

## Task Brief

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

---

## Shared Contracts

_See `implementation_plan.md` for full contract definitions._

