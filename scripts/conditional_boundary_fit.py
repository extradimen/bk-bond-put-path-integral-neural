"""Fit new state-conditioned B/C/D continuation models from frozen data."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[key] = "1"

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import time

import numpy as np

from learning import MLP


def fit_one(data, cell, method, width, layers, seed, lr, cfg):
    prefix = lambda split: f"{split}_{cell}_"
    x = data[prefix("train") + "X"]
    y = data[prefix("train") + "y"]
    v = data[prefix("val") + "X"]
    vy = data[prefix("val") + "y"]
    name = {"B": None, "C": "A", "D": "Dbase"}[method]
    base = np.zeros_like(y) if name is None else data[prefix("train") + name]
    vbase = np.zeros_like(vy) if name is None else data[prefix("val") + name]
    mean = x.mean(axis=0)
    scale = np.maximum(x.std(axis=0), 1e-10)
    target = y - base
    validation_target = vy - vbase
    target_mean = float(target.mean())
    target_scale = max(float(target.std()), 1e-8)
    model = MLP(x.shape[1], width, layers, seed)
    timing = model.fit((x-mean)/scale, (target-target_mean)/target_scale,
                       (v-mean)/scale, (validation_target-target_mean)/target_scale,
                       lr, seed, epochs=cfg["epochs"], batch=cfg["batch"],
                       patience=cfg["patience"])
    pred = model.predict((v-mean)/scale)*target_scale + target_mean + vbase
    mae = float(np.mean(abs(pred-vy)))
    params = {f"W{i}": weight for i, weight in enumerate(model.W)}
    params.update({f"b{i}": bias for i, bias in enumerate(model.b)})
    params.update(mean=mean, scale=scale, ym=target_mean, ys=target_scale)
    return params, dict(cell=cell, method=method, width=width, layers=layers,
                        seed=seed, lr=lr, validation_mae=mae,
                        train_rows=len(x), validation_rows=len(v), fit=timing)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    cfg = json.loads(Path(a.config).read_text())
    source = Path(cfg["data_file"])
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if actual != cfg["data_sha256"]:
        raise RuntimeError("frozen conditional train/validation data SHA-256 mismatch")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    models = out / "models"
    models.mkdir()
    rows = []
    started = time.perf_counter()
    jobs = list(itertools.product(cfg["cells"], cfg["methods"],
                                  cfg["widths"], cfg["layers"],
                                  cfg["seeds"], cfg["learning_rates"]))
    with np.load(source) as data, (out / "fits.jsonl").open("w") as ledger:
        if any(key.startswith("test_") for key in data.files):
            raise RuntimeError("test data must not be present in fit archive")
        for cell in cfg["cells"]:
            train_groups = set(data[f"train_{cell}_group"].tolist())
            val_groups = set(data[f"val_{cell}_group"].tolist())
            if len(train_groups) != cfg["expected_groups"][cell]["train"] or len(val_groups) != cfg["expected_groups"][cell]["val"]:
                raise RuntimeError("fit group counts differ from frozen protocol")
        for cell, method, width, layers, seed, lr in jobs:
            params, row = fit_one(data, cell, method, width, layers, seed, lr, cfg)
            tag = f"{cell}-{method}-{width}-{layers}-{seed}-{lr}"
            np.savez_compressed(models / f"{tag}.npz", **params)
            row["model_file"] = f"models/{tag}.npz"
            rows.append(row)
            ledger.write(json.dumps(row) + "\n")
            ledger.flush()
            print(json.dumps(dict(completed_fits=len(rows), total_fits=len(jobs))), flush=True)
    selected = []
    for cell, method in itertools.product(cfg["cells"], cfg["methods"]):
        candidate = min((r for r in rows if r["cell"] == cell and r["method"] == method),
                        key=lambda r: (r["validation_mae"], r["model_file"]))
        selected.append(candidate)
    (out / "selected.json").write_text(json.dumps(selected, indent=2) + "\n")
    (out / "summary.json").write_text(json.dumps(dict(completed_fits=len(rows),
        total_fits=len(jobs), selected=len(selected), elapsed_seconds=time.perf_counter()-started,
        data_sha256=actual, scope="state-conditioned B/C/D continuation fits; train/validation only"),
        indent=2) + "\n")


if __name__ == "__main__":
    main()
