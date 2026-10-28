"""Independent OU-split crosscheck for frozen T-E/T-B formal labels."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from timevarying_data_pilot import schedule_grid
from timevarying_bermudan import split_put


def check(item):
    split, group, j, cell, case, strike, reference, settings = item
    started = time.perf_counter()
    exercise = [case["exercise"][-1]] if cell == "TE" else case["exercise"]
    x0 = np.log(case["schedule"][0][2]["r0"])
    prices = []
    try:
        for n, rate, order in settings:
            grid = schedule_grid(case, n)
            prices.append(float(np.interp(x0, grid, split_put(
                case["schedule"], exercise, case["maturity"], strike,
                grid, rate, order=order))))
        return dict(split=split, group=group, strike_index=j, cell=cell,
                    reference=reference, prices=prices,
                    difference=prices[-1]-reference,
                    refinement_change=prices[-1]-prices[-2],
                    seconds=time.perf_counter()-started)
    except Exception as exc:
        return dict(split=split, group=group, strike_index=j, cell=cell,
                    reference=reference, prices=prices,
                    error=type(exc).__name__+": "+str(exc),
                    seconds=time.perf_counter()-started)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    source = Path(cfg["data_file"])
    if hashlib.sha256(source.read_bytes()).hexdigest() != cfg["data_all_sha256"]:
        raise RuntimeError("formal time-varying data checksum mismatch")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    items = []
    with np.load(source) as data:
        for split, groups in cfg["selected_groups"].items():
            for group in groups:
                strike_indices = (0, 1, 2) if group == 0 else (1,)
                for j in strike_indices:
                    row = 3*group+j
                    f = data[split+"_TB_X"][row]
                    a1, a2 = np.exp(f[0]), np.exp(f[1])
                    s1, s2 = f[2], f[3]
                    r0, r1, r2 = np.exp(f[4]), np.exp(f[5]), np.exp(f[6])
                    change = float(f[7])
                    e1, e2, e3, maturity, strike = map(float, f[8:13])
                    case = dict(schedule=[(0.0, change, dict(a=float(a1),sigma=float(s1),
                                                             r0=float(r0),rbar=float(r1))),
                                          (change, maturity, dict(a=float(a2),sigma=float(s2),
                                                                  r0=float(r0),rbar=float(r2)))],
                                exercise=[e1,e2,e3], maturity=maturity)
                    for cell in ("TE", "TB"):
                        reference = float(data[split+"_"+cell+"_y"][row])
                        items.append((split,group,j,cell,case,strike,reference,cfg["settings"]))
    began = time.perf_counter()
    with ProcessPoolExecutor(max_workers=cfg["workers"]) as pool, \
            (out/"checks.jsonl").open("w") as ledger:
        rows = []
        for row in pool.map(check, items):
            rows.append(row)
            ledger.write(json.dumps(row)+"\n")
            ledger.flush()
    failures = [r for r in rows if r.get("error") or
                abs(r["difference"]) > cfg["tolerance"] or
                abs(r["refinement_change"]) > cfg["tolerance"]]
    summary = dict(cases=len(rows), failures=len(failures), passed=not failures,
                   elapsed_seconds=time.perf_counter()-began,
                   tolerance=cfg["tolerance"], scope="formal independent split check")
    (out/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    (out/"failures.json").write_text(json.dumps(failures, indent=2)+"\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
