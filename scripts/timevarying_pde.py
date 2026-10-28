"""Backward BK PDE propagation for piecewise-constant calendar-time coefficients.

This module keeps the calendar-time partition explicit.  It is a numerical
solver, not an analytic price or a generalized GTFK approximation.
"""
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.special import roots_hermitenorm

from numerics import pde_curve


def propagate(schedule, start, end, grid, steps_per_year, payoff=None):
    """Return value at ``start`` for a payoff at ``end``.

    ``schedule`` is a sequence of ``(left, right, model)`` intervals covering
    the requested time range.  Each model has the fixed-BK keys accepted by
    ``pde_curve``.  The backward equation applies later intervals first.
    """
    if not (0 <= start < end):
        raise ValueError("expected 0 <= start < end")
    intervals = sorted(schedule, key=lambda item: item[0])
    cursor = start
    pieces = []
    for left, right, model in intervals:
        left, right = float(left), float(right)
        if right <= start or left >= end:
            continue
        lo, hi = max(left, start), min(right, end)
        if abs(lo - cursor) > 1e-12:
            raise ValueError("schedule has a gap or overlap")
        if hi <= lo:
            raise ValueError("empty schedule interval")
        pieces.append((lo, hi, model))
        cursor = hi
    if abs(cursor - end) > 1e-12:
        raise ValueError("schedule does not cover requested horizon")
    value = np.ones(len(grid)) if payoff is None else np.asarray(payoff, dtype=float).copy()
    for left, right, model in reversed(pieces):
        steps = max(4, int(round((right - left) * steps_per_year)))
        value = pde_curve(model, right - left, grid, steps, value)
    return value


def european_put(schedule, exercise, maturity, strike, grid, steps_per_year):
    """Price a put on a unit zero-coupon bond on the supplied state grid."""
    bond = propagate(schedule, exercise, maturity, grid, steps_per_year)
    intrinsic = np.maximum(float(strike) - bond, 0.0)
    return propagate(schedule, 0.0, exercise, grid, steps_per_year, intrinsic)


def split_propagate(schedule, start, end, grid, steps_per_year, payoff=None, order=16):
    """Independent exact-OU/discount split propagation for crosschecks.

    Uses the exact Gaussian OU transition within each constant-coefficient
    time step and Strang splitting for the short-rate discount.  This does
    not share the PDE stencil or linear solver.
    """
    if not (0 <= start < end):
        raise ValueError("expected 0 <= start < end")
    intervals = sorted(schedule, key=lambda item: item[0])
    cursor = start
    pieces = []
    for left, right, model in intervals:
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
    grid = np.asarray(grid, dtype=float)
    value = np.ones(len(grid)) if payoff is None else np.asarray(payoff, dtype=float).copy()
    z, weights = roots_hermitenorm(order)
    weights = weights / np.sqrt(2 * np.pi)
    for left, right, model in reversed(pieces):
        steps = max(4, int(round((right - left) * steps_per_year)))
        dt = (right - left) / steps
        a, sigma, b = model["a"], model["sigma"], np.log(model["rbar"])
        variance = sigma**2 * (-np.expm1(-2*a*dt)) / (2*a)
        mean = b + (grid - b) * np.exp(-a*dt)
        nodes = np.clip(mean[:, None] + np.sqrt(variance) * z, grid[0], grid[-1])
        discount = np.exp(-np.exp(grid) * dt / 2)
        for _ in range(steps):
            value = discount * (CubicSpline(grid, value * discount)(nodes) @ weights)
    return value


def split_european_put(schedule, exercise, maturity, strike, grid, steps_per_year, order=16):
    """Independent OU-splitting price for the same put contract."""
    bond = split_propagate(schedule, exercise, maturity, grid, steps_per_year, order=order)
    payoff = np.maximum(float(strike) - bond, 0.0)
    return split_propagate(schedule, 0.0, exercise, grid, steps_per_year, payoff, order=order)
