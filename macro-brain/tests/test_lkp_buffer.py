"""Integration tests for LKPBuffer — Last Known Position memory.

Verifies decay mechanics, visibility overwrite, non-negativity,
reset behavior, and mixed visibility scenarios.
"""

import numpy as np
import pytest

from src.utils.lkp_buffer import LKPBuffer


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def buffer():
    """Standard 50×50 LKP buffer with 2 enemy channels and 0.02 decay."""
    return LKPBuffer(grid_h=50, grid_w=50, num_enemy_channels=2, decay_rate=0.02)


# ── Tests ───────────────────────────────────────────────────────────

def test_lkp_overwrites_visible_cells(buffer):
    """Visible cells get ground truth density."""
    live = np.zeros((50, 50), dtype=np.float32)
    live[10, 20] = 0.75
    live[30, 40] = 0.50

    vis = np.zeros((50, 50), dtype=np.float32)
    vis[10, 20] = 1.0  # visible
    vis[30, 40] = 1.0  # visible

    result = buffer.update(0, live, vis)

    assert result[10, 20] == pytest.approx(0.75)
    assert result[30, 40] == pytest.approx(0.50)


def test_lkp_decays_hidden_cells(buffer):
    """Hidden cells decay by decay_rate per update."""
    # Pre-seed memory with known density
    buffer.memory[0][5, 5] = 1.0
    buffer.memory[0][15, 15] = 0.5

    live = np.zeros((50, 50), dtype=np.float32)
    vis = np.zeros((50, 50), dtype=np.float32)  # all hidden

    result = buffer.update(0, live, vis)

    assert result[5, 5] == pytest.approx(1.0 - 0.02)
    assert result[15, 15] == pytest.approx(0.5 - 0.02)

    # Second update: decays further
    result2 = buffer.update(0, live, vis)
    assert result2[5, 5] == pytest.approx(1.0 - 2 * 0.02)
    assert result2[15, 15] == pytest.approx(0.5 - 2 * 0.02)


def test_lkp_never_negative(buffer):
    """Decayed density never drops below 0."""
    buffer.memory[0][3, 3] = 0.01  # just above zero

    live = np.zeros((50, 50), dtype=np.float32)
    vis = np.zeros((50, 50), dtype=np.float32)

    result = buffer.update(0, live, vis)

    # 0.01 - 0.02 would be -0.01 but should clamp to 0
    assert result[3, 3] == pytest.approx(0.0)

    # Already at zero: should stay zero
    result2 = buffer.update(0, live, vis)
    assert result2[3, 3] == pytest.approx(0.0)


def test_lkp_reset_zeros_memory(buffer):
    """reset() clears all stored density."""
    buffer.memory[0][10, 10] = 0.9
    buffer.memory[0][20, 20] = 0.5
    buffer.memory[1][5, 5] = 0.7

    buffer.reset()

    assert buffer.memory[0].sum() == pytest.approx(0.0)
    assert buffer.memory[1].sum() == pytest.approx(0.0)

    # get() after reset should also be zeros
    ch0 = buffer.get(0)
    ch1 = buffer.get(1)
    assert ch0.sum() == pytest.approx(0.0)
    assert ch1.sum() == pytest.approx(0.0)


def test_lkp_mixed_visible_hidden(buffer):
    """Partial visibility: some cells overwrite, others decay."""
    # Pre-seed with known values
    buffer.memory[0][0, 0] = 0.8  # will be visible → overwritten
    buffer.memory[0][1, 1] = 0.6  # will be hidden → decayed
    buffer.memory[0][2, 2] = 0.4  # will be hidden → decayed

    live = np.zeros((50, 50), dtype=np.float32)
    live[0, 0] = 0.3  # ground truth: lower than memory

    vis = np.zeros((50, 50), dtype=np.float32)
    vis[0, 0] = 1.0  # only (0,0) is visible

    result = buffer.update(0, live, vis)

    # Visible cell: overwritten with live density (even if lower)
    assert result[0, 0] == pytest.approx(0.3)
    # Hidden cells: decayed
    assert result[1, 1] == pytest.approx(0.6 - 0.02)
    assert result[2, 2] == pytest.approx(0.4 - 0.02)


def test_lkp_update_returns_copy(buffer):
    """update() returns a copy, not a reference to internal memory."""
    live = np.zeros((50, 50), dtype=np.float32)
    live[0, 0] = 1.0
    vis = np.ones((50, 50), dtype=np.float32)

    result = buffer.update(0, live, vis)
    result[0, 0] = 999.0  # mutate the result

    # Internal memory should be unaffected
    assert buffer.memory[0][0, 0] == pytest.approx(1.0)


def test_lkp_get_returns_copy(buffer):
    """get() returns a copy, not a reference to internal memory."""
    buffer.memory[0][0, 0] = 0.5

    got = buffer.get(0)
    got[0, 0] = 999.0

    assert buffer.memory[0][0, 0] == pytest.approx(0.5)


def test_lkp_independent_channels(buffer):
    """Updating one channel does not affect the other."""
    live = np.zeros((50, 50), dtype=np.float32)
    live[10, 10] = 1.0
    vis = np.ones((50, 50), dtype=np.float32)

    buffer.update(0, live, vis)

    # Channel 1 should be untouched
    assert buffer.memory[1][10, 10] == pytest.approx(0.0)
