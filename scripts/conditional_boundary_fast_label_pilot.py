"""Pre-freeze accuracy/cost check for cheaper conditional PDE labels."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[key] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from conditional_boundary import conditional_curves
from put_exercise_boundary_pilot import fixed_contract
from timevarying_data_pilot import schedule_grid
from timevarying_put_risk_pilot import contract as time_contract


def one(features, case, cfg):
    strike = float(features[-1])
    settings = cfg["pde_settings"]
    values = []
    for n, rate, width in settings:
        grid = schedule_grid(case, n, width)
        started = time.perf_counter()
        curves = conditional_curves(case, strike, grid, "pde", rate=rate)
        values.append((grid, curves, time.perf_counter()-started))
    fine_grid, fine_curves, _ = values[-1]
    states = np.linspace(fine_grid[0]+cfg["domain_margin"]*np.ptp(fine_grid),
                         fine_grid[-1]-cfg["domain_margin"]*np.ptp(fine_grid),
                         cfg["states_per_date"])
    records = []
    for j in range(len(case["exercise"])-1):
        fine = np.interp(states, fine_grid, fine_curves[j]["continuation"])
        errors = [float(np.max(abs(fine-np.interp(states, grid,
                          curves[j]["continuation"])))) for grid, curves, _ in values[:-1]]
        records.append(dict(date_index=j, max_abs_by_lower_setting=errors))
    return dict(records=records, seconds_by_setting=[float(v[2]) for v in values])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    cfg = json.loads(Path(a.config).read_text())
    for item in cfg["sources"].values():
        if hashlib.sha256(Path(item["file"]).read_bytes()).hexdigest() != item["sha256"]:
            raise RuntimeError("frozen source checksum mismatch")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    total = sum(len(g) for g in cfg["groups_by_cell"].values())
    with (out / "groups.jsonl").open("w") as ledger:
        for cell, groups in cfg["groups_by_cell"].items():
            with np.load(cfg["sources"][cell]["file"]) as data:
                ids = data[f"train_{cell}_group"]
                for group in groups:
                    indices = np.flatnonzero(ids == group)
                    if len(indices) != 3:
                        raise RuntimeError("group must have three strikes")
                    strikes = []
                    for strike_index, index in enumerate(indices):
                        features = data[f"train_{cell}_X"][index].copy()
                        case = (fixed_contract(features) if cell == "FB" else
                                time_contract(features, cell)[0])
                        strikes.append(dict(strike_index=strike_index,
                            **one(features, case, cfg)))
                    row = dict(cell=cell, group=group, strikes=strikes)
                    rows.append(row)
                    ledger.write(json.dumps(row)+"\n")
                    ledger.flush()
                    print(json.dumps(dict(completed_groups=len(rows),total_groups=total)),flush=True)
    all_errors = [[d["max_abs_by_lower_setting"][k] for row in rows
                   for strike in row["strikes"] for d in strike["records"]]
                  for k in range(len(cfg["pde_settings"])-1)]
    (out / "summary.json").write_text(json.dumps(dict(completed_groups=len(rows),
        total_groups=total, max_abs_by_lower_setting=[max(e) for e in all_errors],
        passed_by_lower_setting=[max(e)<=cfg["tolerance"] for e in all_errors],
        median_seconds_by_setting=[float(np.median([strike["seconds_by_setting"][k]
            for row in rows for strike in row["strikes"]]))
            for k in range(len(cfg["pde_settings"]))],
        scope="train-only cheaper-label pre-freeze pilot; no model fit"),indent=2)+"\n")


if __name__ == "__main__":
    main()
