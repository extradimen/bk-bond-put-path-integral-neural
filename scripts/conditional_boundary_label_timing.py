"""Pre-freeze conditional continuation label quality and cost pilot."""
import os
for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[name] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from conditional_boundary_reference_pilot import one
from put_exercise_boundary_pilot import fixed_contract
from timevarying_put_risk_pilot import contract as time_contract


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    cfg=json.loads(Path(a.config).read_text())
    for src in cfg["sources"].values():
        if hashlib.sha256(Path(src["file"]).read_bytes()).hexdigest()!=src["sha256"]:
            raise RuntimeError("frozen input SHA-256 mismatch")
    out=Path(a.out)
    out.mkdir(parents=True,exist_ok=False)
    total=sum(len(groups)*len(cfg["cells"]) for groups in cfg["groups_by_split"].values())
    rows=[]
    with (out/"quality.jsonl").open("w") as ledger:
        for split,groups in cfg["groups_by_split"].items():
            for cell in cfg["cells"]:
                with np.load(cfg["sources"][cell]["file"]) as data:
                    for group in groups:
                        index=3*group+1
                        x=data[f"{split}_{cell}_X"][index].copy()
                        if data[f"{split}_{cell}_group"][index]!=group:
                            raise RuntimeError("split/group identity mismatch")
                        case=fixed_contract(x) if cell=="FB" else time_contract(x,cell)[0]
                        began=time.perf_counter()
                        records,_=one(case,float(x[-1]),cfg)
                        label_passed=(all(r["continuation_space_change"]<=cfg["continuation_tolerance"] and
                                          r["continuation_independent_change"]<=cfg["continuation_tolerance"]
                                          for r in records) and bool(records[-1]["last_continuation_zero"]))
                        root_qualified=all(len(r["pde_root_log_rate"])==len(r["split_root_log_rate"])==1 and
                                           r["root_difference_short_rate"]<=cfg["root_tolerance"]
                                           for r in records)
                        row=dict(split=split,cell=cell,group=group,label_passed=label_passed,
                                 root_qualified=root_qualified,records=records,
                                 seconds=time.perf_counter()-began)
                        rows.append(row)
                        ledger.write(json.dumps(row)+"\n")
                        ledger.flush()
                        print(json.dumps(dict(completed_groups=len(rows),total_groups=total)),flush=True)
    (out/"summary.json").write_text(json.dumps(dict(completed_groups=len(rows),total_groups=total,
        label_passed_groups=sum(r["label_passed"] for r in rows),
        root_qualified_groups=sum(r["root_qualified"] for r in rows),
        median_seconds=float(np.median([r["seconds"] for r in rows])),
        max_continuation_change=max(max(max(d["continuation_space_change"],
                                         d["continuation_independent_change"]) for d in r["records"])
                                     for r in rows),
        scope="train/validation pre-freeze quality and cost pilot; no model fit"),indent=2)+"\n")


if __name__=="__main__":
    main()
