"""Exploratory E2: fixed-capacity residual fit on validation-matched TE PDE."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[key] = "1"

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
import time

import numpy as np

from timevarying_put_online_cost import contract
from timevarying_data_pilot import pde_price
from timevarying_put_evaluate import predict
from learning import MLP


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def group_baseline(job):
    split, group, x, n, rate = job
    case, dates = contract(x[0], "TE")
    started = time.perf_counter()
    prices = [pde_price(case, dates, float(k), n, rate, 1.0) for k in x[:, -1]]
    return split, group, prices, time.perf_counter()-started


def train(job):
    seed, x, y, base, vx, vy, vbase, model_dir = job
    target, vtarget = y-base, vy-vbase
    mean = x.mean(axis=0)
    scale = np.maximum(x.std(axis=0), 1e-10)
    ym, ys = target.mean(), max(target.std(), 1e-8)
    net = MLP(x.shape[1], 64, 3, seed)
    fit = net.fit((x-mean)/scale, (target-ym)/ys,
                  (vx-mean)/scale, (vtarget-ym)/ys, .001, seed)
    val_pred = net.predict((vx-mean)/scale)*ys+ym+vbase
    params = {f"W{i}": w for i, w in enumerate(net.W)}
    params.update({f"b{i}": b for i, b in enumerate(net.b)})
    params.update(mean=mean, scale=scale, ym=ym, ys=ys)
    model_file = f"TE-Dmatch-1024-{seed}-3-64-0.001.npz"
    np.savez_compressed(Path(model_dir)/model_file, **params)
    return dict(seed=seed, validation_mae=float(np.mean(abs(val_pred-vy))),
                fit=fit, model_file=model_file, layers=3, width=64)


def summarize(pred, truth):
    e = abs(pred-truth)
    return dict(mae=float(e.mean()), q95=float(np.quantile(e, .95)),
                max=float(e.max()), group_mae=e.reshape(-1, 3).mean(axis=1).tolist())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    for stem in ("data", "selected", "models", "scan_summary"):
        if checksum(cfg[stem+"_file"]) != cfg[stem+"_sha256"]:
            raise RuntimeError(stem+" SHA mismatch")
    scan = json.loads(Path(cfg["scan_summary_file"]).read_text())
    selected_grid = scan["cells"]["TE"]["error_matched_pde"]
    n, rate = int(selected_grid["n"]), int(selected_grid["rate"])
    if [n, rate] != cfg["matched_grid"]:
        raise RuntimeError("frozen matched grid differs from validation selection")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    (out/"models").mkdir()
    jobs, arrays = [], {}
    with np.load(cfg["data_file"]) as data:
        for split, count in cfg["groups"].items():
            prefix = split+"_TE_"
            x, y, a, d, group = (data[prefix+k] for k in ("X", "y", "A", "Dbase", "group"))
            rows = np.arange(3*count)
            if not np.array_equal(group[rows], np.repeat(np.arange(count), 3)):
                raise RuntimeError("frozen group order mismatch")
            arrays[split] = dict(x=x[rows].copy(), y=y[rows].copy(),
                                 a=a[rows].copy(), d=d[rows].copy(),
                                 matched=np.empty(3*count))
            for g in range(count):
                jobs.append((split, g, x[3*g:3*g+3].copy(), n, rate))
    started = time.perf_counter()
    timing = {split: [] for split in cfg["groups"]}
    with ProcessPoolExecutor(max_workers=cfg["baseline_workers"]) as pool, \
            (out/"baseline-groups.jsonl").open("w") as ledger:
        for split, g, prices, seconds in pool.map(group_baseline, jobs):
            arrays[split]["matched"][3*g:3*g+3] = prices
            timing[split].append(seconds)
            ledger.write(json.dumps(dict(split=split, group=g, prices=prices, seconds=seconds))+"\n")
            ledger.flush()
    old = json.loads(Path(cfg["selected_file"]).read_text())
    prior = {entry["fit"]["seed"]: entry["fit"] for entry in old
             if entry["selection"] == "fixed_capacity"
             and entry["fit"]["cell"] == "TE"
             and entry["fit"]["method"] == "D"
             and entry["fit"]["budget"] == 1024}
    if set(prior) != set(cfg["seeds"]):
        raise RuntimeError("old fixed-capacity D matches are incomplete")
    t, v, q = (arrays[k] for k in ("train", "val", "test"))
    train_jobs = [(seed, t["x"], t["y"], t["matched"],
                   v["x"], v["y"], v["matched"], str(out/"models")) for seed in cfg["seeds"]]
    with ProcessPoolExecutor(max_workers=cfg["fit_workers"]) as pool:
        fits = list(pool.map(train, train_jobs))
    (out/"fits.json").write_text(json.dumps(fits, indent=2)+"\n")
    rows = []
    for name, base in (("A", q["a"]), ("Dbase", q["d"]), ("Dmatch_base", q["matched"])):
        rows.append(dict(method=name, seed=None, test=summarize(base, q["y"])))
    cache = {}
    for fit in fits:
        pred = predict(fit, out/"models", q["x"], cache)+q["matched"]
        rows.append(dict(method="Dmatch", seed=fit["seed"], test=summarize(pred, q["y"])))
    with tempfile.TemporaryDirectory(prefix="e2-old-models-") as tmp:
        with tarfile.open(cfg["models_file"], "r:gz") as archive:
            if any(not (member.name == "models" or member.name.startswith("models/"))
                   for member in archive.getmembers()):
                raise RuntimeError("unexpected model archive path")
            archive.extractall(tmp, filter="data")
        olddir = Path(tmp)/"models"
        for seed in cfg["seeds"]:
            pred = predict(prior[seed], olddir, q["x"], cache)+q["d"]
            rows.append(dict(method="D_original", seed=seed, test=summarize(pred, q["y"])))
    (out/"test-scores.json").write_text(json.dumps(rows, indent=2)+"\n")
    with tarfile.open(out/"models.tar.gz", "w:gz") as archive:
        archive.add(out/"models", arcname="models")
    summary = dict(scope="exploratory E2 after original time-varying test was viewed",
                   cell="TE", train_groups=cfg["groups"]["train"],
                   val_groups=cfg["groups"]["val"], test_groups=cfg["groups"]["test"],
                   matched_grid=[n, rate], model=dict(layers=3, width=64, lr=.001),
                   seeds=cfg["seeds"], elapsed_seconds=time.perf_counter()-started,
                   baseline_group_seconds_median={k: float(np.median(v)) for k,v in timing.items()},
                   test_mae_by_method={m:float(np.mean([r["test"]["mae"] for r in rows if r["method"]==m]))
                                       for m in ("A", "Dbase", "Dmatch_base", "Dmatch", "D_original")})
    (out/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
