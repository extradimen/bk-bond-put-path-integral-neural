"""Frozen group-isolated data generation for conditional continuation fitting."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[key] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from conditional_boundary_dataset import contract_examples
from put_exercise_boundary_pilot import fixed_contract
from timevarying_put_risk_pilot import contract as time_contract


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    for item in cfg["sources"].values():
        if hashlib.sha256(Path(item["file"]).read_bytes()).hexdigest() != item["sha256"]:
            raise RuntimeError("frozen source checksum mismatch")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    keys = ("X", "y", "A", "Dbase", "group", "strike_index", "date_index", "state_index")
    arrays = {}
    ledger_rows = []
    total = sum(len(groups) * len(cfg["cells"])
                for groups in cfg["groups_by_split"].values())
    with (out / "groups.jsonl").open("w") as ledger:
        for split, groups in cfg["groups_by_split"].items():
            for cell in cfg["cells"]:
                blocks = {key: [] for key in keys}
                with np.load(cfg["sources"][cell]["file"]) as source:
                    for group in groups:
                        started = time.perf_counter()
                        checks = []
                        group_records = 0
                        ids = source[f"{split}_{cell}_group"]
                        indices = np.flatnonzero(ids == group)
                        if len(indices) != 3:
                            raise RuntimeError("frozen group must have three strike contracts")
                        for strike_index, index in enumerate(indices):
                            features = source[f"{split}_{cell}_X"][index].copy()
                            case = (fixed_contract(features) if cell == "FB" else
                                    time_contract(features, cell)[0])
                            examples = contract_examples(features, case,
                                reference=cfg["reference"], independent=cfg["independent"],
                                coarse=cfg["coarse"], gtfk=cfg["gtfk"],
                                state_count=cfg["states_per_date"],
                                boundary_offsets=cfg.get("boundary_offsets", ()))
                            for item in examples:
                                n = len(item["y"])
                                group_records += n
                                for key in ("X", "y", "A", "Dbase"):
                                    blocks[key].append(item[key])
                                for key, value in (("group", group),
                                                   ("strike_index", strike_index),
                                                   ("date_index", item["date_index"])):
                                    blocks[key].append(np.full(n, value, dtype=int))
                                blocks["state_index"].append(np.arange(n, dtype=int))
                                checks.append(item["independent_max_abs"])
                        row = dict(split=split, cell=cell, group=group,
                                   records=group_records,
                                   independent_max_abs=max(checks),
                                   label_passed=max(checks) <= cfg["label_tolerance"],
                                   seconds=time.perf_counter()-started)
                        ledger_rows.append(row)
                        ledger.write(json.dumps(row) + "\n")
                        ledger.flush()
                        print(json.dumps(dict(completed_groups=len(ledger_rows),
                                              total_groups=total)), flush=True)
                for key in keys:
                    arrays[f"{split}_{cell}_{key}"] = np.concatenate(blocks[key], axis=0)
    np.savez_compressed(out / "train-val.npz", **arrays)
    summary = dict(completed_groups=len(ledger_rows), total_groups=total,
                   passed_groups=sum(row["label_passed"] for row in ledger_rows),
                   max_independent_change=max(row["independent_max_abs"] for row in ledger_rows),
                   data_sha256=hashlib.sha256((out / "train-val.npz").read_bytes()).hexdigest(),
                   scope="group-isolated train/validation conditional continuation labels; no fitting or test access")
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
