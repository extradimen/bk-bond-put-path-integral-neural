"""Numerical-stability pilot for time-varying GTFK and coarse-PDE put risks."""
import os
for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[name] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from timevarying_data_pilot import gtfk_price, pde_price
from timevarying_put_online_cost import contract


def checked(path, digest):
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
        raise RuntimeError(f"frozen input checksum mismatch: {path}")


def price(cell, x, method, setting):
    case, dates = contract(x, cell)
    strike = float(x[-1])
    if method == "A":
        return gtfk_price(case, dates, strike, *setting)
    if method == "Dbase":
        return pde_price(case, dates, strike, *setting)
    raise ValueError(method)


def derivative(cell, x, method, setting, axis, h):
    left, right = x.copy(), x.copy()
    left[axis] -= h
    right[axis] += h
    return (price(cell, right, method, setting)
            - price(cell, left, method, setting)) / (2 * h)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    checked(cfg["data_file"], cfg["data_sha256"])
    checked(cfg["risk_file"], cfg["risk_sha256"])
    refs = {}
    for line in Path(cfg["risk_file"]).read_text().splitlines():
        row = json.loads(line)
        key = row["cell"], row["group"]
        if key in refs or not row["passed"] or row["strike_index"] != 1:
            raise RuntimeError(f"invalid reference row: {key}")
        refs[key] = row
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    completed = 0
    with np.load(cfg["data_file"]) as data, (out/"pilot.jsonl").open("w") as ledger:
        for cell in cfg["cells"]:
            for group in cfg["groups"]:
                key = cell, group
                if key not in refs:
                    raise RuntimeError(f"missing reference: {key}")
                ref = refs[key]
                if [d["coordinate"] for d in ref["derivatives"]] != cfg["coordinates"]:
                    raise RuntimeError(f"reference coordinate mismatch: {key}")
                index = 3 * group + 1
                x = data[f"test_{cell}_X"][index].copy()
                if data[f"test_{cell}_group"][index] != group or not np.isclose(x[-1], ref["strike"]):
                    raise RuntimeError(f"contract identity mismatch: {key}")
                started = time.perf_counter()
                methods = {}
                for method in cfg["settings"]:
                    low, high = cfg["settings"][method]
                    baseline_low = price(cell, x, method, low)
                    baseline_high = price(cell, x, method, high)
                    target = float(data[f"test_{cell}_{method}"][index])
                    coords = []
                    for axis, name in enumerate(cfg["coordinates"]):
                        h = cfg["h"][axis]
                        d_low = derivative(cell, x, method, low, axis, h)
                        d_half = derivative(cell, x, method, low, axis, h/2)
                        d_high = derivative(cell, x, method, high, axis, h)
                        coords.append(dict(coordinate=name, low=d_low, half_step=d_half,
                                           high_resolution=d_high,
                                           step_change=abs(d_low-d_half),
                                           resolution_change=abs(d_low-d_high),
                                           reference=float(ref["derivatives"][axis]["reference"])))
                    methods[method] = dict(price_low=baseline_low, price_high=baseline_high,
                                           frozen_price=target, price_check=abs(baseline_low-target),
                                           coordinates=coords)
                row = dict(cell=cell, group=group, methods=methods,
                           seconds=time.perf_counter()-started)
                ledger.write(json.dumps(row)+"\n")
                ledger.flush()
                completed += 1
                print(json.dumps(dict(completed=completed, frozen=len(cfg["cells"])*len(cfg["groups"]))), flush=True)
    summary = dict(completed=completed, frozen=len(cfg["cells"])*len(cfg["groups"]),
                   scope="exploratory numerical derivative stability; no post-hoc pass threshold")
    (out/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
