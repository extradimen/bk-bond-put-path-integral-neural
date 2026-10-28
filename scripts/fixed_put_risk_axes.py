"""Separate space, time, domain and finite-difference axes for put risks."""
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
    f=x[0]
    base=dict(a=float(np.exp(f[0])),sigma=float(f[1]),
              r0=float(np.exp(f[2])),rbar=float(np.exp(f[3])))
    dates=[float(f[4])] if cell=="FE" else list(map(float,f[4:7]))
    maturity=float(f[5] if cell=="FE" else f[7])
    strikes=x[:,-1]
    def shift(j,h):
        c=base.copy()
        if j==0:c["a"]*=np.exp(h)
        elif j==1:c["sigma"]+=h
        elif j==2:c["r0"]*=np.exp(h)
        else:c["rbar"]*=np.exp(h)
        return c
    def deriv(j,h,n,rate,width):
        return np.array([(pde_value(shift(j,h),dates,maturity,float(k),n,rate,"put",width)-
                          pde_value(shift(j,-h),dates,maturity,float(k),n,rate,"put",width))/(2*h)
                         for k in strikes])
    started=time.perf_counter();rows=[]
    n,rate=cfg["base_grid"]
    for j,h0 in enumerate(cfg["h"]):
        h=h0/2
        values={"base":deriv(j,h,n,rate,1.),
                "step":deriv(j,h/2,n,rate,1.),
                "space":deriv(j,h,cfg["space_grid"][0],cfg["space_grid"][1],1.),
                "time":deriv(j,h,cfg["time_grid"][0],cfg["time_grid"][1],1.),
                "domain":deriv(j,h,cfg["domain_grid"][0],cfg["domain_grid"][1],cfg["domain_width"])}
        changes={key:float(np.max(abs(val-values["base"]))) for key,val in values.items() if key!="base"}
        rows.append(dict(coordinate=cfg["coordinates"][j],base=values["base"].tolist(),
                         changes=changes,dominant=max(changes,key=changes.get)))
    return dict(cell=cell,group=group,risks=rows,seconds=time.perf_counter()-started)


def main():
    p=argparse.ArgumentParser();p.add_argument("--config",required=True);p.add_argument("--out",required=True)
    a=p.parse_args();cfg=json.loads(Path(a.config).read_text())
    if hashlib.sha256(Path(cfg["data_file"]).read_bytes()).hexdigest()!=cfg["data_sha256"]:
        raise RuntimeError("data SHA mismatch")
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False);jobs=[]
    with np.load(cfg["data_file"]) as data:
        for cell,groups in cfg["groups"].items():
            x=data["train_"+cell+"_X"];ids=data["train_"+cell+"_group"]
            for g in groups:
                ix=np.flatnonzero(ids==g)
                if len(ix)!=3:raise RuntimeError("group strike count mismatch")
                jobs.append((cell,g,x[ix].copy(),cfg))
    started=time.perf_counter();results=[]
    with ProcessPoolExecutor(max_workers=cfg["workers"]) as pool,(out/"axes.jsonl").open("w") as log:
        for row in pool.map(one,jobs):
            results.append(row);log.write(json.dumps(row)+"\n");log.flush()
    summary=dict(groups=len(results),max_change={axis:max(r["changes"][axis] for x in results for r in x["risks"])
                                                for axis in ("step","space","time","domain")},
                 dominant_counts={axis:sum(r["dominant"]==axis for x in results for r in x["risks"])
                                  for axis in ("step","space","time","domain")},
                 elapsed_seconds=time.perf_counter()-started,
                 scope="axis diagnosis of previously failed training-prefix risk labels")
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary),flush=True)

if __name__=="__main__":main()
