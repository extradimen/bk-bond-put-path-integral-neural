"""Pilot independently refined BK put sensitivities at fixed contracts."""
import os
for k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[k] = "1"
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from bermudan_pilot import value as pde_value


def one(job):
    cell, group, x, cfg = job
    f = x[0]
    model = dict(a=float(np.exp(f[0])), sigma=float(f[1]),
                 r0=float(np.exp(f[2])), rbar=float(np.exp(f[3])))
    dates = [float(f[4])] if cell == "FE" else list(map(float, f[4:7]))
    maturity = float(f[5] if cell == "FE" else f[7])
    strikes = x[:, -1]
    started = time.perf_counter()
    def shift(j, h):
        c = model.copy()
        if j == 0: c["a"] *= np.exp(h)
        elif j == 1: c["sigma"] += h
        elif j == 2: c["r0"] *= np.exp(h)
        else: c["rbar"] *= np.exp(h)
        return c
    def prices(c, n, rate):
        return np.array([pde_value(c, dates, maturity, float(k), n, rate, "put") for k in strikes])
    vals = []
    for j, h0 in enumerate(cfg["h"]):
        deriv = []
        for n, rate in cfg["grids"]:
            for h in (h0, h0/2):
                deriv.append((prices(shift(j,h),n,rate)-prices(shift(j,-h),n,rate))/(2*h))
        step = float(np.max(abs(deriv[-1]-deriv[-2])))
        grid = float(np.max(abs(deriv[-1]-deriv[1])))
        vals.append(dict(coordinate=cfg["coordinates"][j], reference=deriv[-1].tolist(),
                         step_change=step, grid_change=grid,
                         passed=max(step,grid) <= cfg["tolerance"]))
    return dict(cell=cell, group=group, derivatives=vals,
                passed=all(v["passed"] for v in vals), seconds=time.perf_counter()-started)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    cfg=json.loads(Path(a.config).read_text())
    if hashlib.sha256(Path(cfg["data_file"]).read_bytes()).hexdigest()!=cfg["data_sha256"]:
        raise RuntimeError("input SHA mismatch")
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    jobs=[]
    with np.load(cfg["data_file"]) as data:
        for cell in cfg["cells"]:
            pre="train_"+cell+"_"
            x=data[pre+"X"]; group=data[pre+"group"]
            for g in cfg["groups"]:
                rows=np.flatnonzero(group==g)
                if len(rows)!=3:raise RuntimeError("expected three strikes")
                jobs.append((cell,g,x[rows].copy(),cfg))
    started=time.perf_counter();rows=[]
    with ProcessPoolExecutor(max_workers=cfg["workers"]) as pool, (out/"risk.jsonl").open("w") as ledger:
        for row in pool.map(one,jobs):
            rows.append(row);ledger.write(json.dumps(row)+"\n");ledger.flush()
    summary=dict(total=len(rows),passed=sum(r["passed"] for r in rows),
                 failed=[dict(cell=r["cell"],group=r["group"]) for r in rows if not r["passed"]],
                 max_step_change=max(v["step_change"] for r in rows for v in r["derivatives"]),
                 max_grid_change=max(v["grid_change"] for r in rows for v in r["derivatives"]),
                 elapsed_seconds=time.perf_counter()-started,
                 scope="risk-label numerical pilot only; no neural training")
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary),flush=True)

if __name__=="__main__":main()
