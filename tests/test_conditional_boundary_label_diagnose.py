import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import conditional_boundary_label_diagnose as diagnose


def test_compares_all_methods_on_same_early_date_states(monkeypatch):
    monkeypatch.setattr(diagnose, "schedule_grid", lambda _case, n, _width: np.linspace(-2., 2., n))

    def curves(_case, _strike, grid, method, **_kw):
        shift = .02 if method == "split" else (.01 if len(grid) == 21 else 0.)
        return [dict(continuation=np.ones(len(grid)) + shift, gap=grid-.03),
                dict(continuation=np.ones(len(grid))*2 + shift, gap=np.ones(len(grid))),
                dict(continuation=np.zeros(len(grid)), gap=np.ones(len(grid)))]

    monkeypatch.setattr(diagnose, "conditional_curves", curves)
    cfg = dict(pde_settings=[[21, 10, 1.], [41, 20, 1.]],
               independent=[41, 20, 1., 8], domain_margin=.1,
               states_per_date=5, boundary_offsets=[-.1, 0., .1])
    rows = diagnose.contract_differences(np.array([.1, 1.]),
        dict(exercise=[.5, 1.5, 2.5]), cfg)
    assert len(rows) == 2
    assert rows[0]["states"] == 8
    assert rows[1]["states"] == 5
    np.testing.assert_allclose(rows[0]["pde_max_abs_to_finest"], [.01])
    np.testing.assert_allclose(rows[0]["independent_max_abs_to_finest"], .02)
