"""Measure warm, single-process online cost of the frozen fixed-put methods."""
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

from bermudan_gtfk_split_pilot import price as gtfk_bermudan
from bermudan_pilot import value as pde_value
from fixed_put_evaluate import predict
from numerics import gt_price


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contract(features, cell):
    a, sigma, r0, rbar = np.exp(features[0]), features[1], np.exp(features[2]), np.exp(features[3])
    if cell == "FE":
        e3, maturity = features[4:6]
        dates = [float(e3)]
    else:
        e1, e2, e3, maturity = features[4:8]
        dates = [float(e1), float(e2), float(e3)]
    return dict(a=float(a), sigma=float(sigma), r0=float(r0), rbar=float(rbar)), dates, float(maturity)


def baseline(cell, x):
    model, dates, maturity = contract(x[0], cell)
    strikes = x[:, -1].astype(float)
    begin = time.perf_counter()
    if cell == "FE":
        direct = dict(model, expiry=dates[-1], tenor=maturity-dates[-1])
        gt_price(direct, strikes, nq=96, ny=48, both=True)
        a = np.asarray(gt_price(direct, strikes, nq=192, ny=96, both=True)["puts"])
    else:
        a = []
        for strike in strikes:
            g1 = gtfk_bermudan(model, dates, maturity, float(strike), 1201, 192, 96, .75)
            g2 = gtfk_bermudan(model, dates, maturity, float(strike), 1601, 192, 96, .75)
            g3 = gtfk_bermudan(model, dates, maturity, float(strike), 1601, 192, 96, 1.0)
            if max(abs(g2-g1), abs(g3-g1)) > 1e-6:
                g4 = gtfk_bermudan(model, dates, maturity, float(strike), 2401, 192, 96, .75)
                chosen = g4
                if max(abs(g4-g2), abs(g4-g3)) > 1e-6:
                    g5 = gtfk_bermudan(model, dates, maturity, float(strike), 3201, 192, 96, .75)
                    g6 = gtfk_bermudan(model, dates, maturity, float(strike), 4801, 192, 96, .75)
                    g7 = gtfk_bermudan(model, dates, maturity, float(strike), 4801, 192, 96, 1.0)
                    if max(abs(g6-g5), abs(g7-g6)) > 1e-6:
                        raise RuntimeError("GTFK online numerical gate failed")
                    chosen = g6
            else:
                chosen = g2
            a.append(chosen)
        a = np.asarray(a)
    a_seconds = time.perf_counter()-begin
    begin = time.perf_counter()
    d = np.asarray([pde_value(model, dates, maturity, float(k), 201, 100, "put")
                    for k in strikes])
    d_seconds = time.perf_counter()-begin
    return a, d, a_seconds, d_seconds


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
