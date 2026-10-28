"""Validation-only T-E/T-B PDE grid scan for E2 error matching."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[key] = "1"
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from timevarying_put_online_cost import contract
from timevarying_data_pilot import pde_price


def one(job):
    cell, group, x, truth, a, dbase, grids = job
    case, dates = contract(x[0], cell)
    rows = []
    for n, rate in grids:
        start = time.perf_counter()
        price = np.asarray([pde_price(case, dates, float(k), n, rate, 1.0) for k in x[:, -1]])
        if n == 201 and rate == 100 and np.max(abs(price-dbase)) > 1e-6:
            raise RuntimeError("201/100 PDE fails frozen Dbase reproduction")
        rows.append({"n": n, "rate": rate, "prices": price.tolist(),
                     "seconds": time.perf_counter()-start,
                     "group_mae": float(np.mean(abs(price-truth)))})
    return {"cell": cell, "group": group, "a_group_mae": float(np.mean(abs(a-truth))), "grids": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    source = Path(cfg["data_file"])
    if hashlib.sha256(source.read_bytes()).hexdigest() != cfg["data_sha256"]:
        raise RuntimeError("frozen data checksum mismatch")
    jobs = []
    with np.load(source) as data:
        for cell in cfg["cells"]:
            stem = "val_" + cell + "_"
            x, y, a, d = (data[stem + k] for k in ("X", "y", "A", "Dbase"))
            groups = data[stem + "group"]
            for g in cfg["validation_groups"]:
                ix = np.flatnonzero(groups == g)
                if len(ix) != 3:
                    raise RuntimeError("expected three strikes per group")
                jobs.append((cell, g, x[ix].copy(), y[ix].copy(), a[ix].copy(), d[ix].copy(), cfg["grids"]))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    results = []
    with ProcessPoolExecutor(max_workers=cfg["workers"]) as pool, (out/"groups.jsonl").open("w") as ledger:
        for row in pool.map(one, jobs):
            results.append(row)
            ledger.write(json.dumps(row)+"\n")
            ledger.flush()
    summary = {"completed_groups": len(results), "frozen_groups": len(jobs), "cells": {}}
    for cell in cfg["cells"]:
        subset = [r for r in results if r["cell"] == cell]
        a_mae = float(np.mean([r["a_group_mae"] for r in subset]))
        candidates = [{"n": n, "rate": rate,
                       "validation_mae": float(np.mean([r["grids"][i]["group_mae"] for r in subset])),
                       "group_seconds_median": float(np.median([r["grids"][i]["seconds"] for r in subset]))}
                      for i, (n, rate) in enumerate(cfg["grids"])]
        chosen = min(candidates, key=lambda r: (abs(r["validation_mae"]-a_mae),
                                                 r["group_seconds_median"], r["n"]))
        summary["cells"][cell] = {"groups": len(subset), "a_validation_mae": a_mae,
                                   "candidates": candidates, "error_matched_pde": chosen}
    summary["scope"] = "Validation-only error-matching exploratory scan; test set untouched."
    (out/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps({"completed_groups": summary["completed_groups"],
                      "frozen_groups": summary["frozen_groups"]}), flush=True)


if __name__ == "__main__":
    main()
