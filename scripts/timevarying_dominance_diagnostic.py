"""Frozen v7 single-contract diagnostic; never publishes training labels."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from timevarying_data_pilot import pde_price, sample, schedule_grid
from timevarying_bermudan import split_put


PDE_SETTINGS = ((4801, 160, 1.0), (9601, 320, 1.0),
                (14401, 640, 1.0), (19201, 1280, 1.0),
                (24001, 1280, 1.0), (19201, 2560, 1.0),
                (24001, 1280, 1.25))
SPLIT_SETTINGS = ((1601, 160, 16), (3201, 320, 24))


def same(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return bool(np.isfinite(a) and np.isfinite(b) and abs(a-b) <= 5e-15)
    return a == b


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    if cfg.get("status") != "frozen" or cfg.get("group") != 396:
        raise RuntimeError("frozen group 396 config required")
    source = Path(cfg["source_ledger"])
    if hashlib.sha256(source.read_bytes()).hexdigest() != cfg["source_sha256"]:
        raise RuntimeError("source ledger SHA-256 mismatch")
    wait = Path(cfg["source_os_wait_receipt"])
    if hashlib.sha256(wait.read_bytes()).hexdigest() != cfg["source_os_wait_sha256"]:
        raise RuntimeError("source OS wait SHA-256 mismatch")
    state = json.loads(wait.read_text())
    if state.get("termination_evidence") != "os_child_wait_status" or state.get("status") != "completed":
        raise RuntimeError("source OS child wait missing")
    with source.open() as stream:
        row = next((json.loads(line) for i, line in enumerate(stream) if i == 396), None)
    if row is None or row.get("group") != 396 or row.get("certified") is not False:
        raise RuntimeError("expected v6 uncertified row 396")
    case = sample(512, 20261044, "ood_long")[396]
    if not same(row["contract"], case):
        raise RuntimeError("frozen sample mismatch")
    if tuple(tuple(x) for x in cfg["pde_settings"]) != PDE_SETTINGS:
        raise RuntimeError("PDE setting mismatch")
    if tuple(tuple(x) for x in cfg["split_settings"]) != SPLIT_SETTINGS:
        raise RuntimeError("independent setting mismatch")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    records = []
    for j, strike in enumerate(case["strikes"]):
        dates_e = [case["exercise"][-1]]
        dates_b = case["exercise"]
        for n, rate, width in PDE_SETTINGS:
            begun = time.perf_counter()
            euro = pde_price(case, dates_e, strike, n, rate, width)
            berm = pde_price(case, dates_b, strike, n, rate, width)
            record = {"method": "pde", "strike_index": j,
                      "setting": [n, rate, width], "TE": euro, "TB": berm,
                      "TB_minus_TE": berm-euro,
                      "wall_seconds": time.perf_counter()-begun}
            records.append(record)
            with (out/"diagnostic.jsonl").open("a") as file:
                file.write(json.dumps(record)+"\n")
            print(json.dumps(record), flush=True)
        if j == 0:
            for n, rate, order in SPLIT_SETTINGS:
                begun = time.perf_counter()
                grid = schedule_grid(case, n)
                euro = float(split_put(case["schedule"], dates_e,
                                       case["maturity"], strike, grid, rate,
                                       order=order)[n//2])
                berm = float(split_put(case["schedule"], dates_b,
                                       case["maturity"], strike, grid, rate,
                                       order=order)[n//2])
                record = {"method": "independent_ou_split", "strike_index": j,
                          "setting": [n, rate, order], "TE": euro, "TB": berm,
                          "TB_minus_TE": berm-euro,
                          "wall_seconds": time.perf_counter()-begun}
                records.append(record)
                with (out/"diagnostic.jsonl").open("a") as file:
                    file.write(json.dumps(record)+"\n")
                print(json.dumps(record), flush=True)
    summary = {"stage": "time-varying dominance diagnostic v7",
               "scope": "single known failure; no training labels",
               "group": 396, "records": len(records),
               "wall_seconds": time.perf_counter()-start}
    (out/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")


if __name__ == "__main__":
    main()
