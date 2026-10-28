import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from numerics import grid_for, pde_curve
from timevarying_pde import propagate, european_put, split_propagate


MODEL = {"a": 0.4, "r0": 0.04, "rbar": 0.05, "sigma": 0.12}


def test_constant_curve_reduces_to_existing_pde():
    grid = grid_for(MODEL, 101)
    schedule = [(0.0, 2.0, MODEL)]
    actual = propagate(schedule, 0.0, 1.5, grid, 40)
    expected = pde_curve(MODEL, 1.5, grid, 60)
    np.testing.assert_array_equal(actual, expected)
    bond = pde_curve(MODEL, 0.5, grid, 20)
    expected_put = pde_curve(MODEL, 1.0, grid, 40, np.maximum(0.9 - bond, 0))
    np.testing.assert_array_equal(european_put(schedule, 1.0, 1.5, 0.9, grid, 40), expected_put)


def test_schedule_gap_rejected():
    grid = grid_for(MODEL, 101)
    with pytest.raises(ValueError, match="gap"):
        propagate([(0.0, 0.5, MODEL), (0.6, 2.0, MODEL)], 0.0, 1.0, grid, 40)


def test_split_zero_volatility_at_mean_state():
    model = dict(MODEL, sigma=0.0, r0=MODEL["rbar"])
    grid = grid_for(model, 101)
    schedule = [(0.0, 0.4, model), (0.4, 1.0, model)]
    actual = split_propagate(schedule, 0.0, 1.0, grid, 40)[50]
    np.testing.assert_allclose(actual, np.exp(-model["rbar"]), atol=1e-13)
