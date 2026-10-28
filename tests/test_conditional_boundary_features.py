import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from conditional_boundary_features import encode


def test_encoding_preserves_contract_and_state_date_identity():
    x = np.array([.1, .2, .3, 101.])
    dates = [.5, 1.5, 2.]
    states = np.array([-4., -3.])
    first = encode(x, dates, 0, states)
    second = encode(x, dates, 1, states)
    assert first.shape == (2, 8)
    np.testing.assert_array_equal(first[:, :4], np.broadcast_to(x, (2, 4)))
    np.testing.assert_array_equal(first[:, -1], states)
    np.testing.assert_array_equal(first[:, -4:-1], [[.5, 1., 0.], [.5, 1., 0.]])
    np.testing.assert_array_equal(second[:, -4:-1], [[1.5, .5, .5], [1.5, .5, .5]])


def test_terminal_date_is_excluded():
    with pytest.raises(ValueError):
        encode(np.array([1.]), [.5, 1.], 1, np.array([-3.]))
