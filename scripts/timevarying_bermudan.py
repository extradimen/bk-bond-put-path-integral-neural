"""Piecewise-time BK Bermudan put recurrence for PDE and GTFK kernels."""
import numpy as np

from bermudan_gtfk_split_pilot import crossings
from timevarying_pde import propagate as pde_propagate, split_propagate
from timevarying_gtfk import bond as gtfk_bond, propagate as gtfk_propagate


def _dates(exercise, maturity):
    dates = [float(x) for x in exercise]
    if not dates or dates != sorted(set(dates)) or dates[0] <= 0 or dates[-1] >= maturity:
        raise ValueError("exercise dates must be strictly increasing inside (0, maturity)")
    return dates


def pde_put(schedule, exercise, maturity, strike, grid, steps_per_year):
    """Full t=0 state curve for a Bermudan put on a unit zero-coupon bond."""
    dates = _dates(exercise, maturity)
    curve = None
    previous = None
    for date in reversed(dates):
        bond = pde_propagate(schedule, date, maturity, grid, steps_per_year)
        intrinsic = np.maximum(float(strike) - bond, 0.0)
        if curve is None:
            curve = intrinsic
        else:
            continuation = pde_propagate(schedule, date, previous, grid,
                                          steps_per_year, curve)
            curve = np.maximum(intrinsic, continuation)
        previous = date
    return pde_propagate(schedule, 0.0, dates[0], grid, steps_per_year, curve)


def split_put(schedule, exercise, maturity, strike, grid, steps_per_year, order=24):
    """Independent exact-OU/discount-split Bermudan price curve."""
    dates = _dates(exercise, maturity)
    curve = None
    previous = None
    for date in reversed(dates):
        bond = split_propagate(schedule, date, maturity, grid, steps_per_year,
                               order=order)
        intrinsic = np.maximum(float(strike) - bond, 0.0)
        if curve is None:
            curve = intrinsic
        else:
            continuation = split_propagate(schedule, date, previous, grid,
                                            steps_per_year, curve, order)
            curve = np.maximum(intrinsic, continuation)
        previous = date
    return split_propagate(schedule, 0.0, dates[0], grid, steps_per_year,
                           curve, order)


def gtfk_put(schedule, exercise, maturity, strike, starts, grid, nq, ny):
    """Conditional t=0 GTFK price, composing each regime's kernel."""
    dates = _dates(exercise, maturity)
    curve = None
    previous = None
    kinks = []
    for date in reversed(dates):
        bond = gtfk_bond(schedule, date, maturity, grid, grid, nq, ny)
        raw = float(strike) - bond
        intrinsic = np.maximum(raw, 0.0)
        if curve is None:
            curve = intrinsic
            kinks = crossings(grid, raw)
        else:
            continuation = gtfk_propagate(schedule, date, previous, grid,
                                           grid, curve, kinks, nq, ny)
            curve = np.maximum(intrinsic, continuation)
            kinks = crossings(grid, intrinsic - continuation)
        previous = date
    return gtfk_propagate(schedule, 0.0, dates[0], starts, grid,
                          curve, kinks, nq, ny)
