"""Pre-freeze independent OU-split check of T-E/T-B pilot contracts."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import time

import numpy as np

from timevarying_data_pilot import pde_price, sample, schedule_grid
from timevarying_bermudan import split_put


def check(item):
    region, seed, index, case, cell, rate1, rate2, n1, n2, order = item
    start = time.perf_counter()
    dates = [case["exercise"][-1]] if cell == "TE" else case["exercise"]
    strike = case["strikes"][1]
    x0 = np.log(case["schedule"][0][2]["r0"])
    values = []
    try:
        reference = pde_price(case, dates, strike, 4801, 160, 1.0)
        for n, rate in ((n1, rate1), (n2, rate2)):
            grid = schedule_grid(case, n)
            values.append(float(np.interp(x0, grid, split_put(
                case["schedule"], dates, case["maturity"], strike,
                grid, rate, order=order))))
        return dict(region=region, seed=seed, group=index, cell=cell,
                    reference=reference, split=values,
                    split_change=abs(values[1]-values[0]),
                    reference_difference=abs(values[1]-reference),
                    seconds=time.perf_counter()-start)
    except Exception as exc:
        return dict(region=region, seed=seed, group=index, cell=cell,
                    split=values, error=type(exc).__name__+": "+str(exc),
                    seconds=time.perf_counter()-start)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    items = []
    for chosen in cfg["selected"]:
        region, seed, index = chosen["region"], chosen["seed"], chosen["group"]
        case = sample(index+1, seed, region)[index]
        for cell in ("TE", "TB"):
            items.append((region, seed, index, case, cell,
                          cfg["split_rate_1"], cfg["split_rate_2"],
                          cfg["split_n_1"], cfg["split_n_2"], cfg["order"]))
    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=cfg["workers"]) as pool:
        rows = list(pool.map(check, items))
    (out/"checks.jsonl").write_text("".join(json.dumps(r)+"\n" for r in rows))
    failures = [r for r in rows if r.get("error") or
                r["split_change"] > cfg["tolerance"] or
                r["reference_difference"] > cfg["tolerance"]]
    summary = dict(cases=len(rows), failures=len(failures),
                   passed=not failures, elapsed_seconds=time.perf_counter()-start,
                   tolerance=cfg["tolerance"],
                   scope="pre-freeze independent split check; no formal sample")
    (out/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
