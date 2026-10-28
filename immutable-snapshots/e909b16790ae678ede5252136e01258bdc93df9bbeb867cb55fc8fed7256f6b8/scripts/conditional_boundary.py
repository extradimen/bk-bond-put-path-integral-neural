"""Exercise-date conditional bond-put curves for new state-conditioned models."""
import numpy as np

from bermudan_gtfk_split_pilot import crossings
from timevarying_pde import propagate as pde_propagate, split_propagate
from timevarying_gtfk import bond as gtfk_bond, propagate as gtfk_propagate


def conditional_curves(case, strike, grid, method, rate=None, order=24, nq=128, ny=128):
    """Return bond, exercise, continuation and gap at each exercise date.

    Last exercise continuation is exactly zero. `gap` is exercise minus
    continuation at earlier dates and raw strike-minus-bond at the last date.
    All curves are on the same log-rate grid; no t=0 neural price is reused.
    """
    schedule = case["schedule"]
    dates = case["exercise"]
    maturity = case["maturity"]
    if method not in ("pde", "split", "gtfk"):
        raise ValueError(method)
    if method != "gtfk" and (rate is None or rate <= 0):
        raise ValueError("PDE/split propagation needs positive steps per year")
    if not np.all(np.diff(grid) > 0):
        raise ValueError("state grid must increase")
    value = None
    later = None
    kinks = []
    records = []
    for date in reversed(dates):
        if method == "pde":
            bond = pde_propagate(schedule, date, maturity, grid, rate)
        elif method == "split":
            bond = split_propagate(schedule, date, maturity, grid, rate, order=order)
        else:
            bond = gtfk_bond(schedule, date, maturity, grid, grid, nq, ny)
        raw = float(strike)-bond
        exercise = np.maximum(raw, 0.0)
        if value is None:
            continuation = np.zeros_like(exercise)
            gap = raw
            kinks = crossings(grid, raw)
        else:
            if method == "pde":
                continuation = pde_propagate(schedule, date, later, grid, rate, value)
            elif method == "split":
                continuation = split_propagate(schedule, date, later, grid, rate, value, order)
            else:
                continuation = gtfk_propagate(schedule, date, later, grid, grid,
                                              value, kinks, nq, ny)
            gap = exercise-continuation
            kinks = crossings(grid, gap)
        value = np.maximum(exercise, continuation)
        records.append(dict(date=float(date), bond=bond, exercise=exercise,
                            continuation=continuation, value=value, gap=gap))
        later = date
    return list(reversed(records))
