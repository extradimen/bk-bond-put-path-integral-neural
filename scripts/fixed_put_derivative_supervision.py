"""Paired direct-network price-only versus price-and-risk supervision."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[key] = "1"

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from learning import MLP


def run(job):
    cell, arm, seed, cfg, X, y, R, V, vy, Z, zy, zR = job
    mean = X.mean(axis=0)
    scale = np.maximum(X.std(axis=0), 1e-10)
    ym = y.mean()
    ys = max(float(y.std()), 1e-8)
    dims = cfg["supervised_dimensions"]
    derivative_target = R[:, dims] * scale[dims] / ys
    derivatives = None if arm == "price" else dict(
        weight=cfg["derivative_weight"], values=derivative_target, dims=dims)
    net = MLP(X.shape[1], cfg["width"], cfg["layers"], seed)
    fit = net.fit((X-mean)/scale, (y-ym)/ys, (V-mean)/scale,
                  (vy-ym)/ys, cfg["learning_rate"], seed,
                  epochs=cfg["epochs"], batch=cfg["batch"], patience=cfg["patience"],
                  derivatives=derivatives)
    pred = net.predict((Z-mean)/scale)*ys+ym
    risk = net.input_gradient((Z-mean)/scale)[:, :4]*ys/scale[:4]
    row = dict(cell=cell, arm=arm, seed=seed, fit=fit,
               test_price_mae=float(np.mean(abs(pred-zy))),
               test_risk_mae=np.mean(abs(risk-zR), axis=0).tolist(),
               test_group_price_mae=abs(pred-zy).reshape(-1,3).mean(axis=1).tolist(),
               test_group_risk_mae=abs(risk-zR).reshape(-1,3,4).mean(axis=1).tolist())
    weights = {f"W{i}": w for i,w in enumerate(net.W)}
    weights.update({f"b{i}": b for i,b in enumerate(net.b)})
    weights.update(mean=mean, scale=scale, ym=ym, ys=ys)
    return row, weights


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    for path_key, digest_key in (("data_file", "data_sha256"),
                                 ("risk_file", "risk_sha256")):
        path = Path(cfg[path_key])
        if hashlib.sha256(path.read_bytes()).hexdigest() != cfg[digest_key]:
            raise RuntimeError(f"input SHA-256 mismatch: {path}")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    (out/"models").mkdir()
    start = time.perf_counter()
    jobs = []
    with np.load(cfg["data_file"]) as data, np.load(cfg["risk_file"]) as labels:
        for cell in cfg["cells"]:
            arrays = []
            for split, count in cfg["groups"].items():
                prefix = f"{split}_{cell}_"
                X = data[prefix+"X"][:3*count].copy()
                y = data[prefix+"y"][:3*count].copy()
                R = labels[prefix+"risk"].copy()
                ids = data[prefix+"group"][:3*count]
                if len(R) != len(y) or not np.array_equal(ids, np.repeat(np.arange(count), 3)):
                    raise RuntimeError(f"data and labels misaligned: {prefix}")
                if not np.array_equal(ids, labels[prefix+"group"]):
                    raise RuntimeError(f"risk labels group mismatch: {prefix}")
                if R.shape != (len(y),4):
                    raise RuntimeError(f"risk labels shape mismatch: {prefix}")
                arrays.append((X,y,R))
            (X,y,R),(V,vy,_),(Z,zy,zR) = arrays
            for arm in cfg["arms"]:
                for seed in cfg["seeds"]:
                    jobs.append((cell,arm,seed,cfg,X,y,R,V,vy,Z,zy,zR))
    results = []
    with ProcessPoolExecutor(max_workers=cfg["workers"]) as pool, \
         (out/"fits.jsonl").open("w") as ledger:
        for row, weights in pool.map(run,jobs):
            name = f"{row['cell']}-{row['arm']}-{row['seed']}.npz"
            np.savez_compressed(out/"models"/name, **weights)
            row["model_file"] = name
            results.append(row)
            ledger.write(json.dumps(row)+"\n")
            ledger.flush()
            print(json.dumps(dict(cell=row["cell"],arm=row["arm"],seed=row["seed"],
                                  test_price_mae=row["test_price_mae"],
                                  elapsed_seconds=time.perf_counter()-start)), flush=True)
    contrasts = []
    for cell in cfg["cells"]:
        paired = [(next(r for r in results if r["cell"]==cell and r["arm"]=="price" and r["seed"]==seed),
                   next(r for r in results if r["cell"]==cell and r["arm"]=="price_risk" and r["seed"]==seed))
                  for seed in cfg["seeds"]]
        contrasts.append(dict(cell=cell, method="B direct MLP",
                              price_only_mae=float(np.mean([a["test_price_mae"] for a,b in paired])),
                              price_risk_mae=float(np.mean([b["test_price_mae"] for a,b in paired])),
                              price_only_risk_mae=np.mean([a["test_risk_mae"] for a,b in paired],axis=0).tolist(),
                              price_risk_risk_mae=np.mean([b["test_risk_mae"] for a,b in paired],axis=0).tolist(),
                              seed_pair_count=len(paired)))
    (out/"contrasts.json").write_text(json.dumps(contrasts,indent=2)+"\n")
    summary = dict(scope="exploratory direct-network E4 price versus derivative supervision",
                   fits=len(results), cells=cfg["cells"], arms=cfg["arms"],
                   supervised_dimensions=cfg["supervised_dimensions"],
                   elapsed_seconds=time.perf_counter()-start)
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary),flush=True)


if __name__ == "__main__":
    main()
