"""Checksum-pinned recovery of F-E/F-B labels after one train GTFK gate miss."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[key] = "1"

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import signal
import time

import numpy as np

from bermudan_gtfk_split_pilot import price as gtfk_bermudan
from fb_data_pilot import one, sample
from fixed_put_formal_data import pack


TOL = 1e-6
NEW_SETTINGS = [(3201,192,96,.75), (4801,192,96,.75), (4801,192,96,1.0)]


def refine(row, strike_index):
    started, cpu_started = time.perf_counter(), time.process_time()
    c = row["contract"]
    r = row["rows"][strike_index]
    try:
        values = [float(gtfk_bermudan(c["model"], c["exercise"], c["maturity"],
                                         r["strike"], *setting))
                  for setting in NEW_SETTINGS]
        r["gtfk_settings"].extend(NEW_SETTINGS)
        r["gtfk_values"].extend(values)
        r["gtfk_bermudan"] = values[1]
        r["gtfk_numerical_indicator"] = max(abs(values[1]-values[0]),
                                             abs(values[2]-values[1]))
        prices = [r["reference"]["price"], r["european_reference"]["price"],
                  r["gtfk_bermudan"], r["gtfk_european"], r["coarse_pde"],
                  r["coarse_european_pde"]]
        r["bounds"] = bool(all(np.isfinite(prices)) and
                           min(prices) >= 0 and max(prices) <= r["strike"]+1e-8)
    except Exception as exc:
        r["refinement_error"] = type(exc).__name__+": "+str(exc)
    row["seconds"] += time.perf_counter()-started
    row["cpu_seconds"] += time.process_time()-cpu_started


def certify(row):
    row["certified"] = all(r["reference"]["certified"] and
                           r["european_reference"]["certified"] and
                           r["gtfk_numerical_indicator"] <= TOL and
                           r["gtfk_european_numerical_indicator"] <= TOL and
                           r["monotonic"] and r["bounds"] and
                           "refinement_error" not in r
                           for r in row["rows"])
    return row


def evaluate(item):
    row = one(item)
    if "error" not in row:
        for j, r in enumerate(row["rows"]):
            if r["gtfk_numerical_indicator"] > TOL:
                refine(row, j)
        certify(row)
    return row


def failed_strikes(row):
    return [i for i,r in enumerate(row["rows"])
            if not (r["reference"]["certified"] and
                    r["european_reference"]["certified"] and
                    r["gtfk_numerical_indicator"] <= TOL and
                    r["gtfk_european_numerical_indicator"] <= TOL and
                    r["monotonic"] and r["bounds"] and
                    "refinement_error" not in r)]


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
    started = time.perf_counter()
    def alarm(*_):
        raise TimeoutError("fixed-put recovery exceeded frozen wall budget")
    signal.signal(signal.SIGALRM, alarm)
    signal.alarm(cfg["max_seconds"])
    source = Path(cfg["source_train_file"])
    if hashlib.sha256(source.read_bytes()).hexdigest() != cfg["source_train_sha256"]:
        raise RuntimeError("v1 train ledger checksum mismatch")
    rows = [json.loads(line) for line in source.open()]
    original = sample(4096, cfg["train_seed"], "main")
    if len(rows) != 4096 or any(row["group"] != i or row["contract"] != original[i]
                                for i,row in enumerate(rows)):
        raise RuntimeError("v1 train identities or contracts mismatch")
    failed = [row["group"] for row in rows if not row["certified"]]
    if failed != [cfg["repair_group"]] or failed_strikes(rows[cfg["repair_group"]]) != [0]:
        raise RuntimeError("v1 failure set differs from registered repair")
    refine(rows[cfg["repair_group"]], 0)
    certify(rows[cfg["repair_group"]])
    failures = []
    if not rows[cfg["repair_group"]]["certified"]:
        failures.append(dict(split="train", group=cfg["repair_group"],
                             failed_strikes=failed_strikes(rows[cfg["repair_group"]])))
    with (out/"train.jsonl").open("w") as ledger:
        for row in rows:
            ledger.write(json.dumps(row)+"\n")
    timing = {"train":dict(groups=4096, reused_groups=4095,
                           refined_groups=1, source_sha256=cfg["source_train_sha256"])}
    arrays = {}
    if not failures:
        for cell in ("FE", "FB"):
            for key, value in pack(rows, cell).items():
                arrays["train_"+cell+"_"+key] = value
    del rows, original
    for split in cfg["splits"] if not failures else []:
        name = split["name"]
        cases = sample(split["groups"], split["seed"], split["region"])
        began, rows = time.perf_counter(), []
        with ProcessPoolExecutor(max_workers=cfg["workers"]) as pool, \
                (out/(name+".jsonl")).open("w") as ledger:
            for row in pool.map(evaluate, enumerate(cases)):
                rows.append(row)
                ledger.write(json.dumps(row)+"\n")
                ledger.flush()
                if not row["certified"]:
                    failures.append(dict(split=name, group=row["group"],
                                         error=row.get("error"),
                                         failed_strikes=failed_strikes(row)))
                if len(rows)%64 == 0:
                    print(json.dumps(dict(split=name, groups=len(rows),
                                          failures=len(failures),
                                          elapsed_seconds=time.perf_counter()-started)), flush=True)
        timing[name] = dict(groups=len(rows), wall_seconds=time.perf_counter()-began,
                            group_cpu_seconds_sum=sum(r["cpu_seconds"] for r in rows))
        if failures:
            break
        for cell in ("FE", "FB"):
            for key, value in pack(rows, cell).items():
                arrays[name+"_"+cell+"_"+key] = value
    complete = not failures and len(timing) == 1+len(cfg["splits"])
    if failures:
        (out/"gate-failures.json").write_text(json.dumps(failures, indent=2)+"\n")
    summary = dict(stage="fixed-put formal recovery v2", complete=complete,
                   failures=len(failures), timing=timing,
                   elapsed_seconds=time.perf_counter()-started,
                   scope="F-E/F-B paired labels; no model training")
    (out/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    if not complete:
        return
    np.savez_compressed(out/"data-fit.npz", **{k:v for k,v in arrays.items()
                                               if k.startswith("train_") or k.startswith("val_")})
    np.savez_compressed(out/"data-all.npz", **arrays)
    checks = {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (out/"data-fit.npz",out/"data-all.npz")}
    (out/"data-sha256.json").write_text(json.dumps(checks, indent=2)+"\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
