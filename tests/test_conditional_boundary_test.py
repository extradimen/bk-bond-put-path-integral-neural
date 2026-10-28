import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import conditional_boundary_test as boundary_test


def test_boundary_comparison_uses_exercise_date_continuation(monkeypatch):
    case = {"exercise": [.5, 1.5, 2.5]}
    monkeypatch.setattr(boundary_test, "schedule_grid",
                        lambda _case, n, _width: np.linspace(-5., -2., n))

    def fake_curves(_case, _strike, grid, _method, **_kw):
        exercise = np.ones_like(grid)
        continuation = 1. + .1*(grid + 3.497)
        return [dict(exercise=exercise, continuation=continuation,
                     gap=exercise-continuation) for _ in case["exercise"]]

    monkeypatch.setattr(boundary_test, "conditional_curves", fake_curves)
    monkeypatch.setattr(boundary_test, "predict", lambda _path, x: np.zeros(len(x)))
    cfg = dict(reference=[101, 20, 1.], independent=[101, 20, 1., 24],
               coarse=[51, 10, 1.], gtfk=[51, 8, 8, 1.],
               evaluation_states=101, domain_margin=.01,
               reference_root_tolerance=1e-4, reference_value_tolerance=1e-4,
               continuation_mae_tolerance=.002, model_root_tolerance=.001,
               methods=["B", "C", "D"])
    records = boundary_test.evaluate_contract(np.array([.1, 1.]), case,
                                               {m: "unused" for m in cfg["methods"]}, cfg)
    assert len(records) == 2
    assert all(r["reference_valid"] and r["reference_root_count"] == 1 for r in records)
    assert all(not r["methods"]["B"]["passed"] for r in records)
    assert all(r["methods"]["C"]["passed"] and r["methods"]["D"]["passed"] for r in records)
