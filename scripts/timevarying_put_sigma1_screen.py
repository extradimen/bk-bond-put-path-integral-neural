"""Frozen spread-sample GTFK sigma1 derivative screen against PDE labels."""
import os
for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[name] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from timevarying_data_pilot import gtfk_price
from timevarying_put_risk_pilot import contract


def derivative(x, cell, h, setting):
    shifted = []
    for sign in (+1, -1):
        y = x.copy()
        y[2] += sign*h
        case, dates = contract(y, cell)
        shifted.append(gtfk_price(case, dates, float(x[-1]), *setting))
    return (shifted[0]-shifted[1])/(2*h)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    cfg = json.loads(Path(a.config).read_text())
    for key in ("data", "labels"):
        source = cfg["sources"][key]
        if hashlib.sha256(Path(source["file"]).read_bytes()).hexdigest() != source["sha256"]:
            raise RuntimeError(f"{key} SHA-256 mismatch")
    references = {}
    for line in Path(cfg["sources"]["labels"]["file"]).open():
        row = json.loads(line)
        if row["cell"] == cfg["cell"] and row["group"] in cfg["groups"]:
            if row["group"] in references or not row["passed"] or row["strike_index"] != 1:
                raise RuntimeError("reference identity or certification invalid")
            references[row["group"]] = row
    if set(references) != set(cfg["groups"]):
        raise RuntimeError("frozen reference groups missing")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    with np.load(cfg["sources"]["data"]["file"]) as data, (out/"screen.jsonl").open("w") as ledger:
        for group in cfg["groups"]:
            index = 3*group+1
            x = data[f"test_{cfg['cell']}_X"][index].copy()
            if data[f"test_{cfg['cell']}_group"][index] != group:
                raise RuntimeError("frozen group identity mismatch")
            ref = references[group]
            if not np.isclose(x[-1], ref["strike"]):
                raise RuntimeError("frozen strike mismatch")
            sigma = next(d for d in ref["derivatives"] if d["coordinate"] == "sigma1")
            if not sigma["passed"]:
                raise RuntimeError("PDE sigma1 reference uncertified")
            t = time.perf_counter()
            low = derivative(x, cfg["cell"], cfg["h"], cfg["settings"][0])
            low_half = derivative(x, cfg["cell"], cfg["h"]/2, cfg["settings"][0])
            high = derivative(x, cfg["cell"], cfg["h"], cfg["settings"][1])
            record = dict(group=group, low=low, low_half=low_half, high=high,
                          pde_reference=float(sigma["reference"]),
                          step_change=abs(low-low_half), grid_change=abs(low-high),
                          method_difference=abs(high-sigma["reference"]),
                          numerically_stable=max(abs(low-low_half),abs(low-high))<=cfg["numerical_tolerance"],
                          seconds=time.perf_counter()-t)
            ledger.write(json.dumps(record)+"\n")
            ledger.flush()
            rows.append(record)
            print(json.dumps(dict(completed_groups=len(rows), total_groups=len(cfg["groups"]))), flush=True)
    (out/"summary.json").write_text(json.dumps(dict(
        completed_groups=len(rows), total_groups=len(cfg["groups"]),
        stable_groups=sum(r["numerically_stable"] for r in rows),
        max_method_difference=max(r["method_difference"] for r in rows),
        median_method_difference=float(np.median([r["method_difference"] for r in rows])),
        numerical_tolerance=cfg["numerical_tolerance"],
        scope="exploratory spread sample, not full-distribution certification"),indent=2)+"\n")


if __name__ == "__main__":
    main()
