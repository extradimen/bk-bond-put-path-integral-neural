import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import conditional_boundary_fast_label_pilot as pilot


def test_pilot_compares_same_states_and_early_dates(monkeypatch):
    monkeypatch.setattr(pilot, "schedule_grid", lambda _case,n,_width: np.linspace(-5,-2,n))
    def curves(_case,_strike,grid,_method,**_kw):
        return [dict(continuation=np.full(len(grid),v+(0.01 if len(grid)==21 else 0.)))
                for v in (1.,2.,0.)]
    monkeypatch.setattr(pilot, "conditional_curves", curves)
    cfg = dict(pde_settings=[[21,10,1.],[41,20,1.]], domain_margin=.1, states_per_date=5)
    row=pilot.one(np.array([.1,1.]),dict(exercise=[.5,1.5,2.5]),cfg)
    assert len(row["records"])==2
    np.testing.assert_allclose([r["max_abs_by_lower_setting"][0] for r in row["records"]],.01)
