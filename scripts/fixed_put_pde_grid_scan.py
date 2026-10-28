"""Validation-only fixed-put PDE grid scan for error matching and cost frontier."""
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

from bermudan_pilot import value as pde_value


def one(job):
    group, cell, x, truth, a, dbase, grids = job
    f = x[0]
    model = dict(a=float(np.exp(f[0])), sigma=float(f[1]),
                 r0=float(np.exp(f[2])), rbar=float(np.exp(f[3])))
    if cell == "FE":
        dates = [float(f[4])]
        maturity = float(f[5])
    else:
        dates = list(map(float, f[4:7]))
        maturity = float(f[7])
    strikes = x[:, -1]
    rows = []
    for n, rate in grids:
        start = time.perf_counter()
        prices = np.asarray([pde_value(model, dates, maturity, float(k), n, rate, "put")
                             for k in strikes])
        rows.append(dict(n=n, rate=rate, prices=prices.tolist(),
                         seconds=time.perf_counter()-start,
                         group_mae=float(np.mean(abs(prices-truth)))))
        if n == 201 and rate == 100 and np.max(abs(prices-dbase)) > 1e-9:
            raise RuntimeError("201/100 PDE does not reproduce frozen Dbase")
    return dict(group=group, cell=cell, a_group_mae=float(np.mean(abs(a-truth))),
                grids=rows)


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
    jobs = []
    with np.load(source) as data:
        for cell in cfg["cells"]:
            prefix = "val_"+cell+"_"
            x, truth, a, dbase = (data[prefix+key] for key in ("X", "y", "A", "Dbase"))
            groups = data[prefix+"group"]
            for group in cfg["validation_groups"]:
                rows = np.flatnonzero(groups == group)
                if len(rows) != 3:
                    raise RuntimeError("expected three strikes per parameter group")
                jobs.append((group, cell, x[rows].copy(), truth[rows].copy(),
                             a[rows].copy(), dbase[rows].copy(), cfg["grids"]))
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=cfg["workers"]) as pool, \
            (out/"groups.jsonl").open("w") as ledger:
        results = []
        for row in pool.map(one, jobs):
            results.append(row)
            ledger.write(json.dumps(row)+"\n")
            ledger.flush()
    summary = {}
    for cell in cfg["cells"]:
        matched = [r for r in results if r["cell"] == cell]
        a_mae = float(np.mean([r["a_group_mae"] for r in matched]))
        candidates = []
        for index, (n, rate) in enumerate(cfg["grids"]):
            subset = [r["grids"][index] for r in matched]
            candidates.append(dict(n=n, rate=rate,
                                   validation_mae=float(np.mean([v["group_mae"] for v in subset])),
                                   group_seconds_median=float(np.median([v["seconds"] for v in subset])),
                                   group_seconds_mean=float(np.mean([v["seconds"] for v in subset]))))
        chosen = min(candidates, key=lambda c:(abs(c["validation_mae"]-a_mae),
                                                c["group_seconds_mean"], c["n"]))
        summary[cell] = dict(groups=len(matched), a_validation_mae=a_mae,
                             candidates=candidates, error_matched_pde=chosen)
    summary["stage_seconds"] = time.perf_counter()-started
    summary["scope"] = "validation-only candidate selection; no new test inference"
    (out/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
