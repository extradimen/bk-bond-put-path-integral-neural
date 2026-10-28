import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from bermudan_gtfk_split_pilot import price as fixed_price
from numerics import grid_for, gt_bond
from timevarying_gtfk import bond, european_put, segments


MODEL = {"a": 0.4, "r0": 0.04, "rbar": 0.05, "sigma": 0.12}


def test_single_segment_bond_is_fixed_gtfk():
    grid = grid_for(MODEL, 101, 1.5)
    schedule = [(0.0, 2.0, MODEL)]
    states = np.array([np.log(MODEL["r0"])])
    np.testing.assert_array_equal(
        bond(schedule, 0.0, 1.0, states, grid, 16, 16),
        gt_bond(MODEL, 1.0, states, nq=16),
    )


def test_single_segment_european_put_is_fixed_gtfk():
    grid = grid_for(MODEL, 101, 1.5)
    schedule = [(0.0, 2.0, MODEL)]
    value = european_put(schedule, 1.0, 1.5, 0.9,
                         np.array([np.log(MODEL["r0"])]), grid, 16, 16)[0]
    expected = fixed_price(MODEL, [1.0], 1.5, 0.9, 101, 16, 16)
    np.testing.assert_allclose(value, expected, rtol=0, atol=1e-15)


def test_schedule_gap_rejected():
    try:
        segments([(0.0, 0.4, MODEL), (0.5, 2.0, MODEL)], 0.0, 1.0)
    except ValueError as exc:
        assert "gap" in str(exc)
    else:
        raise AssertionError("gap accepted")
