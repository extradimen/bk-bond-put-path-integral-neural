"""Frozen numerical risk-derivative pilot for piecewise BK bond puts."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[key] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from timevarying_data_pilot import pde_price


def contract(features, cell):
    a1, a2 = np.exp(features[0]), np.exp(features[1])
    sigma1, sigma2 = float(features[2]), float(features[3])
    r0, rbar1, rbar2 = np.exp(features[4]), np.exp(features[5]), np.exp(features[6])
    change = float(features[7])
    if cell == "TE":
        exercise = [float(features[8])]
        maturity = float(features[9])
    else:
        exercise = list(map(float, features[8:11]))
        maturity = float(features[11])
    schedule = [(0.0, change, dict(a=float(a1), sigma=sigma1, r0=float(r0), rbar=float(rbar1))),
                (change, maturity, dict(a=float(a2), sigma=sigma2, r0=float(r0), rbar=float(rbar2)))]
    return dict(schedule=schedule, exercise=exercise, maturity=maturity), exercise


def derivative(features, cell, strike, coordinate, h, n, rate, width):
    values = []
    for sign in (1., -1.):
        shifted = features.copy()
        shifted[coordinate] += sign*h
        case, dates = contract(shifted, cell)
        values.append(pde_price(case, dates, strike, n, rate, width))
    return (values[0]-values[1])/(2*h)


def one(cell, group, features, strike, cfg):
    started = time.perf_counter()
    rows = []
    for j, h in enumerate(cfg["h"]):
        n0, rate0, width0 = cfg["coarse"]
        n1, rate1, width1 = cfg["fine"]
        coarse = derivative(features, cell, strike, j, h/2, n0, rate0, width0)
        fine_full = derivative(features, cell, strike, j, h, n1, rate1, width1)
        fine_half = derivative(features, cell, strike, j, h/2, n1, rate1, width1)
        record = dict(coordinate=cfg["coordinates"][j], reference=fine_half,
                      step_change=abs(fine_half-fine_full),
                      space_change=abs(fine_half-coarse))
        if j in cfg["extra_axes"]:
            nt, rt, wt = cfg["time_refined"]
            nd, rd, wd = cfg["domain_refined"]
            record["time_change"] = abs(fine_half-derivative(features, cell, strike, j, h/2, nt, rt, wt))
            record["domain_change"] = abs(fine_half-derivative(features, cell, strike, j, h/2, nd, rd, wd))
        record["passed"] = all(value <= cfg["tolerance"] for key, value in record.items() if key.endswith("_change"))
        rows.append(record)
    return dict(cell=cell, group=group, strike_index=1, strike=strike,
                derivatives=rows, passed=all(r["passed"] for r in rows),
                seconds=time.perf_counter()-started)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    source = Path(cfg["data_file"])
    if hashlib.sha256(source.read_bytes()).hexdigest() != cfg["data_sha256"]:
        raise RuntimeError("frozen data checksum mismatch")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    results = []
    with np.load(source) as data, (out/"risk.jsonl").open("w") as ledger:
        for cell in cfg["cells"]:
            prefix = cfg["split"]+"_"+cell+"_"
            groups = data[prefix+"group"]
            for group in cfg["groups"]:
                rows = np.flatnonzero(groups == group)
                if len(rows) != 3:
                    raise RuntimeError("expected three strikes in frozen group")
                x = data[prefix+"X"][rows[1]].copy()
                result = one(cell, group, x, float(x[-1]), cfg)
                results.append(result)
                ledger.write(json.dumps(result)+"\n")
                ledger.flush()
                print(json.dumps(dict(cell=cell, completed_groups=len(results),
                                      total_groups=len(cfg["cells"])*len(cfg["groups"]))), flush=True)
    summary = dict(groups=len(results), passed=sum(r["passed"] for r in results),
                   failures=[dict(cell=r["cell"], group=r["group"],
                                  coordinates=[v["coordinate"] for v in r["derivatives"] if not v["passed"]])
                             for r in results if not r["passed"]],
                   max_changes={key:max(v[key] for r in results for v in r["derivatives"] if key in v)
                                for key in ("step_change", "space_change", "time_change", "domain_change")},
                   scope="exploratory numerical derivative pilot; only representative time/domain axes")
    (out/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
