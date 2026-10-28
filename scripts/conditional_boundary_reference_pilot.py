"""Independent reference check for state-conditioned continuation labels."""
import os
for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[name] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from conditional_boundary import conditional_curves
from put_exercise_boundary_pilot import fixed_contract, roots
from timevarying_data_pilot import schedule_grid
from timevarying_put_risk_pilot import contract as time_contract


def calculate(case, strike, setting, method):
    grid = schedule_grid(case, setting[0], setting[2])
    curves = conditional_curves(case, strike, grid, method, rate=setting[1],
                                 order=(setting[3] if method == "split" else 24))
    return grid, curves


def one(case, strike, cfg):
    results = [calculate(case,strike,s,"pde") for s in cfg["pde_settings"]]
    independent = calculate(case,strike,cfg["split_setting"],"split")
    coarse_grid, coarse = results[0]
    fine_grid, fine = results[-1]
    split_grid, split = independent
    interior = np.linspace(fine_grid[0]+.1*(fine_grid[-1]-fine_grid[0]),
                           fine_grid[-1]-.1*(fine_grid[-1]-fine_grid[0]),
                           cfg["evaluation_states"])
    records = []
    for i,(a,b,c) in enumerate(zip(coarse,fine,split)):
        coarse_values = np.interp(interior,coarse_grid,a["continuation"])
        fine_values = np.interp(interior,fine_grid,b["continuation"])
        split_values = np.interp(interior,split_grid,c["continuation"])
        roots_pde = roots(fine_grid,b["gap"])
        roots_split = roots(split_grid,c["gap"])
        records.append(dict(date=b["date"],kind="last_exercise" if i==len(fine)-1 else "early_exercise",
                            continuation_space_change=float(np.max(abs(coarse_values-fine_values))),
                            continuation_independent_change=float(np.max(abs(split_values-fine_values))),
                            pde_root_log_rate=roots_pde,split_root_log_rate=roots_split,
                            root_difference_short_rate=(abs(np.exp(roots_pde[0])-np.exp(roots_split[0]))
                                                        if len(roots_pde)==len(roots_split)==1 else None),
                            last_continuation_zero=bool(np.all(b["continuation"]==0)) if i==len(fine)-1 else None))
    passed = bool(records[-1]["last_continuation_zero"]) and all(r["continuation_space_change"]<=cfg["continuation_tolerance"] and
                 r["continuation_independent_change"]<=cfg["continuation_tolerance"] and
                 len(r["pde_root_log_rate"])==len(r["split_root_log_rate"])==1 and
                 r["root_difference_short_rate"]<=cfg["root_tolerance"] for r in records)
    return records,passed


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config",required=True)
    p.add_argument("--out",required=True)
    a = p.parse_args()
    cfg = json.loads(Path(a.config).read_text())
    for source in cfg["sources"].values():
        if hashlib.sha256(Path(source["file"]).read_bytes()).hexdigest()!=source["sha256"]:
            raise RuntimeError("frozen dataset SHA-256 mismatch")
    out = Path(a.out)
    out.mkdir(parents=True,exist_ok=False)
    rows = []
    total = sum(len(g) for g in cfg["groups_by_cell"].values())
    with (out/"reference.jsonl").open("w") as ledger:
        for cell,groups in cfg["groups_by_cell"].items():
            with np.load(cfg["sources"][cell]["file"]) as data:
                for group in groups:
                    index=3*group+1
                    x=data[f"test_{cell}_X"][index].copy()
                    if data[f"test_{cell}_group"][index]!=group:
                        raise RuntimeError("frozen group identity mismatch")
                    case=fixed_contract(x) if cell=="FB" else time_contract(x,cell)[0]
                    began=time.perf_counter()
                    records,passed=one(case,float(x[-1]),cfg)
                    row=dict(cell=cell,group=group,records=records,passed=passed,
                             seconds=time.perf_counter()-began)
                    rows.append(row)
                    ledger.write(json.dumps(row)+"\n")
                    ledger.flush()
                    print(json.dumps(dict(completed_groups=len(rows),total_groups=total)),flush=True)
    (out/"summary.json").write_text(json.dumps(dict(completed_groups=len(rows),total_groups=total,
        passed_groups=sum(r["passed"] for r in rows),
        scope="conditional continuation reference pilot; pre-model feasibility"),indent=2)+"\n")


if __name__=="__main__":
    main()
