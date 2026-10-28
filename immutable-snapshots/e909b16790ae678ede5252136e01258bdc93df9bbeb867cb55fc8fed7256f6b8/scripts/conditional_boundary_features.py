"""Inputs for newly fitted exercise-date conditional continuation models.

Each cell is trained separately. The original contract feature vector remains
unchanged; the added coordinates specify the exercise state and date. The
three-strike contract rows share the same state/date design but retain their
own strike coordinate.
"""

import numpy as np


def encode(features, exercise_dates, date_index, log_rates):
    contract = np.asarray(features, dtype=float)
    dates = np.asarray(exercise_dates, dtype=float)
    states = np.asarray(log_rates, dtype=float)
    if contract.ndim != 1 or not np.all(np.isfinite(contract)):
        raise ValueError("contract features must be a finite vector")
    if dates.ndim != 1 or len(dates) < 2 or not np.all(np.diff(dates) > 0):
        raise ValueError("exercise dates must increase")
    if not 0 <= date_index < len(dates)-1:
        raise ValueError("only preterminal exercise dates have continuation labels")
    if states.ndim != 1 or not np.all(np.isfinite(states)):
        raise ValueError("log-rate states must be a finite vector")
    n = len(states)
    extra = np.column_stack((
        np.full(n, dates[date_index]),
        np.full(n, dates[date_index + 1] - dates[date_index]),
        np.full(n, date_index / (len(dates) - 1)),
        states,
    ))
    return np.column_stack((np.broadcast_to(contract, (n, len(contract))), extra))
