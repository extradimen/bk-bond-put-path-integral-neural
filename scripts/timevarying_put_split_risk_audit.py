"""Independent OU-split finite-difference audit for a frozen put risk coordinate."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[key] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from timevarying_data_pilot import schedule_grid
from timevarying_bermudan import split_put
from timevarying_put_risk_pilot import contract


def price(features, strike, setting):
    n, rate, order, width = setting
    case, dates = contract(features, "TB")
    grid = schedule_grid(case, n, width)
    curve = split_put(case["schedule"], dates, case["maturity"], strike,
                      grid, rate, order)
    return float(curve[n//2])


def derivative(features, strike, coordinate, step, setting):
    up, down = features.copy(), features.copy()
    up[coordinate] += step
    down[coordinate] -= step
    return (price(up, strike, setting)-price(down, strike, setting))/(2*step)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    for src in cfg["sources"]:
        if hashlib.sha256(Path(src["file"]).read_bytes()).hexdigest() != src["sha256"]:
            raise RuntimeError("frozen source checksum mismatch")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    with np.load(cfg["sources"][0]["file"]) as data:
        ids = np.flatnonzero(data["test_TB_group"] == cfg["group"])
        if len(ids) != 3:
            raise RuntimeError("expected three strikes")
        x = data["test_TB_X"][ids[1]].copy()
    label = None
    for line in Path(cfg["sources"][1]["file"]).open():
        row = json.loads(line)
        if row.get("cell") == "TB" and row.get("group") == cfg["group"]:
            label = next(v for v in row["derivatives"] if v["coordinate"] == cfg["coordinate_name"])
            break
    if label is None or not label.get("passed"):
        raise RuntimeError("frozen certified PDE label missing")
    results = []
    with (out/"audit.jsonl").open("w") as ledger:
        for setting in cfg["split_settings"]:
            began = time.perf_counter()
            full = derivative(x, float(x[-1]), cfg["coordinate_index"], cfg["h"], setting)
            half = derivative(x, float(x[-1]), cfg["coordinate_index"], cfg["h"]/2, setting)
            row = dict(setting=setting, full_step=full, half_step=half,
                       step_change=abs(full-half),
                       pde_label=float(label["reference"]),
                       pde_difference=abs(half-label["reference"]),
                       seconds=time.perf_counter()-began)
            ledger.write(json.dumps(row)+"\n")
            ledger.flush()
            results.append(row)
            print(json.dumps(dict(completed_groups=len(results),
                                  total_groups=len(cfg["split_settings"]))), flush=True)
    fine = results[-1]
    summary = dict(settings=len(results), space_change=abs(results[-1]["half_step"]-results[-2]["half_step"]),
                   fine_step_change=fine["step_change"],
                   fine_pde_difference=fine["pde_difference"],
                   tolerance=cfg["tolerance"],
                   passed=max(abs(results[-1]["half_step"]-results[-2]["half_step"]),
                              fine["step_change"],fine["pde_difference"])<=cfg["tolerance"])
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")


if __name__ == "__main__":
    main()
