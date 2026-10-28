"""Frozen paired T-E/T-B put labels with per-contract numerical gates."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import signal
import time

import numpy as np

from timevarying_data_pilot import one as pilot_one, sample, pde_price, gtfk_price


TOL = 1e-6


def evaluate(item):
    index, case = item
    started, cpu_started = time.perf_counter(), time.process_time()
    row = pilot_one(item)
    if "error" in row:
        return row
    for contract in row["rows"]:
        strike = contract["strike"]
        for cell, dates in (("TE", [case["exercise"][-1]]),
                            ("TB", case["exercise"])):
            result = contract["cells"][cell]
            if result["reference_indicator"] > TOL:
                settings = [(9601, 320, 1.0), (14401, 320, 1.0),
                            (9601, 640, 1.0), (12001, 320, 1.25)]
                try:
                    refined = [pde_price(case, dates, strike, *s) for s in settings]
                except Exception as exc:
                    result["refinement_error"] = type(exc).__name__+": "+str(exc)
                else:
                    result["reference_fallback"] = refined
                    result["reference_fallback_settings"] = settings
                    result["reference_indicator"] = max(abs(x-refined[0]) for x in refined[1:])
            if result["gtfk_change"] > TOL:
                try:
                    finer = gtfk_price(case, dates, strike, 6401, 128, 128, 1.0)
                except Exception as exc:
                    result["gtfk_refinement_error"] = type(exc).__name__+": "+str(exc)
                else:
                    result["gtfk_fallback"] = finer
                    result["gtfk_change"] = abs(finer-result["gtfk"][-1])
        euro = contract["cells"]["TE"]
        berm = contract["cells"]["TB"]
        def chosen(r):
            return r["reference_fallback"][0] if "reference_fallback" in r else r["reference"][0]
        values = [chosen(euro), chosen(berm), *euro["gtfk"],
                  *berm["gtfk"], euro["coarse_pde"], berm["coarse_pde"]]
        contract["formal_bounds"] = (all(np.isfinite(values)) and
                                      all(-1e-8 <= x <= strike+1e-8 for x in values) and
                                      chosen(berm)+1e-8 >= chosen(euro))
        contract["formal_certified"] = contract["formal_bounds"] and all(
            r["reference_indicator"] <= TOL and r["gtfk_change"] <= TOL and
            "refinement_error" not in r and "gtfk_refinement_error" not in r
            for r in (euro, berm))
    row["certified"] = all(r["formal_certified"] for r in row["rows"])
    row["seconds"] = time.perf_counter()-started
    row["cpu_seconds"] = time.process_time()-cpu_started
    return row


def pack(rows, cell):
    x, y, a, d, group = [], [], [], [], []
    for row in rows:
        case = row["contract"]
        first, second = [interval[2] for interval in case["schedule"]]
        change = case["schedule"][0][1]
        e1, e2, e3 = case["exercise"]
        common = [np.log(first["a"]), np.log(second["a"]),
                  first["sigma"], second["sigma"], np.log(first["r0"]),
                  np.log(first["rbar"]), np.log(second["rbar"]), change]
        for contract in row["rows"]:
            r = contract["cells"][cell]
            features = ([e3, case["maturity"], contract["strike"]] if cell == "TE"
                        else [e1, e2, e3, case["maturity"], contract["strike"]])
            x.append(common+features)
            y.append(r["reference_fallback"][0] if "reference_fallback" in r else r["reference"][0])
            a.append(r.get("gtfk_fallback", r["gtfk"][-1]))
            d.append(r["coarse_pde"])
            group.append(row["group"])
    return dict(X=np.asarray(x, dtype=np.float64), y=np.asarray(y, dtype=np.float64),
                A=np.asarray(a, dtype=np.float64), Dbase=np.asarray(d, dtype=np.float64),
                group=np.asarray(group, dtype=np.int32))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    available = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count()
    if available < cfg["workers"]:
        raise RuntimeError("frozen worker count exceeds CPU affinity")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    def alarm(*_):
        raise TimeoutError("frozen time-varying data budget exceeded")
    signal.signal(signal.SIGALRM, alarm)
    signal.alarm(cfg["max_seconds"])
    arrays, failures, timing = {}, [], {}
    for split in cfg["splits"]:
        name = split["name"]
        cases = sample(split["groups"], split["seed"], split["region"])
        rows = []
        began = time.perf_counter()
        with ProcessPoolExecutor(max_workers=cfg["workers"]) as pool, \
                (out/(name+".jsonl")).open("w") as ledger:
            for row in pool.map(evaluate, enumerate(cases)):
                rows.append(row)
                ledger.write(json.dumps(row)+"\n")
                ledger.flush()
                if not row["certified"]:
                    failures.append(dict(split=name, group=row["group"], error=row.get("error"),
                                         failed_strikes=[i for i, r in enumerate(row["rows"])
                                                         if not r.get("formal_certified", False)]))
                if len(rows) % 64 == 0:
                    print(json.dumps(dict(split=name, groups=len(rows),
                                          failures=len(failures),
                                          elapsed_seconds=time.perf_counter()-start)), flush=True)
        timing[name] = dict(wall_seconds=time.perf_counter()-began,
                            group_cpu_seconds_sum=sum(r.get("cpu_seconds", 0) for r in rows),
                            groups=len(rows))
        if failures:
            (out/"gate-failures.json").write_text(json.dumps(failures, indent=2)+"\n")
            break
        for cell in ("TE", "TB"):
            for key, value in pack(rows, cell).items():
                arrays[name+"_"+cell+"_"+key] = value
    complete = not failures and len(timing) == len(cfg["splits"])
    summary = dict(stage="formal time-varying paired put labels",
                   complete=complete, failures=len(failures), timing=timing,
                   elapsed_seconds=time.perf_counter()-start,
                   scope="T-E and T-B labels and numerical baselines; no training")
    (out/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    if not complete:
        return
    np.savez_compressed(out/"data-fit.npz", **{k:v for k,v in arrays.items()
                                               if k.startswith("train_") or k.startswith("val_")})
    np.savez_compressed(out/"data-all.npz", **arrays)
    checks = {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (out/"data-fit.npz", out/"data-all.npz")}
    (out/"data-sha256.json").write_text(json.dumps(checks, indent=2)+"\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
