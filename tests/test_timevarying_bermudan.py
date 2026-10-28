import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from bermudan_gtfk_split_pilot import price as fixed_gtfk_price
from bermudan_pilot import value as fixed_pde_value
from numerics import grid_for
from timevarying_bermudan import gtfk_put, pde_put, split_put
from timevarying_pde import european_put, split_european_put
from timevarying_gtfk import european_put as gtfk_european_put


MODEL = {"a": 0.4, "r0": 0.04, "rbar": 0.05, "sigma": 0.12}
SCHEDULE = [(0.0, 2.0, MODEL)]


def test_one_date_reduces_to_european():
    grid = grid_for(MODEL, 101, 1.5)
    states = np.array([np.log(MODEL["r0"])])
    np.testing.assert_array_equal(
        pde_put(SCHEDULE, [1.0], 1.5, 0.98, grid, 40),
        european_put(SCHEDULE, 1.0, 1.5, 0.98, grid, 40),
    )
    np.testing.assert_array_equal(
        split_put(SCHEDULE, [1.0], 1.5, 0.98, grid, 40, 12),
        split_european_put(SCHEDULE, 1.0, 1.5, 0.98, grid, 40, 12),
    )
    np.testing.assert_array_equal(
        gtfk_put(SCHEDULE, [1.0], 1.5, 0.98, states, grid, 16, 16),
        gtfk_european_put(SCHEDULE, 1.0, 1.5, 0.98, states, grid, 16, 16),
    )


def test_constant_schedule_reduces_to_fixed_bermudan():
    grid = grid_for(MODEL, 101, 1.5)
    dates = [0.5, 1.0]
    actual_pde = pde_put(SCHEDULE, dates, 1.5, 0.98, grid, 40)[50]
    expected_pde = fixed_pde_value(MODEL, dates, 1.5, 0.98, 101, 40, "put", 1.5)
    np.testing.assert_allclose(actual_pde, expected_pde, atol=1e-15, rtol=0)
    actual_gtfk = gtfk_put(SCHEDULE, dates, 1.5, 0.98,
                           np.array([np.log(MODEL["r0"])]), grid, 16, 16)[0]
    expected_gtfk = fixed_gtfk_price(MODEL, dates, 1.5, 0.98, 101, 16, 16)
    np.testing.assert_allclose(actual_gtfk, expected_gtfk, atol=1e-15, rtol=0)


def test_more_exercise_dates_cannot_reduce_pde_price():
    grid = grid_for(MODEL, 101, 1.5)
    one = pde_put(SCHEDULE, [1.0], 1.5, 0.98, grid, 40)[50]
    two = pde_put(SCHEDULE, [0.5, 1.0], 1.5, 0.98, grid, 40)[50]
    assert two >= one - 1e-12


def test_invalid_dates_rejected():
    grid = grid_for(MODEL, 101, 1.5)
    with pytest.raises(ValueError):
        pde_put(SCHEDULE, [1.0, 0.5], 1.5, 0.98, grid, 40)
