"""Paired time-varying put direct-network price and derivative supervision."""
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


def read_labels(path, split, cells, counts, axes):
    rows = {}
    for line in Path(path).read_text().splitlines():
        row = json.loads(line)
        cell, group = row["cell"], row["group"]
        if cell not in cells or group >= counts[split]:
            continue
        key = cell, group
        if key in rows or row["strike_index"] != 1 or not row["passed"]:
            raise RuntimeError(f"duplicate or uncertified {split} label {key}")
        if [d["coordinate"] for d in row["derivatives"]] != axes:
            raise RuntimeError(f"{split} coordinate order mismatch {key}")
        rows[key] = row
    if set(rows) != {(cell, group) for cell in cells for group in range(counts[split])}:
        raise RuntimeError(f"{split} labels incomplete")
    return rows


def run(job):
    cell, arm, seed, cfg, X, y, R, V, vy, Z, zy, zR = job
    mean = X.mean(axis=0)
    scale = np.maximum(X.std(axis=0), 1e-10)
    ym = float(y.mean())
    ys = max(float(y.std()), 1e-8)
    dims = cfg["supervised_dimensions"]
    derivatives = None if arm == "price" else {
        "weight": cfg["derivative_weight"],
        "values": R[:, dims]*scale[dims]/ys,
        "dims": dims,
    }
    net = MLP(X.shape[1], cfg["width"], cfg["layers"], seed)
    fit = net.fit((X-mean)/scale, (y-ym)/ys, (V-mean)/scale,
                  (vy-ym)/ys, cfg["learning_rate"], seed,
                  epochs=cfg["epochs"], batch=cfg["batch"],
                  patience=cfg["patience"], derivatives=derivatives)
    pred = net.predict((Z-mean)/scale)*ys+ym
    risk = net.input_gradient((Z-mean)/scale)[:, :len(cfg["coordinates"])]*ys/scale[:len(cfg["coordinates"])]
    row = {"cell": cell, "arm": arm, "seed": seed, "fit": fit,
           "test_price_mae": float(np.mean(abs(pred-zy))),
           "test_risk_mae": np.mean(abs(risk-zR), axis=0).tolist(),
           "test_group_price_error": abs(pred-zy).tolist(),
           "test_group_risk_error": abs(risk-zR).tolist()}
    weights = {f"W{i}": w for i, w in enumerate(net.W)}
    weights.update({f"b{i}": b for i, b in enumerate(net.b)})
    weights.update(mean=mean, scale=scale, ym=ym, ys=ys)
    return row, weights


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    for stem in ("data", "train_risk", "val_risk", "test_risk"):
        path = Path(cfg[stem+"_file"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != cfg[stem+"_sha256"]:
            raise RuntimeError(f"frozen {stem} checksum mismatch")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    (out/"models").mkdir()
    start = time.perf_counter()
    labels = {split: read_labels(cfg[f"{split}_risk_file"], split, cfg["cells"],
                                 cfg["groups"], cfg["coordinates"])
              for split in ("train", "val", "test")}
    jobs = []
    with np.load(cfg["data_file"]) as data:
        for cell in cfg["cells"]:
            arrays = []
            for split, count in cfg["groups"].items():
                stem = f"{split}_{cell}_"
                ids = np.arange(count)*3+1
                if not np.array_equal(data[stem+"group"][ids], np.arange(count)):
                    raise RuntimeError(f"{stem} group identity mismatch")
                X = data[stem+"X"][ids].copy()
                y = data[stem+"y"][ids].copy()
                selected = [labels[split][cell, g] for g in range(count)]
                if any(not np.isclose(X[g, -1], selected[g]["strike"]) for g in range(count)):
                    raise RuntimeError(f"{stem} strike mismatch")
                R = np.asarray([[d["reference"] for d in row["derivatives"]] for row in selected])
                if R.shape != (count, len(cfg["coordinates"])):
                    raise RuntimeError(f"{stem} risk shape mismatch")
                arrays.append((X, y, R))
            (X, y, R), (V, vy, _), (Z, zy, zR) = arrays
            for arm in cfg["arms"]:
                for seed in cfg["seeds"]:
                    jobs.append((cell, arm, seed, cfg, X, y, R, V, vy, Z, zy, zR))
    results = []
    with ProcessPoolExecutor(max_workers=cfg["workers"]) as pool, (out/"fits.jsonl").open("w") as ledger:
        for row, weights in pool.map(run, jobs):
            name = f"{row['cell']}-{row['arm']}-{row['seed']}.npz"
            np.savez_compressed(out/"models"/name, **weights)
            row["model_file"] = name
            results.append(row)
            ledger.write(json.dumps(row)+"\n")
            ledger.flush()
            print(json.dumps({"completed_fits": len(results), "frozen_fits": len(jobs)}), flush=True)
    contrasts = []
    for cell in cfg["cells"]:
        pair = [(next(r for r in results if r["cell"] == cell and r["arm"] == "price" and r["seed"] == seed),
                 next(r for r in results if r["cell"] == cell and r["arm"] == "price_risk" and r["seed"] == seed))
                for seed in cfg["seeds"]]
        contrasts.append({"cell": cell, "seed_pairs": len(pair),
                          "price_only_mae": float(np.mean([a["test_price_mae"] for a, b in pair])),
                          "price_risk_mae": float(np.mean([b["test_price_mae"] for a, b in pair])),
                          "price_only_risk_mae": np.mean([a["test_risk_mae"] for a, b in pair], axis=0).tolist(),
                          "price_risk_risk_mae": np.mean([b["test_risk_mae"] for a, b in pair], axis=0).tolist()})
    (out/"contrasts.json").write_text(json.dumps(contrasts, indent=2)+"\n")
    summary = {"scope": "exploratory time-varying direct-network E4",
               "completed_fits": len(results), "frozen_fits": len(jobs),
               "groups_per_cell": cfg["groups"], "coordinates": cfg["coordinates"],
               "elapsed_seconds": time.perf_counter()-start}
    (out/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
