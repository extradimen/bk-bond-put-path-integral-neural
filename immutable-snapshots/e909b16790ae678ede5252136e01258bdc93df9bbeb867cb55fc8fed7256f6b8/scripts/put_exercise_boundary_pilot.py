"""Actual exercise/continuation crossings for frozen Bermudan put cases."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[key] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from timevarying_data_pilot import schedule_grid
from timevarying_pde import propagate as pde_propagate, split_propagate
from timevarying_put_risk_pilot import contract as time_contract


def fixed_contract(features):
    model = dict(a=float(np.exp(features[0])), sigma=float(features[1]),
                 r0=float(np.exp(features[2])), rbar=float(np.exp(features[3])))
    exercise = list(map(float, features[4:7]))
    maturity = float(features[7])
    return dict(schedule=[(0.0, maturity, model)], exercise=exercise,
                maturity=maturity)


def roots(grid, gap):
    indices = np.flatnonzero(gap[:-1] * gap[1:] < 0)
    return [float(grid[i] - gap[i] * (grid[i+1] - grid[i]) /
                  (gap[i+1] - gap[i])) for i in indices]


def curves(case, strike, grid, rate, method, order=24):
    schedule, dates, maturity = case["schedule"], case["exercise"], case["maturity"]
    propagate = (lambda start, end, payoff=None:
                 pde_propagate(schedule, start, end, grid, rate, payoff)) if method == "pde" else (
                 lambda start, end, payoff=None:
                 split_propagate(schedule, start, end, grid, rate, payoff, order))
    value = None
    later = None
    records = []
    for date in reversed(dates):
        bond = propagate(date, maturity)
        raw = strike - bond
        intrinsic = np.maximum(raw, 0.0)
        if value is None:
            gap = raw
            value = intrinsic
            kind = "terminal_payoff"
        else:
            continuation = propagate(date, later, value)
            gap = intrinsic - continuation
            value = np.maximum(intrinsic, continuation)
            kind = "early_exercise_vs_continuation"
        crossings = roots(grid, gap)
        records.append(dict(date=date, kind=kind, crossing_log_rate=crossings,
                            crossing_short_rate=[float(np.exp(x)) for x in crossings],
                            exercise_nodes=int(np.sum((gap >= 0) & (intrinsic > 1e-12))),
                            positive_intrinsic_nodes=int(np.sum(intrinsic > 1e-12)),
                            gap_at_initial_state=float(np.interp(np.log(schedule[0][2]["r0"]), grid, gap)),
                            gap_min=float(gap.min()), gap_max=float(gap.max())))
        later = date
    return list(reversed(records))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    for source in cfg["sources"].values():
        if hashlib.sha256(Path(source["file"]).read_bytes()).hexdigest() != source["sha256"]:
            raise RuntimeError("frozen dataset checksum mismatch")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    all_rows = []
    groups_by_cell = (cfg["groups_by_cell"] if "groups_by_cell" in cfg
                      else {cell: cfg["groups"] for cell in cfg["cells"]})
    total_groups = sum(len(groups_by_cell[cell]) for cell in cfg["cells"])
    split_settings = cfg["split_settings"] if "split_settings" in cfg else [cfg["split_setting"]]
    with (out/"boundaries.jsonl").open("w") as ledger:
        for cell in cfg["cells"]:
            source = cfg["sources"][cell]
            with np.load(source["file"]) as data:
                for group in groups_by_cell[cell]:
                    ids = data[f"test_{cell}_group"]
                    indices = np.flatnonzero(ids == group)
                    if len(indices) != 3:
                        raise RuntimeError("frozen group must have three strikes")
                    features = data[f"test_{cell}_X"][indices[1]]
                    if cell == "FB":
                        case = fixed_contract(features)
                    else:
                        tc, _ = time_contract(features, cell)
                        case = tc
                    strike = float(features[-1])
                    settings = []
                    for setting in cfg["pde_settings"]:
                        n, rate, width = setting
                        grid = schedule_grid(case, n, width)
                        started = time.perf_counter()
                        settings.append(dict(method="pde", setting=setting,
                                             records=curves(case, strike, grid, rate, "pde"),
                                             seconds=time.perf_counter()-started))
                    for split_setting in split_settings:
                        n, rate, width, order = split_setting
                        grid = schedule_grid(case, n, width)
                        started = time.perf_counter()
                        settings.append(dict(method="independent_ou_split",
                                             setting=split_setting,
                                             records=curves(case, strike, grid, rate, "split", order),
                                             seconds=time.perf_counter()-started))
                    row = dict(cell=cell, group=group, strike_index=1, strike=strike,
                               settings=settings)
                    ledger.write(json.dumps(row)+"\n")
                    ledger.flush()
                    all_rows.append(row)
                    print(json.dumps(dict(cell=cell, group=group,
                                          completed_groups=len(all_rows),
                                          total_groups=total_groups)), flush=True)
    summary = dict(groups=len(all_rows), settings_per_group=len(cfg["pde_settings"])+len(split_settings),
                   scope="exercise/continuation crossings on representative contracts; numerical boundary pilot")
    (out/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
