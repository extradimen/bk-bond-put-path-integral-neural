"""Pre-freeze timing and per-contract quality pilot for T-E/T-B bond puts."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import time

import numpy as np

from numerics import grid_for
from timevarying_bermudan import gtfk_put, pde_put


def sample(n, seed, region="main"):
    if region not in ("main", "ood_vol", "ood_long"):
        raise ValueError("unknown region")
    rng = np.random.default_rng(seed)
    cases = []
    for u in rng.random((n, 11)):
        logscale = lambda lo, hi, z: float(np.exp(np.log(lo) +
                                            (np.log(hi) - np.log(lo)) * z))
        a1, a2 = logscale(.1, 1, u[0]), logscale(.1, 1, u[1])
        s1, s2 = ((float(.65 + .20 * u[2]), float(.65 + .20 * u[3]))
                  if region == "ood_vol" else
                  (float(.1 + .55 * u[2]), float(.1 + .55 * u[3])))
        r0 = logscale(.01, .1, u[4])
        r1, r2 = logscale(.01, .1, u[5]), logscale(.01, .1, u[6])
        if region == "ood_long":
            dates = [1 + u[7]]
            dates.append(dates[-1] + 1 + u[8])
            dates.append(dates[-1] + 1 + u[9])
            maturity = dates[-1] + 2 + 2 * u[10]
        else:
            dates = [.5 + u[7]]
            dates.append(dates[-1] + .5 + u[8])
            dates.append(dates[-1] + .5 + u[9])
            maturity = dates[-1] + 1 + 2 * u[10]
        change = .75 * dates[-1]
        first = {"a": a1, "sigma": s1, "r0": r0, "rbar": r1}
        second = {"a": a2, "sigma": s2, "r0": r0, "rbar": r2}
        schedule = [(0.0, change, first), (change, maturity, second)]
        base = float(np.exp(-r2 * (maturity - dates[-1])))
        strikes = [min(.999, base * ratio) for ratio in (.9, 1.0, 1.1)]
        cases.append({"schedule": schedule, "exercise": dates,
                      "maturity": maturity, "strikes": strikes})
    return cases


def schedule_grid(case, n, width_factor=1.0):
    """Center at initial log-rate; cover the whole piecewise OU path."""
    first = case["schedule"][0][2]
    x0 = float(np.log(first["r0"]))
    first_grid = grid_for(first, 3, 1.5)
    radius = float(first_grid[-1] - x0)
    mean, variance = x0, 0.0
    for left, right, model in case["schedule"]:
        a, sigma, b = model["a"], model["sigma"], np.log(model["rbar"])
        # Substeps bound transient state excursions, including a switch in
        # mean-reversion speed or volatility between exercise dates.
        for _ in range(16):
            dt = (right - left) / 16
            decay = np.exp(-a * dt)
            mean = b + decay * (mean - b)
            variance = decay * decay * variance + sigma * sigma * \
                (-np.expm1(-2 * a * dt)) / (2 * a)
            radius = max(radius, abs(mean - x0) + 7 * np.sqrt(variance) + 0.5)
    return np.linspace(x0 - radius * width_factor,
                       x0 + radius * width_factor, n)


def pde_price(case, dates, strike, n, rate, width):
    grid = schedule_grid(case, n, width)
    return float(pde_put(case["schedule"], dates, case["maturity"], strike,
                         grid, rate)[n // 2])


def gtfk_price(case, dates, strike, n, nq, ny, width):
    model = case["schedule"][0][2]
    grid = schedule_grid(case, n, width)
    starts = np.array([np.log(model["r0"])])
    return float(gtfk_put(case["schedule"], dates, case["maturity"], strike,
                          starts, grid, nq, ny)[0])


def one(item):
    index, case = item
    started, cpu_started = time.perf_counter(), time.process_time()
    rows = []
    try:
        for strike in case["strikes"]:
            prices = {}
            for cell, dates in (("TE", [case["exercise"][-1]]),
                                ("TB", case["exercise"])):
                settings = [(4801, 160, 1.0), (9601, 160, 1.0),
                            (4801, 320, 1.0), (6001, 160, 1.25)]
                reference = [pde_price(case, dates, strike, *s) for s in settings]
                indicator = max(abs(x - reference[0]) for x in reference[1:])
                g1 = gtfk_price(case, dates, strike, 3201, 128, 128, 1.0)
                g2 = gtfk_price(case, dates, strike, 4801, 128, 128, 1.0)
                coarse = pde_price(case, dates, strike, 201, 100, 1.0)
                prices[cell] = {"reference": reference, "reference_settings": settings,
                                "reference_indicator": indicator, "gtfk": [g1, g2],
                                "gtfk_change": abs(g2 - g1), "coarse_pde": coarse}
            rows.append({"strike": strike, "cells": prices,
                         "monotonic": prices["TB"]["reference"][0] + 1e-8 >=
                                      prices["TE"]["reference"][0]})
        certified = all(r["monotonic"] and all(
            r["cells"][cell]["reference_indicator"] <= 1e-6 and
            r["cells"][cell]["gtfk_change"] <= 1e-6
            for cell in ("TE", "TB")) for r in rows)
        return {"group": index, "contract": case, "rows": rows,
                "seconds": time.perf_counter() - started,
                "cpu_seconds": time.process_time() - cpu_started,
                "certified": certified}
    except Exception as exc:
        return {"group": index, "contract": case, "rows": rows,
                "seconds": time.perf_counter() - started,
                "cpu_seconds": time.process_time() - cpu_started,
                "certified": False, "error": type(exc).__name__ + ": " + str(exc)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    cases = sample(cfg["groups"], cfg["seed"], cfg.get("region", "main"))
    started = time.perf_counter()
    rows = []
    with ProcessPoolExecutor(max_workers=cfg["workers"]) as pool, \
            (out / "groups.jsonl").open("w") as ledger:
        for row in pool.map(one, enumerate(cases)):
            rows.append(row)
            ledger.write(json.dumps(row) + "\n")
            ledger.flush()
            print(json.dumps({"group": row["group"],
                              "certified": row["certified"],
                              "seconds": row["seconds"]}), flush=True)
    summary = {"groups": len(rows),
               "certified_groups": sum(x["certified"] for x in rows),
               "failures": [x["group"] for x in rows if not x["certified"]],
               "elapsed_seconds": time.perf_counter() - started,
               "scope": "T-E/T-B pre-freeze quality and timing pilot only"}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
