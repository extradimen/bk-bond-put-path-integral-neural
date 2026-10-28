"""Evaluate new conditional models against independent exercise-date roots."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[key] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from conditional_boundary import conditional_curves
from conditional_boundary_features import encode
from put_exercise_boundary_pilot import fixed_contract, roots
from timevarying_data_pilot import schedule_grid
from timevarying_put_risk_pilot import contract as time_contract


def predict(path, x):
    with np.load(path) as data:
        h = (x-data["mean"])/data["scale"]
        i = 0
        while f"W{i}" in data.files:
            h = h @ data[f"W{i}"] + data[f"b{i}"]
            if f"W{i+1}" in data.files:
                h = np.tanh(h)
            i += 1
        return h[:, 0]*float(data["ys"]) + float(data["ym"])


def evaluate_contract(features, case, models, cfg):
    strike = float(features[-1])
    ref = cfg["reference"]
    independent = cfg["independent"]
    coarse = cfg["coarse"]
    gtfk = cfg["gtfk"]
    grids = {
        "ref": schedule_grid(case, ref[0], ref[2]),
        "independent": schedule_grid(case, independent[0], independent[2]),
        "coarse": schedule_grid(case, coarse[0], coarse[2]),
        "gtfk": schedule_grid(case, gtfk[0], gtfk[3]),
    }
    curves = {
        "ref": conditional_curves(case, strike, grids["ref"], "pde", rate=ref[1]),
        "independent": conditional_curves(case, strike, grids["independent"], "split",
                                          rate=independent[1], order=independent[3]),
        "coarse": conditional_curves(case, strike, grids["coarse"], "pde", rate=coarse[1]),
        "gtfk": conditional_curves(case, strike, grids["gtfk"], "gtfk",
                                   nq=gtfk[1], ny=gtfk[2]),
    }
    lo = grids["ref"][0] + cfg["domain_margin"]*np.ptp(grids["ref"])
    hi = grids["ref"][-1] - cfg["domain_margin"]*np.ptp(grids["ref"])
    states = np.linspace(lo, hi, cfg["evaluation_states"])
    records = []
    for j in range(len(case["exercise"])-1):
        reference = np.interp(states, grids["ref"], curves["ref"][j]["continuation"])
        independent_value = np.interp(states, grids["independent"],
                                      curves["independent"][j]["continuation"])
        exercise = np.interp(states, grids["ref"], curves["ref"][j]["exercise"])
        bases = {
            "B": np.zeros_like(states),
            "C": np.interp(states, grids["gtfk"], curves["gtfk"][j]["continuation"]),
            "D": np.interp(states, grids["coarse"], curves["coarse"][j]["continuation"]),
        }
        ref_roots = roots(grids["ref"], curves["ref"][j]["gap"])
        independent_roots = roots(grids["independent"], curves["independent"][j]["gap"])
        reference_valid = (len(ref_roots) == len(independent_roots) and
            len(ref_roots) <= 1 and
            (not ref_roots or (lo < ref_roots[0] < hi and
             abs(np.exp(ref_roots[0])-np.exp(independent_roots[0])) <= cfg["reference_root_tolerance"])) and
            np.max(abs(reference-independent_value)) <= cfg["reference_value_tolerance"])
        x = encode(features, case["exercise"], j, states)
        methods = {}
        for method in cfg["methods"]:
            prediction = bases[method] + predict(models[method], x)
            pred_roots = roots(states, exercise-prediction)
            topology_match = len(pred_roots) == len(ref_roots)
            root_error = (abs(np.exp(pred_roots[0])-np.exp(ref_roots[0]))
                          if len(pred_roots) == len(ref_roots) == 1 else None)
            mae = float(np.mean(abs(prediction-reference)))
            methods[method] = dict(mae=mae, predicted_root_count=len(pred_roots),
                predicted_root_short_rates=[float(np.exp(z)) for z in pred_roots],
                topology_match=topology_match, root_error_short_rate=root_error,
                passed=bool(reference_valid and topology_match and
                    mae <= cfg["continuation_mae_tolerance"] and
                    (root_error is None or root_error <= cfg["model_root_tolerance"])))
        records.append(dict(date_index=j, date=float(case["exercise"][j]),
            reference_root_count=len(ref_roots),
            reference_root_short_rates=[float(np.exp(z)) for z in ref_roots],
            independent_root_count=len(independent_roots),
            independent_value_max_abs=float(np.max(abs(reference-independent_value))),
            reference_valid=bool(reference_valid), methods=methods))
    return records


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    cfg = json.loads(Path(a.config).read_text())
    for item in [*cfg["sources"].values(), cfg["selected"],
                 *(item for cell in cfg["models"].values() for item in cell.values())]:
        if hashlib.sha256(Path(item["file"]).read_bytes()).hexdigest() != item["sha256"]:
            raise RuntimeError("frozen test source or model checksum mismatch")
    selection = json.loads(Path(cfg["selected"]["file"]).read_text())
    for record in selection:
        expected = cfg["models"][record["cell"]][record["method"]]["file"]
        if Path(expected).name != Path(record["model_file"]).name:
            raise RuntimeError("model file differs from frozen validation selection")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    total = sum(len(groups) for groups in cfg["groups_by_cell"].values())
    with (out / "boundaries.jsonl").open("w") as ledger:
        for cell, groups in cfg["groups_by_cell"].items():
            models = {method: cfg["models"][cell][method]["file"] for method in cfg["methods"]}
            with np.load(cfg["sources"][cell]["file"]) as data:
                group_ids = data[f"test_{cell}_group"]
                for group in groups:
                    started = time.perf_counter()
                    indices = np.flatnonzero(group_ids == group)
                    if len(indices) != 3:
                        raise RuntimeError("frozen test group must have three strike contracts")
                    strikes = []
                    for strike_index, index in enumerate(indices):
                        features = data[f"test_{cell}_X"][index].copy()
                        case = (fixed_contract(features) if cell == "FB" else
                                time_contract(features, cell)[0])
                        strikes.append(dict(strike_index=strike_index,
                            strike=float(features[-1]),
                            records=evaluate_contract(features, case, models, cfg)))
                    row = dict(cell=cell, group=group, strikes=strikes,
                               seconds=time.perf_counter()-started)
                    rows.append(row)
                    ledger.write(json.dumps(row) + "\n")
                    ledger.flush()
                    print(json.dumps(dict(completed_groups=len(rows), total_groups=total)), flush=True)
    method_summary = {}
    records = [record for row in rows for strike in row["strikes"]
               for record in strike["records"]]
    for method in cfg["methods"]:
        method_summary[method] = dict(passed_dates=sum(r["methods"][method]["passed"] for r in records),
            total_dates=len(records),
            mean_mae=float(np.mean([r["methods"][method]["mae"] for r in records])),
            max_root_error_short_rate=max((r["methods"][method]["root_error_short_rate"] or 0.)
                for r in records))
    summary = dict(completed_groups=len(rows), total_groups=total,
        reference_valid_dates=sum(r["reference_valid"] for r in records),
        total_dates=len(records), methods=method_summary,
        scope="held-out exercise-date conditional B/C/D boundary comparison; exploratory small-sample fits")
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
