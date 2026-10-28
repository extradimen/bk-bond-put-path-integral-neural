"""Piecewise composition of fixed-coefficient GTFK conditional kernels.

Every time interval has its own BK coefficients.  The composition is an
approximation: it does not turn GTFK into an exact non-autonomous propagator.
"""
import numpy as np

from bermudan_gtfk_split_pilot import crossings, propagate as fixed_propagate
from numerics import gt_bond


def segments(schedule, start, end):
    if not (0 <= start < end):
        raise ValueError("expected 0 <= start < end")
    cursor = start
    pieces = []
    for left, right, model in sorted(schedule, key=lambda item: item[0]):
        left, right = float(left), float(right)
        if right <= start or left >= end:
            continue
        lo, hi = max(left, start), min(right, end)
        if abs(lo - cursor) > 1e-12:
            raise ValueError("schedule has a gap or overlap")
        pieces.append((lo, hi, model))
        cursor = hi
    if abs(cursor - end) > 1e-12:
        raise ValueError("schedule does not cover requested horizon")
    return pieces


def propagate(schedule, start, end, starts, grid, values, kinks, nq, ny):
    """Propagate terminal state values backward across calendar-time pieces."""
    pieces = segments(schedule, start, end)
    curve = np.asarray(values, dtype=float)
    for index, (left, right, model) in enumerate(reversed(pieces)):
        source = np.atleast_1d(starts) if index == len(pieces) - 1 else grid
        curve = fixed_propagate(model, right - left, source, grid, curve,
                                kinks if index == 0 else [], nq, ny)
    return curve


def bond(schedule, start, end, starts, grid, nq, ny):
    """Discounted unit payoff at ``end`` conditional on states at ``start``."""
    pieces = segments(schedule, start, end)
    if len(pieces) == 1:
        return gt_bond(pieces[0][2], end - start, starts, nq=nq)
    return propagate(schedule, start, end, starts, grid, np.ones(len(grid)), [], nq, ny)


def european_put(schedule, exercise, maturity, strike, starts, grid, nq, ny):
    underlying = bond(schedule, exercise, maturity, grid, grid, nq, ny)
    raw = float(strike) - underlying
    payoff = np.maximum(raw, 0.0)
    return propagate(schedule, 0.0, exercise, starts, grid, payoff,
                     crossings(grid, raw), nq, ny)
