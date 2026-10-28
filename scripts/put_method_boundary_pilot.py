"""Compare actual exercise roots of GTFK and coarse PDE with independent references."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[key] = "1"

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from bermudan_gtfk_split_pilot import crossings
from put_exercise_boundary_pilot import curves, fixed_contract, roots
from timevarying_data_pilot import schedule_grid
from timevarying_gtfk import bond as gtfk_bond, propagate as gtfk_propagate
from timevarying_put_risk_pilot import contract as time_contract


def gtfk_curves(case, strike, grid, nq, ny):
    schedule, dates, maturity = case["schedule"], case["exercise"], case["maturity"]
    value = None
    later = None
    kinks = []
    records = []
    for date in reversed(dates):
        bond = gtfk_bond(schedule, date, maturity, grid, grid, nq, ny)
        raw = strike - bond
        intrinsic = np.maximum(raw, 0.0)
        if value is None:
            gap = raw
            value = intrinsic
            kind = "terminal_payoff"
            kinks = crossings(grid, raw)
        else:
            continuation = gtfk_propagate(schedule, date, later, grid, grid,
                                           value, kinks, nq, ny)
            gap = intrinsic - continuation
            value = np.maximum(intrinsic, continuation)
            kinks = crossings(grid, gap)
            kind = "early_exercise_vs_continuation"
        xroots = roots(grid, gap)
        records.append(dict(date=date, kind=kind, crossing_log_rate=xroots,
                            crossing_short_rate=[float(np.exp(x)) for x in xroots],
                            gap_min=float(gap.min()), gap_max=float(gap.max())))
        later = date
    return list(reversed(records))


def compare(one, other):
    result = []
    for a, b in zip(one, other):
        aa = a["crossing_short_rate"]
        bb = b["crossing_short_rate"]
        result.append(dict(date=a["date"], a_roots=len(aa), b_roots=len(bb),
                           abs_root_difference=(abs(aa[0]-bb[0]) if len(aa)==len(bb)==1 else None)))
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    for source in cfg["sources"].values():
        if hashlib.sha256(Path(source["file"]).read_bytes()).hexdigest() != source["sha256"]:
            raise RuntimeError("frozen input checksum mismatch")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    total = sum(map(len, cfg["groups_by_cell"].values()))
    completed = 0
    with (out/"boundary-methods.jsonl").open("w") as ledger:
        for cell, groups in cfg["groups_by_cell"].items():
            with np.load(cfg["sources"][cell]["file"]) as data:
                for group in groups:
                    ids = np.flatnonzero(data[f"test_{cell}_group"] == group)
                    if len(ids) != 3:
                        raise RuntimeError("expected three strikes in frozen group")
                    features = data[f"test_{cell}_X"][ids[1]]
                    case = fixed_contract(features) if cell == "FB" else time_contract(features, cell)[0]
                    strike = float(features[-1])
                    runs = {}
                    for method, settings in (("pde", cfg["reference_pde_settings"]),
                                             ("split", cfg["independent_split_settings"]),
                                             ("coarse_pde", [cfg["coarse_pde_setting"]]),
                                             ("gtfk", cfg["gtfk_settings"])):
                        runs[method] = []
                        for setting in settings:
                            width = float(setting[3] if method == "gtfk" else setting[2])
                            grid = schedule_grid(case, int(setting[0]), width)
                            begin = time.perf_counter()
                            if method == "gtfk":
                                records = gtfk_curves(case, strike, grid, int(setting[1]), int(setting[2]))
                            else:
                                source_method = "split" if method == "split" else "pde"
                                order = int(setting[3]) if method == "split" else 24
                                records = curves(case, strike, grid, int(setting[1]), source_method, order)
                            runs[method].append(dict(setting=setting,
                                                     grid_short_rate_min=float(np.exp(grid[0])),
                                                     grid_short_rate_max=float(np.exp(grid[-1])),
                                                     records=records,
                                                     seconds=time.perf_counter()-begin))
                    reference = runs["pde"][-1]["records"]
                    comparisons = {m: [compare(r["records"], reference) for r in rr]
                                   for m, rr in runs.items()}
                    row = dict(cell=cell, group=group, strike_index=1, strike=strike,
                               runs=runs, comparisons_with_finest_pde=comparisons)
                    ledger.write(json.dumps(row)+"\n")
                    ledger.flush()
                    completed += 1
                    print(json.dumps(dict(completed_groups=completed, total_groups=total,
                                          cell=cell, group=group)), flush=True)
    (out/"summary.json").write_text(json.dumps(dict(groups=completed, total_groups=total,
                  scope="exploratory A/Dbase exercise-root comparison"), indent=2)+"\n")


if __name__ == "__main__":
    main()
