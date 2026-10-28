"""Construct group-isolated exercise-date continuation examples.

The fine PDE labels, independent OU split check, GTFK and coarse PDE baselines
are computed from the same contract and log-rate states. This module performs
no fitting and does not read a test split implicitly.
"""

import numpy as np

from conditional_boundary import conditional_curves
from conditional_boundary_features import encode
from put_exercise_boundary_pilot import roots
from timevarying_data_pilot import schedule_grid


def contract_examples(features, case, reference=(3201, 400, 1.0),
                      independent=(3201, 400, 1.0, 24),
                      coarse=(201, 100, 1.0), gtfk=(801, 32, 32, 1.0),
                      state_count=33, boundary_offsets=()):
    """Return one contract's preterminal rows and numerical quality checks.

    Settings are explicit so a frozen caller can record them. The independent
    solver must agree with the reference within the caller's frozen gate.
    """
    features = np.asarray(features, dtype=float)
    strike = float(features[-1])
    ref_grid = schedule_grid(case, reference[0], reference[2])
    split_grid = schedule_grid(case, independent[0], independent[2])
    coarse_grid = schedule_grid(case, coarse[0], coarse[2])
    gtfk_grid = schedule_grid(case, gtfk[0], gtfk[3])
    lo = ref_grid[0] + .1 * (ref_grid[-1] - ref_grid[0])
    hi = ref_grid[-1] - .1 * (ref_grid[-1] - ref_grid[0])
    uniform_states = np.linspace(lo, hi, state_count)
    fine = conditional_curves(case, strike, ref_grid, "pde", rate=reference[1])
    independent_rows = conditional_curves(case, strike, split_grid, "split",
                                          rate=independent[1], order=independent[3])
    coarse_rows = conditional_curves(case, strike, coarse_grid, "pde", rate=coarse[1])
    gtfk_rows = conditional_curves(case, strike, gtfk_grid, "gtfk",
                                   nq=gtfk[1], ny=gtfk[2])
    if not (len(fine) == len(independent_rows) == len(coarse_rows) == len(gtfk_rows)
            == len(case["exercise"])):
        raise RuntimeError("exercise-date row count differs across methods")
    examples = []
    for j in range(len(fine) - 1):
        fine_roots = roots(ref_grid, fine[j]["gap"])
        if len(fine_roots) == 1 and boundary_offsets:
            nearby = np.array([fine_roots[0] + offset for offset in boundary_offsets])
            nearby = nearby[(nearby > lo) & (nearby < hi)]
            states = np.unique(np.concatenate((uniform_states, nearby)))
        else:
            states = uniform_states
        target = np.interp(states, ref_grid, fine[j]["continuation"])
        independent_value = np.interp(states, split_grid,
                                      independent_rows[j]["continuation"])
        coarse_value = np.interp(states, coarse_grid, coarse_rows[j]["continuation"])
        gtfk_value = np.interp(states, gtfk_grid, gtfk_rows[j]["continuation"])
        if not all(np.all(np.isfinite(v)) for v in
                   (target, independent_value, coarse_value, gtfk_value)):
            raise FloatingPointError("nonfinite conditional continuation values")
        examples.append(dict(date_index=j,
                             X=encode(features, case["exercise"], j, states),
                             states=states.copy(), y=target,
                             A=gtfk_value, Dbase=coarse_value,
                             independent_max_abs=float(np.max(abs(target-independent_value))),
                             reference_root_count=len(fine_roots)))
    if not np.all(fine[-1]["continuation"] == 0):
        raise RuntimeError("terminal exercise continuation must be zero")
    return examples
