"""Integration tests for TacticalExtractor — CNN+MLP feature extractor.

Validates forward pass shapes, batch processing, summary dimension handling,
and non-zero CNN output for non-zero input.
"""

import numpy as np
import pytest
import torch
import gymnasium as gym

from src.models.feature_extractor import TacticalExtractor


# ── Helpers ─────────────────────────────────────────────────────────

def _make_obs_space() -> gym.spaces.Dict:
    """Build the canonical 8-channel + summary observation space."""
    obs = {}
    for ch in range(8):
        obs[f"ch{ch}"] = gym.spaces.Box(
            low=0.0, high=1.0, shape=(50, 50), dtype=np.float32
        )
    obs["summary"] = gym.spaces.Box(
        low=0.0, high=1.0, shape=(12,), dtype=np.float32
    )
    return gym.spaces.Dict(obs)


def _make_dummy_obs(batch_size: int, value: float = 0.0) -> dict[str, torch.Tensor]:
    """Create a batch of observations with constant fill value."""
    obs = {}
    for ch in range(8):
        obs[f"ch{ch}"] = torch.full((batch_size, 50, 50), value, dtype=torch.float32)
    obs["summary"] = torch.full((batch_size, 12), value, dtype=torch.float32)
    return obs


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def extractor():
    """TacticalExtractor with default 256-dim output."""
    obs_space = _make_obs_space()
    return TacticalExtractor(observation_space=obs_space, features_dim=256)


# ── Tests ───────────────────────────────────────────────────────────

def test_extractor_forward_shape(extractor):
    """Forward pass with dummy Dict obs produces (B, 256) tensor."""
    obs = _make_dummy_obs(batch_size=1)
    with torch.no_grad():
        out = extractor(obs)

    assert out.shape == (1, 256)
    assert out.dtype == torch.float32


def test_extractor_batch_processing(extractor):
    """Batch of 4 observations produces (4, 256) output."""
    obs = _make_dummy_obs(batch_size=4)
    with torch.no_grad():
        out = extractor(obs)

    assert out.shape == (4, 256)


def test_extractor_handles_summary_dim(extractor):
    """12-dim summary vector processed correctly."""
    obs = _make_dummy_obs(batch_size=2)
    # Set a distinctive summary pattern
    obs["summary"] = torch.tensor([
        [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.0, 0.5],
        [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0, 1.0, 0.5],
    ], dtype=torch.float32)

    with torch.no_grad():
        out = extractor(obs)

    assert out.shape == (2, 256)
    # Different summaries should produce different outputs
    # (CNN input is same zero grids, but summary differs)
    assert not torch.allclose(out[0], out[1])


def test_extractor_cnn_output_nonzero(extractor):
    """CNN branch produces non-zero output for non-zero input."""
    obs = _make_dummy_obs(batch_size=1, value=0.5)

    with torch.no_grad():
        out = extractor(obs)

    # With non-zero input, output should be non-zero
    assert out.abs().sum().item() > 0.0


def test_extractor_features_dim_configurable():
    """Features dim can be configured to a non-default value."""
    obs_space = _make_obs_space()
    ext = TacticalExtractor(observation_space=obs_space, features_dim=128)

    obs = _make_dummy_obs(batch_size=1)
    with torch.no_grad():
        out = ext(obs)

    assert out.shape == (1, 128)
    assert ext.features_dim == 128


def test_extractor_zero_input_produces_finite_output(extractor):
    """All-zero input should produce finite output (no NaN/Inf)."""
    obs = _make_dummy_obs(batch_size=2, value=0.0)

    with torch.no_grad():
        out = extractor(obs)

    assert torch.isfinite(out).all(), "Output contains NaN or Inf"


def test_extractor_gradient_flows():
    """Gradients flow through the full extractor for backprop."""
    obs_space = _make_obs_space()
    ext = TacticalExtractor(observation_space=obs_space, features_dim=256)

    obs = _make_dummy_obs(batch_size=2, value=0.3)
    # Make obs require grad
    for key in obs:
        obs[key] = obs[key].requires_grad_(True)

    out = ext(obs)
    loss = out.sum()
    loss.backward()

    # Verify gradients exist on at least one grid channel
    assert obs["ch0"].grad is not None
    assert obs["ch0"].grad.abs().sum().item() > 0.0
