"""Governed P3c numerical pilot; no model training or method ranking."""
import argparse
import json
from pathlib import Path
import time

import numpy as np

from numerics import grid_for
from timevarying_pde import european_put as pde_put, split_european_put
from timevarying_gtfk import european_put as gtfk_put


def evaluate(case, setting):
    schedule = [(item["start"], item["end"], item["model"])
                for item in case["schedule"]]
    model = schedule[0][2]
    grid = grid_for(model, setting["n"], setting["width_scale"])
    center = np.array([np.log(model["r0"])])
    exercise, maturity, strike = case["exercise"], case["maturity"], case["strike"]
    start = time.perf_counter()
    pde = float(pde_put(schedule, exercise, maturity, strike, grid,
                        setting["steps_per_year"])[setting["n"] // 2])
    pde_seconds = time.perf_counter() - start
    start = time.perf_counter()
    split = float(split_european_put(schedule, exercise, maturity, strike, grid,
                                     setting["steps_per_year"], setting["split_order"])
                  [setting["n"] // 2])
    split_seconds = time.perf_counter() - start
    start = time.perf_counter()
    gtfk = float(gtfk_put(schedule, exercise, maturity, strike, center, grid,
                           setting["nq"], setting["ny"])[0])
    gtfk_seconds = time.perf_counter() - start
    return {"setting": setting, "pde": pde, "split": split, "gtfk": gtfk,
            "pde_split_gap": abs(pde - split),
            "gtfk_pde_gap": abs(gtfk - pde),
            "seconds": {"pde": pde_seconds, "split": split_seconds,
                        "gtfk": gtfk_seconds}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    records = []
    for case in cfg["cases"]:
        results = []
        for setting in cfg["settings"]:
            result = evaluate(case, setting)
            results.append(result)
            print(json.dumps({"case": case["name"], **result}), flush=True)
        records.append({"case": case["name"], "results": results})
    report = {"scope": "P3c exploratory numerical pilot only; no training or ranking",
              "cases": records}
    (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
