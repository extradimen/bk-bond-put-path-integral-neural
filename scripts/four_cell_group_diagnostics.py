"""Frozen exploratory group diagnostics from four already evaluated put cells."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def checked(path, digest):
    path = Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise RuntimeError("frozen input checksum mismatch: " + str(path))
    return path


def selected_tags(entries, cell, seeds):
    tags = {}
    for entry in entries:
        fit = entry["fit"]
        if entry["selection"] == "tuned" and fit["budget"] == 4096 and fit["cell"] == cell:
            key = (fit["method"], fit["seed"])
            if key in tags:
                raise RuntimeError("duplicate selected model")
            tags[key] = fit["tag"]
    if set(tags) != {(method, seed) for method in ("B", "C", "D") for seed in seeds}:
        raise RuntimeError("incomplete selected model set")
    return tags


def describe(values):
    a = np.asarray(values, dtype=float)
    return dict(count=len(a), mean=float(np.mean(a)), median=float(np.median(a)),
                q95=float(np.quantile(a, .95)), q99=float(np.quantile(a, .99)),
                maximum=float(np.max(a)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    all_rows = []
    premium = {}
    with (out/"groups.jsonl").open("w") as ledger:
        for source in cfg["sources"]:
            data_path = checked(source["data_file"], source["data_sha256"])
            pred_path = checked(source["predictions_file"], source["predictions_sha256"])
            selected_path = checked(source["selected_file"], source["selected_sha256"])
            entries = json.loads(selected_path.read_text())
            with np.load(data_path) as data, np.load(pred_path) as predictions:
                for split in cfg["splits"]:
                    for cell in source["cells"]:
                        prefix = split+"_"+cell+"_"
                        n = cfg["groups"][split]
                        truth = data[prefix+"y"]
                        group = data[prefix+"group"]
                        if len(truth) != 3*n or not np.array_equal(group, np.repeat(np.arange(n), 3)):
                            raise RuntimeError("frozen group identity mismatch: " + prefix)
                        methods = {m: np.abs(data[prefix+m]-truth).reshape(n, 3).mean(axis=1)
                                   for m in ("A", "Dbase")}
                        tags = selected_tags(entries, cell, cfg["seeds"])
                        for method in ("B", "C", "D"):
                            errors = []
                            for seed in cfg["seeds"]:
                                key = split+"_tuned_"+tags[(method, seed)]
                                if key not in predictions or predictions[key].shape != truth.shape:
                                    raise RuntimeError("missing or malformed frozen prediction: " + key)
                                errors.append(np.abs(predictions[key]-truth).reshape(n, 3).mean(axis=1))
                            methods[method] = np.mean(errors, axis=0)
                        for i in range(n):
                            prices = truth[3*i:3*i+3]
                            row = dict(cell=cell, split=split, group=i, strikes=3,
                                       price_mean=float(np.mean(prices)),
                                       price_min=float(np.min(prices)),
                                       near_zero_strikes=int(np.sum(prices < cfg["near_zero_price"])),
                                       error={m:float(methods[m][i]) for m in ("A", "B", "C", "Dbase", "D")})
                            all_rows.append(row)
                            ledger.write(json.dumps(row)+"\n")
                            ledger.flush()
                        print(json.dumps(dict(cell=cell, split=split, completed_groups=len(all_rows),
                                              total_groups=cfg["total_groups"])), flush=True)
                    left, right = source["cells"]
                    lx, rx = data[split+"_"+left+"_X"], data[split+"_"+right+"_X"]
                    common = 4 if left == "FE" else 8
                    tail = 3 if left == "FE" else 3
                    if not np.allclose(lx[:, :common], rx[:, :common]) or not np.allclose(lx[:, -tail:], rx[:, -tail:]):
                        raise RuntimeError("paired European/Bermudan input mismatch")
                    diff = data[split+"_"+right+"_y"]-data[split+"_"+left+"_y"]
                    premium[source["name"]+"_"+split] = dict(
                        price_premium=describe(diff),
                        negative_beyond_tolerance=int(np.sum(diff < -cfg["premium_tolerance"])),
                        near_zero_fraction=float(np.mean(np.abs(diff) <= cfg["premium_near_zero"])))
    summary = dict(scope="exploratory frozen evaluation diagnostics; price premium is not an exercise boundary",
                   groups=len(all_rows), premium=premium, strata={})
    for cell in ("FE", "FB", "TE", "TB"):
        summary["strata"][cell] = {}
        for split in cfg["splits"]:
            rows = [r for r in all_rows if r["cell"] == cell and r["split"] == split]
            near = [r for r in rows if r["near_zero_strikes"] > 0]
            summary["strata"][cell][split] = dict(
                groups=len(rows), near_zero_groups=len(near),
                method_group_mae={m:describe([r["error"][m] for r in rows]) for m in ("A", "B", "C", "Dbase", "D")},
                near_zero_group_mae={m:describe([r["error"][m] for r in near]) if near else None
                                     for m in ("A", "B", "C", "Dbase", "D")})
    (out/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps(dict(groups=summary["groups"], strata=12)), flush=True)


if __name__ == "__main__":
    main()
