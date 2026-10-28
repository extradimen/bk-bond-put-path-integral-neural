"""Post-failure numerical diagnosis for frozen conditional-label groups.

This is a diagnostic only. It never changes or selects training labels.
"""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[key] = "1"

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from conditional_boundary import conditional_curves
from put_exercise_boundary_pilot import fixed_contract, roots
from timevarying_data_pilot import schedule_grid
from timevarying_put_risk_pilot import contract as time_contract


def contract_differences(features, case, cfg):
    strike = float(features[-1])
    curves = []
    for n, rate, width in cfg["pde_settings"]:
        grid = schedule_grid(case, n, width)
        curves.append((grid, conditional_curves(case, strike, grid, "pde", rate=rate)))
    n, rate, width, order = cfg["independent"]
    split_grid = schedule_grid(case, n, width)
    split = conditional_curves(case, strike, split_grid, "split", rate=rate, order=order)
    fine_grid, fine = curves[-1]
    lo = fine_grid[0] + cfg["domain_margin"] * np.ptp(fine_grid)
    hi = fine_grid[-1] - cfg["domain_margin"] * np.ptp(fine_grid)
    uniform = np.linspace(lo, hi, cfg["states_per_date"])
    records = []
    for date_index in range(len(case["exercise"])-1):
        reference_roots = roots(fine_grid, fine[date_index]["gap"])
        states = uniform
        if len(reference_roots) == 1:
            offsets = np.asarray(cfg["boundary_offsets"], dtype=float)
            nearby = reference_roots[0] + offsets
            nearby = nearby[(nearby > lo) & (nearby < hi)]
            states = np.unique(np.concatenate((uniform, nearby)))
        target = np.interp(states, fine_grid, fine[date_index]["continuation"])
        pde_differences = [float(np.max(np.abs(target - np.interp(
            states, grid, rows[date_index]["continuation"]))))
            for grid, rows in curves[:-1]]
        independent_difference = float(np.max(np.abs(target - np.interp(
            states, split_grid, split[date_index]["continuation"]))))
        records.append(dict(date_index=date_index, states=len(states),
            reference_root_count=len(reference_roots),
            pde_max_abs_to_finest=pde_differences,
            independent_max_abs_to_finest=independent_difference))
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    for source in cfg["sources"].values():
        if hashlib.sha256(Path(source["file"]).read_bytes()).hexdigest() != source["sha256"]:
            raise RuntimeError("frozen source checksum mismatch")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    total = sum(len(groups) for cells in cfg["groups_by_split"].values()
                for groups in cells.values())
    with (out / "groups.jsonl").open("w") as ledger:
        for split_name, cells in cfg["groups_by_split"].items():
            for cell, groups in cells.items():
                with np.load(cfg["sources"][cell]["file"]) as data:
                    ids = data[f"{split_name}_{cell}_group"]
                    for group in groups:
                        indices = np.flatnonzero(ids == group)
                        if len(indices) != 3:
                            raise RuntimeError("group must have three strike contracts")
                        strikes = []
                        for strike_index, index in enumerate(indices):
                            features = data[f"{split_name}_{cell}_X"][index].copy()
                            case = (fixed_contract(features) if cell == "FB" else
                                    time_contract(features, cell)[0])
                            strikes.append(dict(strike_index=strike_index,
                                records=contract_differences(features, case, cfg)))
                        row = dict(split=split_name, cell=cell, group=group, strikes=strikes)
                        rows.append(row)
                        ledger.write(json.dumps(row) + "\n")
                        ledger.flush()
                        print(json.dumps(dict(completed_groups=len(rows), total_groups=total)), flush=True)
    (out / "summary.json").write_text(json.dumps(dict(completed_groups=len(rows),
        total_groups=total, scope="post-failure numerical diagnostic; no label repair or fit"),
        indent=2) + "\n")


if __name__ == "__main__":
    main()
