import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import conditional_boundary_dataset as dataset


def test_contract_rows_align_methods_and_exclude_terminal(monkeypatch):
    case = {"exercise": [.5, 1.5, 2.5]}
    monkeypatch.setattr(dataset, "schedule_grid", lambda _case, n, _width: np.linspace(-5, -2, n))

    def fake_curves(_case, _strike, grid, method, **_kw):
        offset = {"pde": 0., "split": .01, "gtfk": .02}[method]
        if method == "pde" and len(grid) == 201:
            offset = .03
        return [{"continuation": np.full(len(grid), date + offset),
                 "gap": np.ones(len(grid))}
                for date in (1., 2., 0.)]

    monkeypatch.setattr(dataset, "conditional_curves", fake_curves)
    rows = dataset.contract_examples(np.array([.1, 1.]), case, state_count=5)
    assert len(rows) == 2
    assert all(row["X"].shape == (5, 6) for row in rows)
    np.testing.assert_allclose(rows[1]["y"], 2.)
    np.testing.assert_allclose(rows[1]["A"] - rows[1]["y"], .02)
    np.testing.assert_allclose(rows[1]["Dbase"] - rows[1]["y"], .03)
    np.testing.assert_allclose(rows[1]["independent_max_abs"], .01)


def test_boundary_offsets_add_training_states_near_reference_root(monkeypatch):
    case = {"exercise": [.5, 1.5, 2.5]}
    monkeypatch.setattr(dataset, "schedule_grid", lambda _case, n, _width: np.linspace(-2., 2., n))

    def fake_curves(_case, _strike, grid, method, **_kw):
        return [{"continuation": np.ones(len(grid)), "gap": grid.copy() - .03},
                {"continuation": np.ones(len(grid)), "gap": np.ones(len(grid))},
                {"continuation": np.zeros(len(grid)), "gap": np.ones(len(grid))}]

    monkeypatch.setattr(dataset, "conditional_curves", fake_curves)
    rows = dataset.contract_examples(np.array([.1, 1.]), case, state_count=5,
                                     boundary_offsets=(-.1, 0., .1))
    assert len(rows[0]["states"]) == 8
    assert len(rows[1]["states"]) == 5
    assert rows[0]["reference_root_count"] == 1
    assert rows[1]["reference_root_count"] == 0
