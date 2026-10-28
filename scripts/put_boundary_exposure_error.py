"""Exploratory exercise-boundary exposure versus frozen t=0 price errors."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def checked(spec):
    path = Path(spec["file"])
    if hashlib.sha256(path.read_bytes()).hexdigest() != spec["sha256"]:
        raise RuntimeError(f"input hash mismatch: {path}")
    return path


def normal_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def moments(features, cell, date):
    if cell == "FB":
        a, sigma, x0, b = math.exp(features[0]), features[1], features[2], features[3]
        intervals = [(0.0, date, a, sigma, b)]
    else:
        a1, a2 = math.exp(features[0]), math.exp(features[1])
        sigma1, sigma2 = features[2], features[3]
        x0, b1, b2, change = features[4], features[5], features[6], features[7]
        intervals = [(0.0, min(date, change), a1, sigma1, b1)]
        if date > change:
            intervals.append((change, date, a2, sigma2, b2))
    mean, variance = float(x0), 0.0
    for left, right, a, sigma, b in intervals:
        dt = float(right - left)
        decay = math.exp(-a * dt)
        mean = float(b) + (mean - float(b)) * decay
        variance = variance * decay**2 + float(sigma)**2 * (-math.expm1(-2*a*dt))/(2*a)
    if variance <= 0:
        raise RuntimeError("nonpositive exercise-state variance")
    return mean, math.sqrt(variance)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    paths = {key: checked(value) for key, value in cfg["sources"].items()}
    classifications = [json.loads(line) for line in paths["classification"].read_text().splitlines()]
    expected = {(cell, group) for cell in cfg["cells"] for group in cfg["groups"]}
    if {(row["cell"], row["group"]) for row in classifications} != expected or len(classifications) != len(expected):
        raise RuntimeError("boundary group set mismatch")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    completed = 0
    with np.load(paths["fixed_data"]) as fixed, np.load(paths["time_data"]) as time, \
         np.load(paths["fixed_predictions"]) as fixed_pred, np.load(paths["time_predictions"]) as time_pred, \
         (out/"groups.jsonl").open("w") as ledger:
        data_by_cell = {"FB": fixed, "TB": time}
        pred_by_cell = {"FB": fixed_pred, "TB": time_pred}
        selected_by_cell = {
            "FB": json.loads(paths["fixed_selected"].read_text()),
            "TB": json.loads(paths["time_selected"].read_text()),
        }
        for boundary in classifications:
            cell, group = boundary["cell"], boundary["group"]
            data, preds = data_by_cell[cell], pred_by_cell[cell]
            idx = 3*group + cfg["strike_index"]
            if data[f"test_{cell}_group"][idx] != group:
                raise RuntimeError("dataset group mismatch")
            features = data[f"test_{cell}_X"][idx]
            reference = float(data[f"test_{cell}_y"][idx])
            status = [decision["status"] for decision in boundary["decisions"]]
            qualified = all(value == "single_root_consistent" for value in status)
            exposures = []
            if qualified:
                for decision in boundary["decisions"]:
                    roots = decision["pde_roots"]
                    if len(roots) != 1 or roots[0] <= 0:
                        raise RuntimeError("qualified decision missing a single positive root")
                    mean, sd = moments(features, cell, decision["date"])
                    log_root = math.log(roots[0])
                    band = cfg["log_rate_half_width"]
                    exposure = normal_cdf((log_root+band-mean)/sd) - normal_cdf((log_root-band-mean)/sd)
                    exposures.append(exposure)
            errors = {}
            for method in cfg["methods"]:
                if method in ("A", "Dbase"):
                    estimates = [float(data[f"test_{cell}_{method}"][idx])]
                else:
                    fits = [entry["fit"] for entry in selected_by_cell[cell]
                            if entry["selection"] == "tuned" and entry["fit"]["cell"] == cell
                            and entry["fit"]["method"] == method and entry["fit"]["budget"] == cfg["budget"]]
                    if sorted(fit["seed"] for fit in fits) != sorted(cfg["seeds"]):
                        raise RuntimeError("selected seed mismatch")
                    estimates = [float(preds["test_tuned_"+fit["tag"]][idx]) for fit in fits]
                errors[method] = float(np.mean(np.abs(np.asarray(estimates)-reference)))
            row = dict(cell=cell, group=group, qualified=qualified, decision_status=status,
                       near_boundary_probability=max(exposures) if qualified else None,
                       price_absolute_error=errors)
            ledger.write(json.dumps(row)+"\n")
            ledger.flush()
            completed += 1
            print(json.dumps(dict(completed=completed, frozen=len(expected))), flush=True)
    if completed != cfg["frozen_groups"]:
        raise RuntimeError("group count mismatch")
    rows = [json.loads(line) for line in (out/"groups.jsonl").read_text().splitlines()]
    summary = dict(completed=completed, frozen=cfg["frozen_groups"],
                   qualified=sum(row["qualified"] for row in rows),
                   unqualified=sum(not row["qualified"] for row in rows),
                   log_rate_half_width=cfg["log_rate_half_width"],
                   scope="exploratory t=0 middle-strike price errors against OU probability near future exercise roots")
    for cell in cfg["cells"]:
        subset = [row for row in rows if row["cell"] == cell and row["qualified"]]
        summary[cell] = {}
        for label, selected in (("near", [row for row in subset if row["near_boundary_probability"] >= cfg["near_probability_threshold"]]),
                                ("far", [row for row in subset if row["near_boundary_probability"] < cfg["near_probability_threshold"]])):
            summary[cell][label] = dict(groups=len(selected),
                                        mean_price_absolute_error={method: float(np.mean([row["price_absolute_error"][method] for row in selected])) if selected else None
                                                                   for method in cfg["methods"]})
    (out/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")


if __name__ == "__main__":
    main()
