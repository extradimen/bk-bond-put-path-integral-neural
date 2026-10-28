"""Exploratory, pre-freeze domain scan for the four failed time-varying groups."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import time

from timevarying_data_pilot import sample, pde_price


def one(item):
    index, case = item
    started = time.perf_counter()
    strike = case["strikes"][1]
    cells = {}
    settings = [(2401, 160, 1.5), (3201, 160, 2.0),
                (4801, 160, 3.0), (6401, 160, 4.0),
                (8001, 160, 4.0)]
    for cell, dates in (("TE", [case["exercise"][-1]]),
                        ("TB", case["exercise"])):
        cells[cell] = [pde_price(case, dates, strike, *s) for s in settings]
    return {"group": index, "strike": strike, "contract": case,
            "settings": settings, "cells": cells,
            "seconds": time.perf_counter() - started}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    cases = sample(cfg["source_groups"], cfg["source_seed"])
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=cfg["workers"]) as pool, \
            (out / "groups.jsonl").open("w") as ledger:
        for result in pool.map(one, ((i, cases[i]) for i in cfg["indices"])):
            ledger.write(json.dumps(result) + "\n")
            ledger.flush()
            print(json.dumps({"group": result["group"],
                              "seconds": result["seconds"]}), flush=True)
    (out / "summary.json").write_text(json.dumps({
        "groups": cfg["indices"],
        "elapsed_seconds": time.perf_counter() - started,
        "scope": "exploratory domain diagnosis; no formal label or fit"
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
