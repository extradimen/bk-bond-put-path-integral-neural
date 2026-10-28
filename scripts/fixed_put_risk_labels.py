"""Certified fixed-put local risk labels on frozen group splits; no fitting."""
import os
for k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[k] = "1"
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import signal
import time
import numpy as np
from fixed_put_risk_pilot import one


def main():
    p=argparse.ArgumentParser();p.add_argument("--config",required=True);p.add_argument("--out",required=True)
    a=p.parse_args();cfg=json.loads(Path(a.config).read_text())
    if hashlib.sha256(Path(cfg["data_file"]).read_bytes()).hexdigest()!=cfg["data_sha256"]:
        raise RuntimeError("formal put data checksum mismatch")
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    def alarm(*_):raise TimeoutError("risk label wall budget exceeded")
    signal.signal(signal.SIGALRM,alarm);signal.alarm(cfg["max_seconds"])
    started=time.perf_counter();failures=[];arrays={};timing={}
    with np.load(cfg["data_file"]) as data:
        for split,count in cfg["groups"].items():
            for cell in cfg["cells"]:
                prefix=split+"_"+cell+"_"
                x=data[prefix+"X"][:3*count]
                group=data[prefix+"group"][:3*count]
                if not np.array_equal(group,np.repeat(np.arange(count),3)):
                    raise RuntimeError("frozen group ordering mismatch")
                jobs=[(cell,g,x[3*g:3*g+3].copy(),cfg) for g in range(count)]
                results=[];began=time.perf_counter()
                with ProcessPoolExecutor(max_workers=cfg["workers"]) as pool,\
                     (out/(split+"-"+cell+".jsonl")).open("w") as ledger:
                    for row in pool.map(one,jobs):
                        results.append(row);ledger.write(json.dumps(row)+"\n");ledger.flush()
                        if not row["passed"]:
                            failures.append(dict(split=split,cell=cell,group=row["group"],
                                                 failed_coordinates=[v["coordinate"] for v in row["derivatives"] if not v["passed"]]))
                        if len(results)%32==0:
                            print(json.dumps(dict(split=split,cell=cell,done=len(results),total=count,
                                                  failures=len(failures),elapsed=time.perf_counter()-started)),flush=True)
                timing[split+"_"+cell]=dict(groups=count,wall_seconds=time.perf_counter()-began,
                                              cpu_seconds_sum=sum(r["seconds"] for r in results))
                arrays[split+"_"+cell+"_risk"]=np.concatenate(
                    [np.stack([v["reference"] for v in r["derivatives"]],axis=1) for r in results])
                arrays[split+"_"+cell+"_group"]=group.copy()
    summary=dict(scope="exploratory fixed-put risk labels, no neural fit",
                 groups=cfg["groups"],cells=cfg["cells"],failures=len(failures),
                 complete=len(failures)==0,timing=timing,elapsed_seconds=time.perf_counter()-started)
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    if failures:
        (out/"gate-failures.json").write_text(json.dumps(failures,indent=2)+"\n")
        print(json.dumps(summary),flush=True)
        return
    np.savez_compressed(out/"risk-labels.npz",**arrays)
    (out/"risk-labels.sha256").write_text(hashlib.sha256((out/"risk-labels.npz").read_bytes()).hexdigest()+"\n")
    print(json.dumps(summary),flush=True)

if __name__=="__main__":main()
