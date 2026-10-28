"""Measure warm, single-process online cost of the frozen time-varying put methods."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[key] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
import time

import numpy as np

from timevarying_data_pilot import pde_price, gtfk_price
from timevarying_put_evaluate import predict


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contract(features, cell):
    a1, a2 = np.exp(features[0]), np.exp(features[1])
    sigma1, sigma2 = float(features[2]), float(features[3])
    r0, rbar1, rbar2 = np.exp(features[4]), np.exp(features[5]), np.exp(features[6])
    change = float(features[7])
    if cell == "TE":
        e3, maturity = map(float, features[8:10])
        exercise = [e3]
    else:
        e1, e2, e3, maturity = map(float, features[8:12])
        exercise = [e1, e2, e3]
    case = dict(schedule=[(0.0,change,dict(a=float(a1),sigma=sigma1,r0=float(r0),rbar=float(rbar1))),
                          (change,maturity,dict(a=float(a2),sigma=sigma2,r0=float(r0),rbar=float(rbar2)))],
                exercise=exercise,maturity=maturity)
    return case, exercise


def baseline(cell, x):
    case, dates = contract(x[0], cell)
    strikes = x[:, -1].astype(float)
    a, d = [], []
    begin = time.perf_counter()
    for strike in strikes:
        g1 = gtfk_price(case, dates, float(strike), 3201, 128, 128, 1.0)
        g2 = gtfk_price(case, dates, float(strike), 4801, 128, 128, 1.0)
        chosen = g2
        if abs(g2-g1) > 1e-6:
            g3 = gtfk_price(case, dates, float(strike), 6401, 128, 128, 1.0)
            if abs(g3-g2) > 1e-6:
                raise RuntimeError("GTFK online numerical gate failed")
            chosen = g3
        a.append(chosen)
    a_seconds = time.perf_counter()-begin
    begin = time.perf_counter()
    for strike in strikes:
        d.append(pde_price(case, dates, float(strike), 201, 100, 1.0))
    d_seconds = time.perf_counter()-begin
    return np.asarray(a), np.asarray(d), a_seconds, d_seconds


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    for name in ("data", "selected", "models"):
        if sha256(cfg[name+"_file"]) != cfg[name+"_sha256"]:
            raise RuntimeError(name+" input checksum mismatch")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    selected = json.loads(Path(cfg["selected_file"]).read_text())
    chosen = {(fit["cell"], fit["method"], fit["seed"]): entry["fit"]
              for entry in selected if entry["selection"] == "tuned"
              for fit in [entry["fit"]] if fit["budget"] == 4096}
    expected = {(cell, method, seed) for cell in cfg["cells"]
                for method in ("B", "C", "D") for seed in cfg["seeds"]}
    if set(chosen) != expected:
        raise RuntimeError("selected model set differs from frozen cost plan")
    records = []
    with np.load(cfg["data_file"]) as data, tempfile.TemporaryDirectory(prefix="put-cost-") as temp:
        with tarfile.open(cfg["models_file"], "r:gz") as archive:
            if any(not (member.name == "models" or member.name.startswith("models/"))
                   for member in archive.getmembers()):
                raise RuntimeError("unexpected model archive path")
            archive.extractall(temp, filter="data")
        modeldir = Path(temp)/"models"
        cache = {}
        for cell in cfg["cells"]:
            prefix = cfg["split"]+"_"+cell+"_"
            groups = data[prefix+"group"]
            for group in cfg["groups"]:
                rows = np.flatnonzero(groups == group)
                if len(rows) != 3:
                    raise RuntimeError("group does not have three strikes")
                x = data[prefix+"X"][rows]
                # Warm the selected networks before timing; model loading is a separate deployment cost.
                for method in ("B", "C", "D"):
                    for seed in cfg["seeds"]:
                        predict(chosen[(cell, method, seed)], modeldir, x, cache)
                a, d, a_time, d_time = baseline(cell, x)
                if max(np.max(abs(a-data[prefix+"A"][rows])),
                       np.max(abs(d-data[prefix+"Dbase"][rows]))) > cfg["price_check_tolerance"]:
                    raise RuntimeError("recomputed numerical baseline differs from frozen data")
                for method in ("B", "C", "D"):
                    for seed in cfg["seeds"]:
                        fit = chosen[(cell, method, seed)]
                        begin = time.perf_counter()
                        residual = predict(fit, modeldir, x, cache)
                        nn_time = time.perf_counter()-begin
                        full_time = nn_time + (a_time if method == "C" else d_time if method == "D" else 0)
                        records.append(dict(cell=cell, group=group, method=method, seed=seed,
                                            strikes=3, neural_seconds=nn_time,
                                            baseline_seconds=full_time-nn_time,
                                            full_online_seconds=full_time,
                                            prediction=(residual+(a if method == "C" else d if method == "D" else 0)).tolist()))
                records.append(dict(cell=cell, group=group, method="A", strikes=3,
                                    full_online_seconds=a_time, prediction=a.tolist()))
                records.append(dict(cell=cell, group=group, method="Dbase", strikes=3,
                                    full_online_seconds=d_time, prediction=d.tolist()))
    (out/"records.json").write_text(json.dumps(records, indent=2)+"\n")
    summary = {}
    for cell in cfg["cells"]:
        summary[cell] = {}
        for method in ("A", "B", "C", "Dbase", "D"):
            times = np.asarray([r["full_online_seconds"] for r in records
                                if r["cell"] == cell and r["method"] == method])
            summary[cell][method] = dict(group_count=len(times), batch_size=3,
                                         median_seconds=float(np.median(times)),
                                         mean_seconds=float(np.mean(times)),
                                         q95_seconds=float(np.quantile(times, .95)))
    (out/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
