import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import conditional_boundary_repair_data as repair


def test_failed_groups_reads_only_original_failures(tmp_path):
    p = tmp_path / "groups.jsonl"
    p.write_text("\n".join(json.dumps(x) for x in [
        dict(split="train", cell="FB", group=2, label_passed=True),
        dict(split="train", cell="FB", group=3, label_passed=False),
        dict(split="val", cell="TB", group=1, label_passed=False),
    ]) + "\n")
    assert repair.failed_groups(p) == {("train", "FB", 3), ("val", "TB", 1)}


def test_group_examples_preserves_group_and_state_alignment(monkeypatch):
    monkeypatch.setattr(repair, "fixed_contract", lambda _features: {"exercise": [.5, 1.5, 2.5]})

    def fake_examples(features, _case, **_kwargs):
        return [dict(X=np.ones((2, 6)) * features[-1], y=np.array([1., 2.]),
                     A=np.array([.1, .2]), Dbase=np.array([.3, .4]),
                     date_index=0, independent_max_abs=.00001)]

    monkeypatch.setattr(repair, "contract_examples", fake_examples)
    source = {"train_FB_group": np.array([4, 4, 4]),
              "train_FB_X": np.array([[.1, .9], [.1, 1.], [.1, 1.1]])}
    blocks, error = repair.group_examples(source, "train", "FB", 4,
        dict(independent=[], coarse=[], gtfk=[], states_per_date=2,
             boundary_offsets=[]), [21, 10, 1.])
    assert error == .00001
    assert len(blocks["y"]) == 6
    np.testing.assert_array_equal(blocks["group"], 4)
    np.testing.assert_array_equal(blocks["strike_index"], [0, 0, 1, 1, 2, 2])
    np.testing.assert_array_equal(blocks["state_index"], [0, 1, 0, 1, 0, 1])
