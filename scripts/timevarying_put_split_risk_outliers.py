"""Post-screen independent OU audit of frozen sigma1 outlier groups."""
import os
for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[name] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from timevarying_put_split_risk_audit import derivative


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    cfg = json.loads(Path(a.config).read_text())
    for name in ("data", "labels", "screen"):
        src = cfg["sources"][name]
        if hashlib.sha256(Path(src["file"]).read_bytes()).hexdigest() != src["sha256"]:
            raise RuntimeError(f"{name} SHA-256 mismatch")
    reference = {}
    for line in Path(cfg["sources"]["labels"]["file"]).open():
        row = json.loads(line)
        if row["cell"] == "TB" and row["group"] in cfg["groups"]:
            if row["group"] in reference or row["strike_index"] != 1 or not row["passed"]:
                raise RuntimeError("invalid frozen PDE reference")
            reference[row["group"]] = row
    screen = {r["group"]:r for r in map(json.loads,Path(cfg["sources"]["screen"]["file"]).open())}
    if set(reference) != set(cfg["groups"]) or not set(cfg["groups"]) <= set(screen):
        raise RuntimeError("missing frozen group")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    with np.load(cfg["sources"]["data"]["file"]) as data, (out/"audit.jsonl").open("w") as ledger:
        for group in cfg["groups"]:
            index = 3*group+1
            x = data["test_TB_X"][index].copy()
            if data["test_TB_group"][index] != group or not np.isclose(x[-1],reference[group]["strike"]):
                raise RuntimeError("frozen contract mismatch")
            pde = next(d for d in reference[group]["derivatives"] if d["coordinate"] == "sigma1")
            if not pde["passed"]:
                raise RuntimeError("uncertified PDE sigma1")
            began = time.perf_counter()
            values = []
            for setting in cfg["split_settings"]:
                full = derivative(x,float(x[-1]),2,cfg["h"],setting)
                half = derivative(x,float(x[-1]),2,cfg["h"]/2,setting)
                values.append(dict(setting=setting,full=full,half=half,step_change=abs(full-half)))
            fine = values[-1]
            row = dict(group=group,split=values,pde_reference=float(pde["reference"]),
                       gtfk_high=float(screen[group]["high"]),
                       split_pde_difference=abs(fine["half"]-pde["reference"]),
                       gtfk_split_difference=abs(screen[group]["high"]-fine["half"]),
                       space_change=abs(values[-1]["half"]-values[-2]["half"]),
                       passed=max(fine["step_change"],abs(values[-1]["half"]-values[-2]["half"]),
                                  abs(fine["half"]-pde["reference"]))<=cfg["tolerance"],
                       seconds=time.perf_counter()-began)
            ledger.write(json.dumps(row)+"\n")
            ledger.flush()
            rows.append(row)
            print(json.dumps(dict(completed_groups=len(rows),total_groups=len(cfg["groups"]))),flush=True)
    (out/"summary.json").write_text(json.dumps(dict(completed_groups=len(rows),
        total_groups=len(cfg["groups"]),passed_groups=sum(r["passed"] for r in rows),
        max_split_pde_difference=max(r["split_pde_difference"] for r in rows),
        min_gtfk_split_difference=min(r["gtfk_split_difference"] for r in rows),
        tolerance=cfg["tolerance"],scope="post-screen outlier diagnosis, not independent holdout"),indent=2)+"\n")


if __name__ == "__main__":
    main()
